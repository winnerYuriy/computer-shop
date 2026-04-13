# payment/views.py

import json
import hashlib
import base64
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
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
            
            if product.stock >= quantity:
                product.stock -= quantity
                product.save()
                print(f"✅ Оновлено залишок {product.name}: -{quantity} (залишилось {product.stock})")
            else:
                print(f"⚠️ Недостатньо товару {product.name}: потрібно {quantity}, є {product.stock}")
        except Product.DoesNotExist:
            print(f"❌ Товар з ID {item['id']} не знайдено")


def payment_process(request, order_id):
    """Створення платежу LiqPay"""
    order = get_object_or_404(Order, id=order_id, is_paid=False)
    
    public_key = getattr(settings, 'LIQPAY_PUBLIC_KEY', '')
    private_key = getattr(settings, 'LIQPAY_PRIVATE_KEY', '')
    
    if not public_key or not private_key:
        public_key = 'sandbox_i1234567890'
        private_key = 'sandbox_1234567890'
        messages.warning(request, 'Використовуються тестові ключі LiqPay')
    
    order_products = order.products
    product_names = [item['name'] for item in order_products[:3]]
    description = ', '.join(product_names)
    if len(order_products) > 3:
        description += f' та ще {len(order_products) - 3} товарів'
    
    base_url = request.build_absolute_uri('/')
    
    data = {
        'version': '3',
        'public_key': public_key,
        'action': 'pay',
        'amount': str(order.total_amount),
        'currency': 'UAH',
        'description': description[:100],
        'order_id': str(order.id),
        'server_url': base_url + 'payment/callback/',
        'result_url': base_url + f'payment/result/?order_id={order.id}',
    }
    
    data_str = base64.b64encode(json.dumps(data).encode()).decode()
    signature = generate_liqpay_signature(data_str, private_key)
    
    form_html = f'''
    <form method="POST" action="https://www.liqpay.ua/api/3/checkout" accept-charset="utf-8" id="liqpayForm">
        <input type="hidden" name="data" value="{data_str}" />
        <input type="hidden" name="signature" value="{signature}" />
        <button type="submit" class="btn btn-primary btn-lg">
            Оплатити {order.total_amount}₴
        </button>
    </form>
    '''
    
    return render(request, 'payment/process.html', {
        'order': order,
        'form': form_html,
    })


def payment_result(request):
    """Сторінка повернення після оплати (через result_url)"""
    order_id = request.GET.get('order_id')
    status = request.GET.get('status')
    
    if order_id:
        try:
            order = Order.objects.get(id=order_id)
            
            if not order.is_paid:
                # Оновлюємо статус замовлення
                order.is_paid = True
                order.status = 'paid'
                order.payment_id = request.GET.get('payment_id', '')
                order.payment_method = 'liqpay'
                order.save()
                
                # Зменшуємо кількість товарів на складі
                update_product_stock(order)
                
                messages.success(request, f'Замовлення #{order.id} успішно оплачено!')
                return redirect('payment:complete')
            else:
                messages.info(request, f'Замовлення #{order.id} вже оплачено')
                return redirect('payment:complete')
                
        except Order.DoesNotExist:
            messages.error(request, 'Замовлення не знайдено')
    
    messages.warning(request, f'Статус оплати: {status if status else "невідомо"}')
    return redirect('payment:cancel')


@csrf_exempt
def payment_callback(request):
    """Callback від LiqPay після оплати (серверний виклик)"""
    data = request.POST.get('data')
    signature = request.POST.get('signature')
    
    if not data or not signature:
        return HttpResponse('Missing data', status=400)
    
    private_key = getattr(settings, 'LIQPAY_PRIVATE_KEY', 'sandbox_1234567890')
    
    expected_signature = generate_liqpay_signature(data, private_key)
    
    if signature != expected_signature:
        return HttpResponse('Invalid signature', status=400)
    
    try:
        decoded_data = json.loads(base64.b64decode(data).decode())
        
        order_id = int(decoded_data.get('order_id'))
        status = decoded_data.get('status')
        
        order = get_object_or_404(Order, id=order_id)
        
        if status == 'success' and not order.is_paid:
            with transaction.atomic():
                order.is_paid = True
                order.status = 'paid'
                order.payment_id = decoded_data.get('payment_id')
                order.payment_method = 'liqpay'
                order.save()
                
                # Зменшуємо кількість товарів на складі
                update_product_stock(order)
                
            print(f"✅ Замовлення #{order.id} оплачено через callback! Склад оновлено.")
        
        return HttpResponse('OK')
    
    except Exception as e:
        print(f"Помилка в callback: {e}")
        return HttpResponse(str(e), status=400)


def payment_complete(request):
    """Сторінка після успішної оплати"""
    return render(request, 'payment/complete.html')


def payment_cancel(request):
    """Сторінка при скасуванні оплати"""
    messages.warning(request, 'Оплату скасовано')
    return render(request, 'payment/cancel.html')