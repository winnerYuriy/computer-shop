# cart/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import transaction
from shop.models import Product, Order
from .cart import Cart


@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id, is_active=True)
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        messages.error(request, 'Вкажіть коректну кількість товару.')
        return redirect('cart:cart_detail')

    try:
        cart.add(product=product, quantity=quantity, override_quantity=False)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect('cart:cart_detail')
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
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        messages.error(request, 'Вкажіть коректну кількість товару.')
        return redirect('cart:cart_detail')

    if quantity == 0:
        cart.remove(product)
    else:
        try:
            cart.add(product=product, quantity=quantity, override_quantity=True)
        except ValueError as error:
            messages.error(request, str(error))
    
    return redirect('cart:cart_detail')


def checkout(request):
    """Сторінка оформлення замовлення"""
    cart = Cart(request)
    
    cart_quantities = cart.get_quantities()
    if not cart_quantities:
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
        
        order = None
        with transaction.atomic():
            products = list(
                Product.objects.select_for_update()
                .filter(id__in=cart_quantities)
                .order_by('id')
            )
            products_by_id = {str(product.id): product for product in products}
            if len(products_by_id) != len(cart_quantities):
                errors.append('Один або кілька товарів більше не доступні.')

            products_list = []
            total_amount = 0
            for product_id, quantity in cart_quantities.items():
                product = products_by_id.get(product_id)
                if product is None:
                    continue
                if not product.is_active:
                    errors.append(f'«{product.name}» більше недоступний.')
                    continue
                if quantity > product.stock:
                    errors.append(
                        f'Для «{product.name}» доступно лише {product.stock} шт.'
                    )
                    continue
                if product.price <= 0 or product.final_price <= 0:
                    errors.append(f'Для «{product.name}» задана некоректна ціна.')
                    continue
                if product.sale_price is not None and product.sale_price >= product.price:
                    errors.append(f'Для «{product.name}» задана некоректна акційна ціна.')
                    continue

                current_price = product.final_price
                total_amount += current_price * quantity
                products_list.append({
                    'id': product.id,
                    'name': product.name,
                    'price': str(current_price),
                    'quantity': quantity,
                    'image': product.image.url if product.image else None,
                })

            if not errors:
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
                    total_amount=total_amount,
                    status='new',
                    is_paid=False,
                )

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'cart/checkout.html', {'cart': cart})
        
        # Очищаємо кошик
        cart.clear()
        
        messages.success(request, f'Замовлення #{order.id} створено!')
        
        # Перенаправляємо на сторінку оплати
        return redirect('payment:process', order_id=order.id)
    
    return render(request, 'cart/checkout.html', {'cart': cart})