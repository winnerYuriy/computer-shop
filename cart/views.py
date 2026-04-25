# cart/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from shop.models import Product, Order
from .cart import Cart


@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id, available=True) 
    quantity = int(request.POST.get('quantity', 1))
    cart.add(product=product, quantity=quantity, override_quantity=False)
    messages.success(request, f'{product.title} додано до кошика')
    return redirect('cart:cart_detail')


@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    messages.success(request, 'Товар видалено з кошика')
    return redirect('cart:cart_detail')


def cart_detail(request):
    cart = Cart(request)
    return render(request, 'cart/detail.html', {'cart': cart})


@require_POST
def cart_update(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity > 0:
        cart.add(product=product, quantity=quantity, override_quantity=True)
    else:
        cart.remove(product)
    
    messages.success(request, 'Кошик оновлено')
    return redirect('cart:cart_detail')


def checkout(request):
    """Сторінка оформлення замовлення з автозаповненням даних користувача"""
    cart = Cart(request)
    
    # Перевіряємо, чи кошик не порожній
    if len(cart) == 0:
        messages.warning(request, 'Ваш кошик порожній')
        return redirect('cart:cart_detail')
    
    # Дані за замовчуванням
    initial_data = {}
    
    # Якщо користувач авторизований, підтягуємо його дані
    if request.user.is_authenticated:
        user = request.user
        initial_data = {
            'full_name': user.get_full_name() or user.username,
            'phone': getattr(user, 'phone', ''),
            'email': user.email,
            'address': getattr(user, 'address', ''),
            'city': getattr(user, 'city', ''),
        }
    
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        delivery_method = request.POST.get('delivery_method', 'nova_post')
        city = request.POST.get('city', '').strip()
        nova_post_office = request.POST.get('nova_post_office', '').strip()
        address = request.POST.get('address', '').strip()
        comment = request.POST.get('comment', '').strip()
        
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
            return render(request, 'cart/checkout.html', {
                'cart': cart,
                'form_data': request.POST,
                'initial_data': initial_data,
            })
        
        # Формуємо список товарів
        products_list = []
        for item in cart:
            products_list.append({
                'id': item['product'].id,
                'name': item['product'].title,
                'price': str(item['price']),
                'quantity': item['quantity'],
                'image': item['product'].main_image.url if item['product'].main_image else None,
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
    
    context = {
        'cart': cart,
        'initial_data': initial_data,
    }
    return render(request, 'cart/checkout.html', context)