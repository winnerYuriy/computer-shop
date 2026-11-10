# payment/views.py

import base64
import hashlib
import hmac
import json
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.conf import settings
from django.db import transaction
from shop.models import Order, Product


def generate_liqpay_signature(data, private_key):
    """Генерує підпис для LiqPay"""
    return base64.b64encode(
        hashlib.sha1(
            (private_key + data + private_key).encode()
        ).digest()
    ).decode()


def update_product_stock(order):
    """Зменшує кількість товарів на складі після оплати"""
    for item in order.products:
        try:
            product = Product.objects.get(id=item['id'])
            quantity = item['quantity']
            
            if product.quantity >= quantity:
                product.quantity -= quantity
                product.save(update_fields=['quantity'])
                print(f"✅ Оновлено залишок {product.title}: -{quantity} (залишилось {product.quantity})")
            else:
                print(f"⚠️ Недостатньо товару {product.title}: потрібно {quantity}, є {product.quantity}")
        except Product.DoesNotExist:
            print(f"❌ Товар з ID {item['id']} не знайдено")


def payment_process(request, order_id):
    """Створення платежу LiqPay"""
    order = get_object_or_404(Order, id=order_id, is_paid=False)
    
    public_key = getattr(settings, 'LIQPAY_PUBLIC_KEY', '')
    private_key = getattr(settings, 'LIQPAY_PRIVATE_KEY', '')
    
    if not public_key or not private_key:
        return render(request, 'payment/process.html', {
            'order': order,
            'payment_error': 'Не налаштовані ключі LiqPay. Додайте їх у файл .env.',
        }, status=503)
    
    order_products = order.products
    product_names = [item['name'] for item in order_products[:3]]
    description = ', '.join(product_names)
    if len(order_products) > 3:
        description += f' та ще {len(order_products) - 3} товарів'
    
    base_url = request.build_absolute_uri('/')
    server_url = getattr(settings, 'LIQPAY_SERVER_URL', '') or base_url + 'payment/callback/'
    
    data = {
        'version': '3',
        'public_key': public_key,
        'action': 'pay',
        'amount': str(order.total_amount),
        'currency': 'UAH',
        'description': description[:100],
        'order_id': str(order.id),
        'server_url': server_url,
        'result_url': base_url + f'payment/result/?order_id={order.id}',
    }
    if settings.LIQPAY_SANDBOX:
        data['sandbox'] = 1
    
    data_str = base64.b64encode(json.dumps(data).encode()).decode()
    signature = generate_liqpay_signature(data_str, private_key)
    
    return render(request, 'payment/process.html', {
        'order': order,
        'liqpay_data': data_str,
        'liqpay_signature': signature,
    })


def payment_result(request):
    """Показує результат з БД; браузерне повернення не підтверджує оплату."""
    order_id = request.GET.get('order_id')
    if not order_id:
        return redirect('payment:cancel')

    order = get_object_or_404(Order, id=order_id)
    if order.is_paid:
        return redirect('payment:complete')

    return render(request, 'payment/result.html', {'order': order})


@csrf_exempt
@require_POST
def payment_callback(request):
    """Callback від LiqPay після оплати (серверний виклик)"""
    data = request.POST.get('data')
    signature = request.POST.get('signature')
    
    if not data or not signature:
        return HttpResponse('Missing data', status=400)
    
    private_key = getattr(settings, 'LIQPAY_PRIVATE_KEY', '')
    if not private_key or not settings.LIQPAY_PUBLIC_KEY:
        return HttpResponse('Payment is not configured', status=503)
    
    expected_signature = generate_liqpay_signature(data, private_key)
    
    if not hmac.compare_digest(signature, expected_signature):
        return HttpResponse('Invalid signature', status=400)
    
    try:
        decoded_data = json.loads(base64.b64decode(data, validate=True).decode())
        if not isinstance(decoded_data, dict):
            return HttpResponse('Invalid payment data', status=400)
        order_id = int(decoded_data.get('order_id'))
        amount = Decimal(str(decoded_data.get('amount')))
    except (ValueError, TypeError, InvalidOperation, json.JSONDecodeError):
        return HttpResponse('Invalid payment data', status=400)

    with transaction.atomic():
        try:
            order = Order.objects.select_for_update().get(id=order_id)
        except Order.DoesNotExist:
            return HttpResponse('Order not found', status=404)

        if (
            decoded_data.get('public_key') != settings.LIQPAY_PUBLIC_KEY
            or decoded_data.get('action') != 'pay'
            or decoded_data.get('currency') != 'UAH'
            or amount != order.total_amount
        ):
            return HttpResponse('Payment does not match order', status=400)

        if decoded_data.get('status') in ('success', 'sandbox') and not order.is_paid:
            order.is_paid = True
            order.status = 'paid'
            order.payment_id = decoded_data.get('payment_id')
            order.payment_method = 'liqpay'
            order.save()
            update_product_stock(order)

    return HttpResponse('OK')


def payment_complete(request):
    """Сторінка після успішної оплати"""
    return render(request, 'payment/complete.html')


def payment_cancel(request):
    """Сторінка при скасуванні оплати"""
    messages.warning(request, 'Оплату скасовано')
    return render(request, 'payment/cancel.html')