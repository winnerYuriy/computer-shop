# admin_config/views.py

import os
import pandas as pd
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from django.http import HttpResponse
from django.utils.text import slugify
from django.utils import timezone

# Імпортуємо моделі з додатків
from shop.models import Product, Category, Brand, Promotion


@staff_member_required
def import_products_view(request):
    """Сторінка імпорту товарів з Excel з автоматичним створенням категорій та брендів"""
    # Мапінг колонок Excel -> поля в коді
    
    column_mapping = {
        'Name': 'title',
        'name': 'title',
        'Назва': 'title',
        'CategoryName': 'category',
        'category_name': 'category',
        'Категорія': 'category',
        'Vendor': 'brand',
        'vendor': 'brand',
        'Бренд': 'brand',
        'PriceUAH': 'price',
        'RetailPrice': 'price',
        'Ціна': 'price',
        'RecommendedPrice': 'old_price',
        'PriceUSD': 'old_price',
        'Stock': 'quantity',
        'stock': 'quantity',
        'Available': 'available',
        'available': 'available',
        'Article': 'article',
        'article': 'article',
        'Code': 'code',
        'code': 'code',
        'Warranty': 'warranty',
        'warranty': 'warranty',
        'Country': 'country',
        'country': 'country',
        'Description': 'description',
        'description': 'description',
        'Model': 'model',
        'ProductID': 'product_id',
    }

    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        
        if not excel_file.name.endswith(('.xlsx', '.xls')):
            messages.error(request, 'Будь ласка, завантажте файл у форматі Excel (.xlsx або .xls)')
            return redirect('admin:index')
        
        file_path = default_storage.save('temp_import.xlsx', ContentFile(excel_file.read()))
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)
        
        created_categories = set()
        created_brands = set()
        created_products = 0
        updated_products = 0
        skipped_products = 0
        errors = []
        
        try:
            df = pd.read_excel(full_path)
            df = df.where(pd.notnull(df), None)
            
            for index, row in df.iterrows():
                try:
                    # Назва товару
                    title = row.get('Name') or row.get('name') or row.get('Назва')
                    if not title:
                        errors.append(f"Рядок {index+2}: пропущено (немає назви товару)")
                        continue
                    
                    # Генеруємо slug з назви
                    base_slug = slugify(title)
                    slug = base_slug
                    counter = 1
                    
                    # Перевіряємо унікальність slug
                    while Product.objects.filter(slug=slug).exists():
                        slug = f"{base_slug}-{counter}"
                        counter += 1
                    
                    # Категорія
                    category_name = row.get('CategoryName') or row.get('category_name') or row.get('Категорія')
                    category = None
                    if category_name:
                        category, created = Category.objects.get_or_create(
                            name=category_name,
                            defaults={'slug': slugify(category_name), 'parent': None}
                        )
                        if created:
                            created_categories.add(category_name)
                    
                    # Бренд
                    brand_name = row.get('Vendor') or row.get('vendor') or row.get('Бренд')
                    brand = None
                    if brand_name:
                        brand, created = Brand.objects.get_or_create(
                            name=brand_name,
                            defaults={'slug': slugify(brand_name)}
                        )
                        if created:
                            created_brands.add(brand_name)
                    
                    # Ціна
                    price = row.get('PriceUAH') or row.get('RetailPrice') or row.get('Ціна') or 0
                    try:
                        price = float(price)
                    except (ValueError, TypeError):
                        price = 0
                    
                    # Стара ціна
                    old_price = row.get('RecommendedPrice') or row.get('PriceUSD') or None
                    if old_price:
                        try:
                            old_price = float(old_price)
                        except (ValueError, TypeError):
                            old_price = None
                    
                    # Знижка
                    discount = 0
                    if old_price and price and old_price > price:
                        discount = int(((old_price - price) / old_price) * 100)
                    
                    # Кількість
                    quantity = row.get('Stock') or row.get('stock') or 1
                    try:
                        quantity = int(quantity) if quantity else 1
                    except (ValueError, TypeError):
                        quantity = 1
                    
                    # Наявність
                    available_raw = row.get('Available') or row.get('available') or 1
                    if isinstance(available_raw, str):
                        available = available_raw.lower() in ['так', 'true', '1', 'yes', '+']
                    else:
                        available = bool(available_raw)
                    
                    # Інші поля
                    article = row.get('Article') or row.get('article') or ''
                    code = row.get('Code') or row.get('code') or ''
                    warranty = row.get('Warranty') or row.get('warranty') or 0
                    try:
                        warranty = int(warranty) if warranty else 0
                    except (ValueError, TypeError):
                        warranty = 0
                    country = row.get('Country') or row.get('country') or ''
                    description = row.get('Description') or row.get('description') or ''
                    full_description = f"Модель: {row.get('Model', '')}\nВиробник: {brand_name}\nГарантія: {warranty} міс." if row.get('Model') else ''
                    
                    # Додаткові атрибути
                    attributes = {}
                    optional_fields = ['Model', 'ProductID', 'EAN', 'FOP', 'GroupID', 'ClassID', 'ClassName', 'DayDelivery', 'Bonus', 'Exclusive', 'UKTVED']
                    for field in optional_fields:
                        if row.get(field):
                            attributes[field.lower()] = row.get(field)
                    
                    # Акції
                    promotions = []
                    promotions_str = row.get('promotions') or row.get('Акції', '')
                    if promotions_str:
                        for promo_name in str(promotions_str).split(','):
                            promo_name = promo_name.strip()
                            if promo_name:
                                promo, _ = Promotion.objects.get_or_create(
                                    name=promo_name,
                                    defaults={
                                        'promotion_type': 'sale',
                                        'start_date': timezone.now(),
                                        'end_date': timezone.now() + timezone.timedelta(days=365),
                                        'slug': slugify(promo_name)
                                    }
                                )
                                promotions.append(promo)
                    
                    # Перевіряємо, чи існує товар з таким code або title
                    existing_product = None
                    if code:
                        existing_product = Product.objects.filter(code=code).first()
                    
                    if existing_product:
                        # Оновлюємо існуючий товар
                        product = existing_product
                        product.title = title
                        product.category = category
                        product.brand = brand
                        product.price = price
                        product.old_price = old_price
                        product.discount = discount
                        product.quantity = quantity
                        product.available = available
                        product.article = article
                        product.warranty = warranty
                        product.country = country
                        product.description = description
                        product.full_description = full_description
                        product.attributes = attributes if attributes else None
                        product.save()
                        updated_products += 1
                    else:
                        # Створюємо новий товар з унікальним slug
                        product = Product.objects.create(
                            title=title,
                            slug=slug,
                            category=category,
                            brand=brand,
                            price=price,
                            old_price=old_price,
                            discount=discount,
                            quantity=quantity,
                            available=available,
                            article=article,
                            code=code,
                            warranty=warranty,
                            country=country,
                            description=description,
                            full_description=full_description,
                            attributes=attributes if attributes else None,
                        )
                        created_products += 1
                    
                    # Додаємо акції
                    if promotions:
                        product.promotions.set(promotions)
                        
                except Exception as e:
                    errors.append(f"Рядок {index+2}: {str(e)}")
                    continue
            
            # Підсумкове повідомлення
            message_parts = []
            if created_products > 0:
                message_parts.append(f"✅ Створено товарів: {created_products}")
            if updated_products > 0:
                message_parts.append(f"🔄 Оновлено товарів: {updated_products}")
            if created_categories:
                message_parts.append(f"📁 Створено категорій: {', '.join(created_categories)}")
            if created_brands:
                message_parts.append(f"🏷️ Створено брендів: {', '.join(created_brands)}")
            
            if message_parts:
                messages.success(request, '. '.join(message_parts))
            else:
                messages.warning(request, "Не було створено або оновлено жодного товару")
            
            if errors:
                messages.warning(request, f"⚠️ Помилок: {len(errors)}. Перевірте консоль для деталей.")
                for error in errors[:5]:
                    print(error)
                
        except Exception as e:
            messages.error(request, f'❌ Помилка імпорту: {str(e)}')
        finally:
            if os.path.exists(full_path):
                os.remove(full_path)
        
        return redirect('admin:index')
    
    return render(request, 'admin/import_products.html')


@staff_member_required
def export_products_view(request):
    """Експорт товарів у Excel"""
    products = Product.objects.all().select_related('category', 'brand').prefetch_related('promotions')
    
    data = []
    for product in products:
        row = {
            'ID': product.id,
            'Name': product.title,
            'CategoryName': product.category.name if product.category else '',
            'Vendor': product.brand.name if product.brand else '',
            'PriceUAH': float(product.price),
            'RecommendedPrice': float(product.old_price) if product.old_price else '',
            'Stock': product.quantity,
            'Available': 'Так' if product.available else 'Ні',
            'Article': product.article or '',
            'Code': product.code or '',
            'Warranty': product.warranty,
            'Country': product.country or '',
            'Discount': product.discount,
            'Description': product.description,
            'FullDescription': product.full_description,
            'Attributes': product.attributes if product.attributes else '',
            'Promotions': ', '.join([p.name for p in product.promotions.all()]),
            'Created': product.created_at.strftime('%Y-%m-%d %H:%M:%S') if product.created_at else '',
            'Updated': product.updated_at.strftime('%Y-%m-%d %H:%M:%S') if product.updated_at else '',
        }
        data.append(row)
    
    df = pd.DataFrame(data)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="products_export.xlsx"'
    df.to_excel(response, index=False, engine='openpyxl')
    
    return response


@staff_member_required
def export_template_view(request):
    """Завантаження шаблону для імпорту"""
    template_data = [{
        'Name': 'Приклад товару',
        'CategoryName': 'Ноутбуки',
        'Vendor': 'ASUS',
        'PriceUAH': 18999,
        'RecommendedPrice': 15999,
        'Stock': 25,
        'Available': 'Так',
        'Article': 'ART001',
        'Code': 'CODE001',
        'Warranty': 24,
        'Country': 'Китай',
        'Description': 'Короткий опис товару',
        'FullDescription': 'Повний опис товару',
        'Attributes': '{"Процесор": "Intel Core i5", "RAM": "16GB", "SSD": "512GB"}',
        'Promotions': 'Новинка,Хіт продажів',
    }]
    
    df = pd.DataFrame(template_data)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="import_template.xlsx"'
    df.to_excel(response, index=False, engine='openpyxl')
    
    return response


@staff_member_required
def dashboard_stats_view(request):
    """JSON статистика для дашборду (AJAX)"""
    from django.db.models import Sum, Count, Avg
    from datetime import timedelta
    
    total_products = Product.objects.count()
    total_available = Product.objects.filter(available=True).count()
    total_categories = Category.objects.count()
    total_brands = Brand.objects.count()
    
    # Статистика по замовленнях
    try:
        from shop.models import Order
        total_orders = Order.objects.count()
        total_revenue = Order.objects.filter(is_paid=True).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        month_ago = timezone.now() - timedelta(days=30)
        recent_orders = Order.objects.filter(created_at__gte=month_ago).count()
    except ImportError:
        total_orders = 0
        total_revenue = 0
        recent_orders = 0
    
    low_stock = Product.objects.filter(quantity__lt=5, available=True).count()
    no_image = Product.objects.filter(main_image='').count()
    
    data = {
        'total_products': total_products,
        'total_available': total_available,
        'total_categories': total_categories,
        'total_brands': total_brands,
        'total_orders': total_orders,
        'total_revenue': int(total_revenue),
        'recent_orders': recent_orders,
        'low_stock': low_stock,
        'no_image': no_image,
    }
    
    import json
    return HttpResponse(json.dumps(data, ensure_ascii=False), content_type='application/json')