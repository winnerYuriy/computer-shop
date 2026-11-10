# shop/utils.py

from datetime import time
import os
import hashlib
import requests
import logging
from django.core.files.base import ContentFile
import uuid
from django.utils.text import slugify
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO




logger = logging.getLogger(__name__)

HOST = os.getenv('HOST', 'http://api.brain.com.ua')
OPT_HOST = os.getenv('OPT_HOST', 'https://opt.brain.com.ua')


def md5_hash(text):
    """Обчислює MD5 хеш рядка"""
    return hashlib.md5(text.encode()).hexdigest()


def get_token(auth_url=None):
    """Отримує токен авторизації для Brain API"""
    login = os.getenv('BRAIN_LOGIN')
    password = os.getenv('BRAIN_PASSWORD')
    
    if not login or not password:
        logger.error("Не вказані LOGIN або PASSWORD для Brain API")
        return None
    
    if not auth_url:
        auth_url = f'{HOST}/auth'
    
    try:
        r = requests.post(auth_url, data={
            'login': login,
            'password': md5_hash(password)
        }, timeout=30)
        
        if r.status_code == 200:
            res = r.json()
            token = res.get('result', None)
            logger.info(f'Отримано токен Brain: {token}')
            return token
        else:
            logger.error(f'Помилка авторизації: {r.status_code}')
            return None
    except Exception as e:
        logger.error(f'Помилка отримання токена: {e}')
        return None


# ===================================================================
# СПОСІБ 1: Пряме формування URL за кодом товару (без API)
# ===================================================================

def get_image_url_by_product_code(product_code, image_type='full'):
    """
    Формує URL зображення за кодом товару (без API)
    
    Формула: https://opt.brain.com.ua/static/images/prod_img/{предостанній символ}/{останній символ}/{код}.jpg
    
    image_type: 'full', 'large', 'medium', 'small'
    """
    if not product_code:
        return None
    
    code_str = str(product_code).strip()
    if len(code_str) < 2:
        return None
    
    # Останній та передостанній символи
    last_char = code_str[-1]
    second_last_char = code_str[-2]
    
    base_url = f"{OPT_HOST}/static/images/prod_img/{second_last_char}/{last_char}/{code_str}.jpg"
    
    # Для різних типів зображень (якщо потрібно)
    type_suffixes = {
        'full': '',
        'main': '_main',
        'large': '_big',
        'medium': '',
        'small': '_small',
    }
    
    suffix = type_suffixes.get(image_type, '')
    if suffix:
        base_url = base_url.replace('.jpg', f'{suffix}.jpg')
    
    return base_url


def get_all_image_urls_by_product_code(product_code):
    """
    Отримує всі можливі URL зображень за кодом товару (без API)
    """
    if not product_code:
        return []
    
    urls = []
    code_str = str(product_code).strip()
    if len(code_str) < 2:
        return urls
    
    last_char = code_str[-1]
    second_last_char = code_str[-2]
    base_path = f"{OPT_HOST}/static/images/prod_img/{second_last_char}/{last_char}/{code_str}"
    
    # Стандартні типи зображень
    variations = [
        (f"{base_path}.jpg", 'medium'),
        (f"{base_path}_main.jpg", 'full'),
        (f"{base_path}_big.jpg", 'large'),
        (f"{base_path}_small.jpg", 'small'),
    ]
    
    for url, img_type in variations:
        urls.append({'url': url, 'type': img_type})
    
    return urls


# ===================================================================
# СПОСІБ 2: API метод product_pictures (потребує токен та productID)
# ===================================================================

def get_product_images_by_product_id(product_id, token):
    """
    Отримує зображення товару за productID через API
    API: /product_pictures/{productID}/{SID}
    """
    if not token or not product_id:
        return []
    
    url = f'{HOST}/product_pictures/{product_id}/{token}'
    
    try:
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 1 and data.get('result'):
                return data['result']
            else:
                logger.warning(f'API не повернуло зображень: {data}')
                return []
        else:
            logger.warning(f'Помилка API: {response.status_code}')
            return []
    except Exception as e:
        logger.error(f'Помилка отримання зображень: {e}')
        return []


def get_product_data_by_code(product_code, token, lang='ua'):
    """
    Отримує повну інформацію про товар за кодом (включаючи productID)
    API: /product/product_code/{product_code}/{SID}
    """
    if not token or not product_code:
        return None
    
    url = f'{HOST}/product/product_code/{product_code}/{token}'
    
    try:
        response = requests.get(url, params={'lang': lang}, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 1:
                return data.get('result')
        return None
    except Exception as e:
        logger.error(f'Помилка отримання товару {product_code}: {e}')
        return None


# ===================================================================
# ЗАГАЛЬНІ ФУНКЦІЇ ДЛЯ РОБОТИ З ЗОБРАЖЕННЯМИ
# ===================================================================

def save_image_from_url(image_url, product_identifier, image_type='main'):
    """
    Завантажує зображення за URL та зберігає локально
    Повертає (ContentFile, filename) або (None, None)
    """
    if not image_url:
        return None, None
    
    try:
        response = requests.get(image_url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if response.status_code == 200:
            # Визначаємо розширення файлу
            content_type = response.headers.get('content-type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = 'jpg'
            elif 'png' in content_type:
                ext = 'png'
            elif 'webp' in content_type:
                ext = 'webp'
            else:
                ext = 'jpg'
            
            # Генеруємо унікальне ім'я файлу
            filename = f"{slugify(product_identifier)}_{image_type}_{uuid.uuid4().hex[:8]}.{ext}"
            
            # Створюємо ContentFile для збереження
            image_file = ContentFile(response.content, name=filename)
            return image_file, filename
        else:
            logger.warning(f'Не вдалося завантажити зображення: {image_url} (HTTP {response.status_code})')
            return None, None
    except Exception as e:
        logger.error(f'Помилка завантаження зображення {image_url}: {e}')
        return None, None


def download_product_images_by_code(product, token=None):
    """
    Завантажує зображення для товару за його code (product_code)
    
    Пріоритет:
    1. Якщо є token та productID -> використовуємо API product_pictures
    2. Інакше -> формуємо URL за кодом товару
    """
    if not product.code:
        logger.warning(f'Товар {product.id} не має code')
        return False
    
    images_urls = []
    
    # Спосіб 1: через API (якщо є token та productID)
    if token:
        # Спочатку отримуємо productID за code
        product_data = get_product_data_by_code(product.code, token)
        if product_data and product_data.get('productID'):
            product_id = product_data['productID']
            images_data = get_product_images_by_product_id(product_id, token)
            for img in images_data:
                if img.get('full_image'):
                    images_urls.append(img['full_image'])
    
    # Спосіб 2: формуємо URL за кодом (якщо API не дав результатів)
    if not images_urls:
        urls = get_all_image_urls_by_product_code(product.code)
        for url_info in urls:
            images_urls.append(url_info['url'])
    
    if not images_urls:
        logger.warning(f'Не знайдено URL зображень для товару {product.code}')
        return False
    
    # Завантажуємо перше зображення як головне
    main_image_url = images_urls[0]
    image_file, filename = save_image_from_url(main_image_url, product.code, 'main')
    
    if image_file:
        product.main_image.save(filename, image_file, save=True)
        logger.info(f'✅ Зображення завантажено для товару {product.code}')
        return True
    
    return False


def update_product_from_api(product, token):
    """
    Оновлює товар даними з API за його code (product_code)
    """
    if not product.code or not token:
        return False
    
    product_data = get_product_data_by_code(product.code, token)
    
    if not product_data:
        return False
    
    updated = False
    
    # # Оновлюємо ціну
    # if product_data.get('price_uah'):
    #     try:
    #         new_price = float(product_data['price_uah'])
    #         if product.price != new_price:
    #             product.price = new_price
    #             updated = True
    #     except:
    #         pass
    
    # # Оновлюємо стару ціну
    # if product_data.get('retail_price_uah'):
    #     try:
    #         new_old_price = float(product_data['retail_price_uah'])
    #         if product.old_price != new_old_price:
    #             product.old_price = new_old_price
    #             updated = True
    #     except:
    #         pass
    
    # Оновлюємо кількість
    if product_data.get('available'):
        try:
            available_data = product_data['available']
            if isinstance(available_data, dict):
                total_quantity = sum(available_data.values())
                if product.quantity != total_quantity:
                    product.quantity = total_quantity
                    product.available = total_quantity > 0
                    updated = True
        except:
            pass
    
    # Оновлюємо гарантію
    if product_data.get('warranty'):
        try:
            new_warranty = int(product_data['warranty'])
            if product.warranty != new_warranty:
                product.warranty = new_warranty
                updated = True
        except:
            pass
    
    # Оновлюємо країну
    if product_data.get('country'):
        new_country = product_data['country']
        if product.country != new_country:
            product.country = new_country
            updated = True
    
    # Оновлюємо додаткові характеристики
    if product_data.get('options'):
        options_dict = {}
        for opt in product_data['options']:
            options_dict[opt.get('name', '')] = opt.get('value', '')
        
        current_attrs = product.attributes or {}
        if current_attrs.get('brain_options') != options_dict:
            current_attrs['brain_options'] = options_dict
            product.attributes = current_attrs
            updated = True
    
    if updated:
        product.save()
        logger.info(f'✅ Оновлено товар {product.code} з API')
    
    return updated

# ===================================================================
# ФУНКЦІЇ ДЛЯ РОБОТИ З ПРАЙС-ЛИСТАМИ
# ===================================================================

def get_pricelist_url(target_id, format_type='xlsx', lang='ua', full=0, token=None):
    """
    Отримує посилання на прайс-лист з Brain API
    
    Параметри:
    - target_id: ID пункту видачі (обов'язково)
    - format_type: формат (xml, xlsx, xls, json, php)
    - lang: мова (ua, ru)
    - full: 0 - тільки локальний склад, 1 - вся наявність, 2 - короткий прайс
    - token: токен авторизації (якщо не вказано, отримуємо новий)
    """
    if not token:
        token = get_token()
        if not token:
            logger.error("Не вдалося отримати токен для запиту прайс-листа")
            return None
    
    url = f'{HOST}/pricelists/{target_id}/{format_type}/{token}'
    
    params = {
        'lang': lang,
        'full': full
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 1 and data.get('url'):
                return data['url']
            else:
                logger.error(f"API повернуло помилку: {data}")
                return None
        else:
            logger.error(f"Помилка API: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Помилка отримання прайс-листа: {e}")
        return None


def download_pricelist(target_id, format_type='xlsx', lang='ua', full=0, save_path=None):
    """
    Завантажує прайс-лист та зберігає локально
    
    Повертає шлях до збереженого файлу або None
    """
    pricelist_url = get_pricelist_url(target_id, format_type, lang, full)
    
    if not pricelist_url:
        return None
    
    try:
        response = requests.get(pricelist_url, timeout=60)
        
        if response.status_code == 200:
            # Визначаємо розширення файлу
            ext = format_type if format_type != 'xlsx' else 'xlsx'
            
            # Формуємо ім'я файлу
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filename = f"pricelist_{target_id}_{timestamp}.{ext}"
            
            if save_path is None:
                save_path = os.path.join(settings.MEDIA_ROOT, 'pricelists')
            
            # Створюємо директорію, якщо її немає
            os.makedirs(save_path, exist_ok=True)
            
            # Повний шлях до файлу
            file_path = os.path.join(save_path, filename)
            
            # Зберігаємо файл
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"✅ Прайс-лист збережено: {file_path}")
            return file_path, filename
        else:
            logger.error(f"Помилка завантаження прайс-листа: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Помилка збереження прайс-листа: {e}")
        return None

# ============================================================
# ГЕНЕРАЦІЯ PDF ДОКУМЕНТІВ
# ============================================================


def generate_invoice_pdf(invoice, request=None):
    """
    Генерує PDF-файл рахунку-фактури
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    elements = []
    
    # Стилі для української мови
    styles.add(ParagraphStyle(
        name='UkrainianTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=1,  # Центр
        spaceAfter=20
    ))
    
    styles.add(ParagraphStyle(
        name='UkrainianNormal',
        parent=styles['Normal'],
        fontSize=10,
        leading=12
    ))
    
    # Заголовок
    elements.append(Paragraph("РАХУНОК-ФАКТУРА", styles['UkrainianTitle']))
    elements.append(Spacer(1, 10))
    
    # Інформація про рахунок
    info_data = [
        [Paragraph(f"<b>№ {invoice.invoice_number}</b>", styles['UkrainianNormal']),
         Paragraph(f"<b>від {invoice.invoice_date.strftime('%d.%m.%Y')}</b>", styles['UkrainianNormal'])],
    ]
    info_table = Table(info_data, colWidths=[250, 250])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 15))
    
    # Продавець
    elements.append(Paragraph("<b>ПРОДАВЕЦЬ:</b>", styles['UkrainianNormal']))
    elements.append(Paragraph(invoice.seller, styles['UkrainianNormal']))
    elements.append(Paragraph(f"Код ЄДРПОУ: {invoice.seller_code}", styles['UkrainianNormal']))
    elements.append(Paragraph(f"Місцезнаходження: {invoice.seller_address}", styles['UkrainianNormal']))
    elements.append(Spacer(1, 15))
    
    # Покупець
    elements.append(Paragraph("<b>ПОКУПЕЦЬ:</b>", styles['UkrainianNormal']))
    elements.append(Paragraph(invoice.legal_entity.name, styles['UkrainianNormal']))
    elements.append(Paragraph(f"Код ЄДРПОУ: {invoice.legal_entity.code_edrpou}", styles['UkrainianNormal']))
    elements.append(Paragraph(f"Місцезнаходження: {invoice.legal_entity.legal_address or invoice.legal_entity.actual_address}", styles['UkrainianNormal']))
    elements.append(Spacer(1, 15))
    
    # Таблиця товарів/послуг
    table_data = [
        ['№', 'Найменування товарів/послуг', 'Кількість', 'Од.', 'Ціна', 'Сума']
    ]
    
    for idx, item in enumerate(invoice.items.all(), 1):
        table_data.append([
            str(idx),
            Paragraph(item.name, styles['UkrainianNormal']),
            str(item.quantity),
            item.unit,
            f"{item.price:.2f}",
            f"{item.total:.2f}"
        ])
    
    # Підсумки
    table_data.append(['', '', '', '', 'ВСЬОГО:', f"{invoice.subtotal:.2f}"])
    table_data.append(['', '', '', '', 'БЕЗ ПДВ:', f"{invoice.vat_amount:.2f}"])
    table_data.append(['', '', '', '', 'ВСЬОГО ДО ОПЛАТИ:', f"{invoice.total_amount:.2f}"])
    
    table = Table(table_data, colWidths=[30, 250, 50, 40, 60, 70])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -4), colors.beige),
        ('BACKGROUND', (0, -3), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
        ('TOPPADDING', (0, -3), (-1, -1), 6),
        ('BOTTOMPADDING', (0, -3), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -4), 0.5, colors.grey),
        ('BOX', (0, -3), (-1, -1), 0.5, colors.grey),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    # Банківські реквізити
    elements.append(Paragraph("<b>Банківські реквізити:</b>", styles['UkrainianNormal']))
    elements.append(Paragraph(f"Банк: {invoice.legal_entity.bank_name or 'Не вказано'}", styles['UkrainianNormal']))
    elements.append(Paragraph(f"Розрахунковий рахунок: {invoice.legal_entity.bank_account or 'Не вказано'}", styles['UkrainianNormal']))
    elements.append(Paragraph(f"МФО: {invoice.legal_entity.bank_mfo or 'Не вказано'}", styles['UkrainianNormal']))
    elements.append(Spacer(1, 20))
    
    # Підписи
    elements.append(Paragraph("Підпис керівника: ___________________", styles['UkrainianNormal']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Підпис головного бухгалтера: ___________________", styles['UkrainianNormal']))
    
    # Генерація PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer