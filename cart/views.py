# cart/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from shop.models import Product, Order
from .cart import Cart


@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id, is_active=True)
    quantity = int(request.POST.get('quantity', 1))
    cart.add(product=product, quantity=quantity, override_quantity=False)
    messages.success(request, f'{product.name} додано до кошика')
    return redirect('cart:cart_detail')


@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    messages.success(request, 'Товар видалено з кошика')
    return redirect('cart:cart_detail')


def cart_detail(request):
    return render(request, 'cart/detail.html')


@require_POST
def cart_update(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity > 0:
        cart.add(product=product, quantity=quantity, override_quantity=True)
    else:
        cart.remove(product)
    
    return redirect('cart:cart_detail')


def checkout(request):
    """Сторінка оформлення замовлення"""
    cart = Cart(request)
    
    if len(cart) == 0:
        messages.warning(request, 'Ваш кошик порожній')
        return redirect('cart:cart_detail')
    
    if request.method == 'POST':
        # Отримуємо дані з форми
        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        delivery_method = request.POST.get('delivery_method')
        city = request.POST.get('city')
        nova_post_office = request.POST.get('nova_post_office')
        address = request.POST.get('address')
        comment = request.POST.get('comment', '')
        
        # Валідація
        errors = []
        if not full_name:
            errors.append('Вкажіть ПІБ')
        if not phone:
            errors.append('Вкажіть телефон')
        if not email:
            errors.append('Вкажіть email')
        if delivery_method == 'nova_post' and not nova_post_office:
            errors.append('Вкажіть відділення Нової Пошти')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'cart/checkout.html', {'cart': cart})
        
        # Формуємо список товарів для збереження
        products_list = []
        for item in cart:
            products_list.append({
                'id': item['product'].id,
                'name': item['product'].name,
                'price': str(item['price']),
                'quantity': item['quantity'],
                'image': item['product'].image.url if item['product'].image else None,
            })
        
        # Створюємо замовлення
        order = Order.objects.create(
            full_name=full_name,
            phone=phone,
            email=email,
            address=address or city or nova_post_office,
            city=city,
            nova_post_office=nova_post_office,
            delivery_method=delivery_method,
            comment=comment,
            products=products_list,
            total_amount=cart.get_total_price(),
            status='new',
            is_paid=False,
        )
        
        # Очищаємо кошик
        cart.clear()
        
        messages.success(request, f'Замовлення #{order.id} створено!')
        
        # Перенаправляємо на сторінку оплати
        return redirect('payment:process', order_id=order.id)
    
    return render(request, 'cart/checkout.html', {'cart': cart})