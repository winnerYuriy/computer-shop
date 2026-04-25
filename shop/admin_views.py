import csv 
import datetime
import json
import os
import tempfile
import requests
import logging
from config import settings
from django.db.models import Sum
from decimal import Decimal
from shop.utils import (
    get_image_url_by_product_code, get_token, get_pricelist_url, 
    download_pricelist, generate_invoice_pdf, save_image_from_url
)
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import FileResponse, HttpResponse, JsonResponse
from django.db import transaction
from shop.models import Product, Category, Brand, LegalEntity, Order, Invoice, InvoiceItem, Service
import pandas as pd
from django.views.decorators.csrf import csrf_exempt
from .models import AdminNotification

# Налаштування логера
import_logger = logging.getLogger('import_logger')

@staff_member_required
def import_products(request):
    result = None
    if request.method == 'POST':
        excel_file = request.FILES.get('excel_file')
        usd_rate = request.POST.get('usd_rate')
        update_existing = request.POST.get('update_existing') == 'yes'
        
        if not excel_file:
            messages.error(request, 'Будь ласка, виберіть файл')
            return redirect('.')
        
        # Отримання курсу USD
        if usd_rate and usd_rate.strip():
            try:
                usd_rate = float(usd_rate.replace(',', '.'))
            except:
                usd_rate = None
        else:
            usd_rate = None
        
        if usd_rate is None:
            usd_rate = get_usd_rate()
            if usd_rate is None:
                messages.error(request, 'Не вдалося отримати курс USD. Вкажіть вручну.')
                return redirect('.')
        
        # Зберігаємо файл тимчасово
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            for chunk in excel_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name
        
        try:
            result = process_import(tmp_path, usd_rate, update_existing, request)
            
            # Формуємо повідомлення про результат
            summary = result['summary']
            msg = f"📊 Імпорт завершено. Створено: {result['created']}, Оновлено: {result['updated']}, Помилок: {result['errors']}"
            
            # Додаємо деталі змін
            if result['price_changes']:
                msg += f"\n💰 Змін цін: {result['price_changes']}"
            if result['price_increases']:
                msg += f" (зросло: {result['price_increases']}, зменшилось: {result['price_decreases']})"
            
            messages.success(request, msg)
            
            # Логування в файл
            import_logger.info(f"=== ІМПОРТ ЗАВЕРШЕНО: {datetime.now().isoformat()} ===")
            import_logger.info(f"Файл: {excel_file.name}")
            import_logger.info(f"Створено: {result['created']}, Оновлено: {result['updated']}, Помилок: {result['errors']}")
            import_logger.info(f"Зміни цін: +{result['price_increases']}/-{result['price_decreases']}")
            
            # Зберігаємо детальний лог змін
            if result['change_log']:
                import_logger.info("Детальні зміни:")
                for change in result['change_log']:
                    import_logger.info(f"  {change}")
            
        except Exception as e:
            messages.error(request, f'Помилка імпорту: {str(e)}')
            import_logger.error(f"Помилка імпорту: {str(e)}")
        finally:
            os.unlink(tmp_path)
        
        return render(request, 'admin/import_products.html', {'result': result})
    
    return render(request, 'admin/import_products.html')


def process_import(file_path, usd_rate, update_existing, request=None):
    df = pd.read_excel(file_path, dtype=str)
    
    # Перевірка курсу
    if usd_rate is None:
        usd_rate = 40.0
        print(f"⚠️ Курс USD не вказано, використовуємо {usd_rate}")
    else:
        try:
            usd_rate = float(usd_rate)
            print(f"Використовуємо курс USD: {usd_rate}")
        except:
            usd_rate = 40.0
            print(f"⚠️ Помилка конвертації курсу, використовуємо {usd_rate}")
    
    # Перевіряємо, чи є колонка RetailPrice
    has_retail_price = 'RetailPrice' in df.columns
    
    created = 0
    updated = 0
    errors = 0
    error_list = []
    price_changes = 0
    price_increases = 0
    price_decreases = 0
    change_log = []
    
    for index, row in df.iterrows():
        try:
            with transaction.atomic():
                # --- Отримання категорії ---
                cat_name = row.get('CategoryName', '')
                
                if pd.isna(cat_name) or str(cat_name).strip() == '':
                    cat_name = 'Без категорії'
                else:
                    cat_name = str(cat_name).strip()
                
                if cat_name and cat_name != 'Без категорії':
                    slug_value = slugify(cat_name)
                else:
                    slug_value = 'without-category'
                
                category, cat_created = Category.objects.get_or_create(
                    name=cat_name,
                    defaults={'slug': slug_value}
                )
                
                if cat_created:
                    change_log.append(f"📁 Створено категорію: {cat_name}")
                
                # --- Бренд ---
                vendor_name = row.get('Vendor', '')
                brand = None
                if not pd.isna(vendor_name) and str(vendor_name).strip() != '':
                    vendor_name = str(vendor_name).strip()
                    brand, brand_created = Brand.objects.get_or_create(
                        name=vendor_name,
                        defaults={'slug': slugify(vendor_name)}
                    )
                    if brand_created:
                        change_log.append(f"🏷️ Створено бренд: {vendor_name}")
                
                # --- Артикул ---
                article = row.get('Article', '')
                if pd.isna(article) or str(article).strip() == '':
                    errors += 1
                    error_list.append(f'Рядок {index+2}: пропущено (немає артикулу)')
                    continue
                article = str(article).strip()
                
                # --- Код ---
                code = row.get('Code', '')
                if pd.isna(code):
                    code = ''
                else:
                    code = str(code).strip()
                
                # --- ЦІНА ---
                price_uah = Decimal('0')
                price_source = None
                
                if has_retail_price:
                    retail_price_raw = row.get('RetailPrice', '0')
                    if not pd.isna(retail_price_raw) and str(retail_price_raw).strip() != '':
                        try:
                            retail_price_str = str(retail_price_raw).strip().replace(',', '.').replace(' ', '')
                            import re
                            retail_price_str = re.sub(r'[^\d.]', '', retail_price_str)
                            if retail_price_str and retail_price_str != '':
                                price_uah = Decimal(retail_price_str)
                                price_uah = price_uah.quantize(Decimal('1'), rounding='ROUND_HALF_UP')
                                price_source = 'RetailPrice'
                        except Exception as e:
                            price_uah = Decimal('0')
                
                if price_uah == 0:
                    price_usd_raw = row.get('PriceUSD', '0')
                    if pd.isna(price_usd_raw):
                        price_usd_str = '0'
                    else:
                        price_usd_str = str(price_usd_raw).strip().replace(',', '.')
                        import re
                        price_usd_str = re.sub(r'[^\d.-]', '', price_usd_str)
                        if price_usd_str == '' or price_usd_str == '-':
                            price_usd_str = '0'
                    
                    try:
                        price_usd = Decimal(price_usd_str)
                        price_uah = price_usd * Decimal(str(usd_rate))
                        price_uah = price_uah.quantize(Decimal('1'), rounding='ROUND_HALF_UP')
                        price_source = f'PriceUSD ({price_usd}$ → {usd_rate} конвертація)'
                    except:
                        price_uah = Decimal('0')
                
                # --- Кількість ---
                stock_available = row.get('Stock', '0')
                if pd.isna(stock_available):
                    quantity = 0
                else:
                    stock_str = str(stock_available).strip().lower()
                    try:
                        quantity = int(float(stock_str))
                    except:
                        quantity = 0
                
                available = quantity > 0
                
                # --- Гарантія ---
                warranty_val = row.get('Warranty', 0)
                if pd.isna(warranty_val):
                    warranty = 0
                else:
                    try:
                        warranty = int(float(str(warranty_val).replace(',', '.')))
                    except:
                        warranty = 0
                
                # --- Країна ---
                country = row.get('Country', '')
                if pd.isna(country):
                    country = ''
                else:
                    country = str(country).strip()
                
                # --- Назва ---
                title = row.get('Name', '')
                if pd.isna(title):
                    title = 'Без назви'
                else:
                    title = str(title).strip()[:250]
                
                # --- Опис ---
                description = row.get('Description', '')
                if pd.isna(description):
                    description = ''
                else:
                    description = str(description).strip()[:2000]
                
                # --- Пошук або оновлення ---
                if update_existing:
                    product = Product.objects.filter(article=article).first()
                    
                    if product:
                        changes = []
                        
                        # Перевірка змін
                        if product.title != title:
                            changes.append(f"назву '{product.title}' → '{title}'")
                            product.title = title
                        
                        if product.category != category:
                            changes.append(f"категорію '{product.category.name if product.category else 'Без'}' → '{category.name}'")
                            product.category = category
                        
                        if product.brand != brand:
                            changes.append(f"бренд '{product.brand.name if product.brand else 'Немає'}' → '{brand.name if brand else 'Немає'}'")
                            product.brand = brand
                        
                        if product.price != price_uah:
                            old_price = product.price
                            change_type = "📈 ЗРОСЛА" if price_uah > old_price else "📉 ЗМЕНШИЛАСЯ"
                            changes.append(f"ціну {old_price}₴ → {price_uah}₴ ({change_type})")
                            product.price = price_uah
                            price_changes += 1
                            if price_uah > old_price:
                                price_increases += 1
                            else:
                                price_decreases += 1
                        
                        if product.quantity != quantity:
                            changes.append(f"кількість '{product.quantity}' → '{quantity}'")
                            product.quantity = quantity
                        
                        if product.available != available:
                            changes.append(f"наявність '{product.available}' → '{available}'")
                            product.available = available
                        
                        if product.warranty != warranty:
                            changes.append(f"гарантію '{product.warranty}' міс → '{warranty}' міс")
                            product.warranty = warranty
                        
                        if product.country != country:
                            changes.append(f"країну '{product.country}' → '{country}'")
                            product.country = country
                        
                        if changes:
                            product.save()
                            updated += 1
                            change_msg = f"✅ Оновлено: {article} - {title}\n   📝 Зміни: {', '.join(changes)}"
                            change_log.append(change_msg)
                            
                            # Виводимо в консоль
                            print(change_msg)
                            
                            # Додаємо повідомлення в браузер (через messages)
                            if request:
                                messages.info(request, f"🔄 {article}: {', '.join(changes[:3])}" + 
                                             (f" та інші" if len(changes) > 3 else ""))
                        else:
                            print(f"  ⏭️ Без змін: {article}")
                        continue
                    else:
                        # Створення нового товару
                        product = Product.objects.create(
                            category=category,
                            brand=brand,
                            title=title,
                            article=article,
                            code=code,
                            description=description,
                            price=price_uah,
                            quantity=quantity,
                            available=available,
                            warranty=warranty,
                            country=country,
                        )
                        created += 1
                        change_msg = f"✨ Створено: {article} - {title} (ціна: {price_uah}₴)"
                        change_log.append(change_msg)
                        print(change_msg)
                        
                        if request:
                            messages.success(request, f"✨ Створено новий товар: {article} - {title}")
                else:
                    # Якщо не оновлюємо існуючі, просто створюємо нові
                    if not Product.objects.filter(article=article).exists():
                        Product.objects.create(
                            category=category,
                            brand=brand,
                            title=title,
                            article=article,
                            code=code,
                            description=description,
                            price=price_uah,
                            quantity=quantity,
                            available=available,
                            warranty=warranty,
                            country=country,
                        )
                        created += 1
                        print(f"  ✅ Створено: {article}")
                
        except Exception as e:
            errors += 1
            error_list.append(f'Рядок {index+2}: {str(e)}')
            print(f"  ❌ ПОМИЛКА: {str(e)}")
    
    summary = {
        'created': created,
        'updated': updated,
        'errors': errors,
        'error_list': error_list,
        'price_changes': price_changes,
        'price_increases': price_increases,
        'price_decreases': price_decreases,
        'change_log': change_log,
    }
    
    print(f"\n=== ПІДСУМОК: Створено: {created}, Оновлено: {updated}, Помилок: {errors} ===")
    print(f"💰 Змін цін: {price_changes} (зросло: {price_increases}, зменшилось: {price_decreases})")
    
    import_logger.info(f"Підсумок імпорту: +{created}/~{updated}/!{errors}")
    import_logger.info(f"Зміни цін: +{price_increases}/-{price_decreases}")
    
    return summary


def get_usd_rate():
    try:
        url = 'https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=USD&json'
        response = requests.get(url, timeout=10)
        data = response.json()
        if data and 'rate' in data[0]:
            return float(data[0]['rate'])
    except:
        pass
    return None


def slugify(text):
    from django.utils.text import slugify
    return slugify(text)


def parse_int(value):
    if value is None or str(value).strip() == '' or str(value) == 'nan':
        return 0
    try:
        return int(float(str(value).replace(',', '.')))
    except:
        return 0


@staff_member_required
def export_products(request):
    """Експорт товарів у CSV форматі"""
    
    # Отримуємо всі товари
    products = Product.objects.select_related('category', 'brand').all()
    
    # Створюємо відповідь CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="products_export.csv"'
    
    writer = csv.writer(response)
    
    # Заголовки колонок (українською)
    headers = [
        'ID', 'Артикул', 'Код товару', 'Назва', 'URL', 'Категорія', 'Бренд',
        'Ціна', 'Стара ціна', 'Знижка %', 'Кількість', 'Наявність',
        'Короткий опис', 'Повний опис', 'Гарантія (міс.)', 'Країна виробництва',
        'Рейтинг', 'Кількість відгуків', 'Дата створення', 'Характеристики (JSON)'
    ]
    writer.writerow(headers)
    
    # Записуємо дані
    for product in products:
        row = [
            product.id,
            product.article or '',
            product.code or '',
            product.title,
            product.slug,
            product.category.name if product.category else '',
            product.brand.name if product.brand else '',
            str(product.price),
            str(product.old_price) if product.old_price else '',
            str(product.discount),
            product.quantity,
            'Так' if product.available else 'Ні',
            product.description or '',
            product.full_description or '',
            product.warranty,
            product.country or '',
            str(product.rating),
            product.reviews_count,
            product.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            json.dumps(product.attributes, ensure_ascii=False) if product.attributes else '',
        ]
        writer.writerow(row)
    
    return response


@staff_member_required
def export_products_page(request):
    """Сторінка з інтерфейсом експорту"""
    total_products = Product.objects.count()
    available_products = Product.objects.filter(available=True).count()
    
    context = {
        'total_products': total_products,
        'available_products': available_products,
    }
    return render(request, 'admin/export_products.html', context)


@staff_member_required
def pricelist_settings(request):
    """Сторінка налаштувань та отримання прайс-листа"""
    result = None
    pricelist_url = None
    target_id = request.session.get('pricelist_target_id', '29')
    format_type = request.session.get('pricelist_format', 'xlsx')
    full_type = request.session.get('pricelist_full', '0')
    lang = request.session.get('pricelist_lang', 'ua')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'get_url':
            # Отримання посилання на прайс-лист
            target_id = request.POST.get('target_id', '29')
            format_type = request.POST.get('format', 'xlsx')
            full_type = request.POST.get('full', '0')
            lang = request.POST.get('lang', 'ua')
            
            # Зберігаємо в сесію
            request.session['pricelist_target_id'] = target_id
            request.session['pricelist_format'] = format_type
            request.session['pricelist_full'] = full_type
            request.session['pricelist_lang'] = lang
            
            token = get_token()
            if token:
                pricelist_url = get_pricelist_url(
                    target_id=target_id,
                    format_type=format_type,
                    lang=lang,
                    full=int(full_type),
                    token=token
                )
                if pricelist_url:
                    messages.success(request, '✅ Посилання на прайс-лист отримано!')
                else:
                    messages.error(request, '❌ Не вдалося отримати посилання на прайс-лист')
            else:
                messages.error(request, '❌ Не вдалося отримати токен доступу')
        
        elif action == 'download':
            # Завантаження прайс-листа
            target_id = request.POST.get('target_id', '29')
            format_type = request.POST.get('format', 'xlsx')
            full_type = request.POST.get('full', '0')
            lang = request.POST.get('lang', 'ua')
            
            token = get_token()
            if token:
                file_path, filename = download_pricelist(
                    target_id=target_id,
                    format_type=format_type,
                    lang=lang,
                    full=int(full_type)
                )
                if file_path:
                    messages.success(request, f'✅ Прайс-лист завантажено: {filename}')
                    result = {'file_path': file_path, 'filename': filename}
                else:
                    messages.error(request, '❌ Не вдалося завантажити прайс-лист')
            else:
                messages.error(request, '❌ Не вдалося отримати токен доступу')
    
    context = {
        'target_id': target_id,
        'format_type': format_type,
        'full_type': full_type,
        'lang': lang,
        'pricelist_url': pricelist_url,
        'result': result,
    }
    return render(request, 'admin/pricelist.html', context)


@staff_member_required
def download_pricelist_file(request, filename):
    """Скачування збереженого прайс-листа"""
    file_path = os.path.join(settings.MEDIA_ROOT, 'pricelists', filename)
    
    if os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)
    else:
        messages.error(request, 'Файл не знайдено')
        return redirect('admin:pricelist_settings')
    

@staff_member_required
def service_calculator(request):
    """Калькулятор послуг та комплектуючих"""
    from shop.models import ServiceCategory, LegalEntity
    
    context = {
        'categories': ServiceCategory.objects.filter(is_active=True),
        'legal_entities': LegalEntity.objects.filter(is_active=True),
    }
    return render(request, 'admin/service_calculator.html', context)


@csrf_exempt
@staff_member_required
def generate_invoice_ajax(request):
    """Генерація рахунку через AJAX"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            legal_entity_id = data.get('legal_entity_id')
            items = data.get('items', [])
            
            if not legal_entity_id:
                return JsonResponse({'success': False, 'error': 'Не обрано юридичну особу'})
            
            if not items:
                return JsonResponse({'success': False, 'error': 'Кошик порожній'})
            
            legal_entity = LegalEntity.objects.get(id=legal_entity_id)
            
            # Розрахунок сум
            subtotal = Decimal('0')
            invoice_items = []
            
            for item in items:
                price = Decimal(str(item['price']))
                quantity = Decimal(str(item['quantity']))
                total = price * quantity
                subtotal += total
                
                # Знаходимо послугу/комплектуючу
                service = Service.objects.filter(id=item['id']).first()
                
                invoice_items.append({
                    'service': service,
                    'name': item['name'],
                    'quantity': quantity,
                    'price': price,
                    'total': total,
                })
            
            vat_amount = subtotal * Decimal('0.2')
            total_amount = subtotal + vat_amount
            
            # Створюємо рахунок
            invoice = Invoice.objects.create(
                legal_entity=legal_entity,
                seller='ТОВ "TechShop"',
                seller_code='12345678',
                seller_address='м. Київ, вул. Технічна, 1',
                subtotal=subtotal,
                vat_rate=20,
                vat_amount=vat_amount,
                total_amount=total_amount,
                created_by=request.user.username,
            )
            
            # Додаємо позиції
            for item_data in invoice_items:
                InvoiceItem.objects.create(
                    invoice=invoice,
                    service=item_data['service'],
                    name=item_data['name'],
                    quantity=item_data['quantity'],
                    price=item_data['price'],
                    total=item_data['total'],
                )
            
            return JsonResponse({
                'success': True,
                'invoice_id': invoice.id,
                'invoice_number': invoice.invoice_number,
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Метод не підтримується'})


@staff_member_required
def download_invoice_pdf(request, invoice_id):
    """Завантаження PDF рахунку"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    pdf_buffer = generate_invoice_pdf(invoice, request)
    return FileResponse(
        pdf_buffer,
        as_attachment=True,
        filename=f"рахунок_{invoice.invoice_number}.pdf",
        content_type='application/pdf'
    )


@staff_member_required
def invoice_list(request):
    """Список рахунків"""
    invoices = Invoice.objects.select_related('legal_entity').all()
    return render(request, 'admin/invoice_list.html', {'invoices': invoices})

def get_admin_context(request):
    """Контекст для головної сторінки адмінки"""
    return {
        'recent_invoices': Invoice.objects.select_related('legal_entity').order_by('-invoice_date')[:5],
        'total_orders': Order.objects.count(),
        'total_revenue': Order.objects.filter(is_paid=True).aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'total_customers': User.objects.count(),
        'total_products': Product.objects.filter(available=True).count(),
        'recent_orders': Order.objects.order_by('-created_at')[:10],
    }

@staff_member_required
def download_missing_images(request):
    """Завантаження зображень для товарів без фото"""
    result = None
    
    if request.method == 'POST':
        products = Product.objects.filter(main_image='')
        
        if not products.exists():
            messages.warning(request, 'Немає товарів без зображень')
            return redirect('admin:shop_product_changelist')
        
        token = get_token()
        if not token:
            messages.error(request, '❌ Не вдалося отримати доступ до API')
            return redirect('admin:shop_product_changelist')
        
        success_count = 0
        failed_count = 0
        change_log = []
        error_list = []
        
        for product in products:
            if not product.code:
                failed_count += 1
                error_list.append(f'❌ {product.article}: немає коду товару (code)')
                continue
            
            try:
                # Спроба завантажити зображення
                image_url = get_image_url_by_product_code(product.code)
                if image_url:
                    image_file, filename = save_image_from_url(image_url, product.code, 'main')
                    if image_file:
                        product.main_image.save(filename, image_file, save=True)
                        success_count += 1
                        change_log.append(f'✅ {product.article}: зображення завантажено для "{product.title}"')
                    else:
                        failed_count += 1
                        error_list.append(f'❌ {product.article}: не вдалося зберегти зображення')
                else:
                    failed_count += 1
                    error_list.append(f'❌ {product.article}: не знайдено URL зображення')
            except Exception as e:
                failed_count += 1
                error_list.append(f'❌ {product.article}: {str(e)}')
        
        result = {
            'success': success_count,
            'failed': failed_count,
            'total': products.count(),
            'change_log': change_log,
            'error_list': error_list,
        }
        
        messages.success(request, f'✅ Завантажено зображення для {success_count} товарів')
    
    products_count = Product.objects.filter(main_image='').count()
    
    context = {
        'products_count': products_count,
        'result': result,
    }
    return render(request, 'admin/download_missing_images.html', context)


@staff_member_required
def create_invoice_from_order(request, order_id):
    """Створення рахунку-фактури на основі замовлення"""
    order = get_object_or_404(Order, id=order_id)
    
    # Перевірки
    if not order.legal_entity:
        messages.error(request, f'❌ Замовлення #{order.id}: не обрано юридичну особу')
        return redirect('admin:shop_order_changelist')
    
    if not order.invoice_required:
        messages.warning(request, f'⚠️ Замовлення #{order.id}: не потрібен рахунок-фактура')
        return redirect('admin:shop_order_changelist')
    
    # Перевіряємо, чи вже є рахунок
    existing_invoice = Invoice.objects.filter(order=order).first()
    if existing_invoice:
        messages.warning(request, f'⚠️ Рахунок №{existing_invoice.invoice_number} вже створено для замовлення #{order.id}')
        return redirect('admin:shop_invoice_change', existing_invoice.id)
    
    # Розраховуємо суми
    subtotal = Decimal(str(order.total_amount))
    vat_amount = subtotal * Decimal('0.2')
    total_amount = subtotal + vat_amount
    
    # Створюємо рахунок
    invoice = Invoice.objects.create(
        legal_entity=order.legal_entity,
        order=order,
        subtotal=subtotal,
        vat_amount=vat_amount,
        total_amount=total_amount,
        created_by=request.user.username,
    )
    
    # Додаємо позиції з замовлення
    for item in order.products:
        InvoiceItem.objects.create(
            invoice=invoice,
            name=item.get('name', 'Товар'),
            quantity=Decimal(str(item.get('quantity', 1))),
            price=Decimal(str(item.get('price', 0))),
            total=Decimal(str(item.get('quantity', 1))) * Decimal(str(item.get('price', 0))),
        )
    
    messages.success(request, f'✅ Рахунок №{invoice.invoice_number} створено на основі замовлення #{order.id}')
    
    return redirect('admin:shop_invoice_change', invoice.id)


@staff_member_required
def get_notifications(request):
    """AJAX отримання сповіщень"""
    notifications = AdminNotification.objects.filter(is_read=False)[:20]
    data = {
        'count': notifications.count(),
        'notifications': [
            {
                'id': n.id,
                'type': n.notification_type,
                'title': n.title,
                'message': n.message,
                'link': n.link,
                'created_at': n.created_at.strftime('%d.%m.%Y %H:%M'),
            }
            for n in notifications
        ]
    }
    return JsonResponse(data)


@staff_member_required
def mark_notification_read(request, notification_id):
    """Позначити сповіщення як прочитане"""
    notification = get_object_or_404(AdminNotification, id=notification_id)
    notification.is_read = True
    notification.save()
    return JsonResponse({'success': True})


@staff_member_required
def mark_all_notifications_read(request):
    """Позначити всі сповіщення як прочитані"""
    AdminNotification.objects.filter(is_read=False).update(is_read=True)
    return JsonResponse({'success': True})
