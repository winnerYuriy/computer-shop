import os
import hashlib
import requests
import logging
import uuid
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.files.base import ContentFile
from django.utils.text import slugify

from shop.models import Product, Category, Brand
import pandas as pd

# Налаштування логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Константи
HOST = os.getenv('BRAIN_HOST', 'https://brain.example.com')


def md5_hash(text):
    """Обчислює MD5 хеш рядка"""
    return hashlib.md5(text.encode()).hexdigest()


def get_token():
    """Отримує токен авторизації для Brain API"""
    login = os.getenv('BRAIN_LOGIN')
    password = os.getenv('BRAIN_PASSWORD')

    if not login or not password:
        logger.error("Не вказані LOGIN або PASSWORD для Brain API")
        return None

    try:
        r = requests.post(f'{HOST}/auth', data={
            'login': login,
            'password': md5_hash(password)
        }, timeout=30)

        res = r.json()
        token = res.get('result')
        if token:
            logger.info("✅ Токен Brain API успішно отримано")
        else:
            logger.warning("⚠️ Не вдалося отримати токен Brain API")
        return token
    except Exception as e:
        logger.error(f'Помилка отримання токена: {e}')
        return None


def save_image_from_url(image_url, product_article, product_id):
    """Завантажує зображення за URL і повертає (ContentFile, filename)"""
    if not image_url:
        return None, None

    try:
        response = requests.get(image_url, timeout=30)
        if response.status_code != 200:
            logger.warning(f'Не вдалося завантажити зображення: {image_url}')
            return None, None

        # Визначення розширення
        content_type = response.headers.get('content-type', '')
        ext = 'jpg'
        if 'png' in content_type:
            ext = 'png'
        elif 'webp' in content_type:
            ext = 'webp'

        filename = f"{slugify(product_article)}_{product_id}_{uuid.uuid4().hex[:8]}.{ext}"
        image_file = ContentFile(response.content, name=filename)
        return image_file, filename

    except Exception as e:
        logger.error(f'Помилка завантаження зображення {image_url}: {e}')
        return None, None


class Command(BaseCommand):
    help = 'Імпорт товарів з Excel-файлу (ціна продажу з колонки RetailPrice)'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help='Шлях до Excel-файлу')
        parser.add_argument('--update_existing', action='store_true', help='Оновлювати існуючі товари')
        parser.add_argument('--no_images', action='store_true', help='Пропустити завантаження зображень')
        parser.add_argument('--product_id_col', type=str, default='ProductID', help='Колонка з ID товару в Brain')
        parser.add_argument('--debug_prices', action='store_true', help='Показати детальну діагностику цін')

    def handle(self, *args, **options):
        file_path = options['file']
        update_existing = options['update_existing']
        no_images = options['no_images']
        product_id_col = options['product_id_col']
        debug_prices = options['debug_prices']

        if not os.path.exists(file_path):
            self.stderr.write(self.style.ERROR(f'Файл не знайдено: {file_path}'))
            return

        # Отримання токена (тільки якщо завантажуємо зображення)
        token = None
        if not no_images:
            token = get_token()

        # Читання Excel
        try:
            df = pd.read_excel(file_path, dtype=str)
            df = df.fillna('')  # замінюємо NaN на порожній рядок
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Помилка читання Excel: {e}'))
            return

        # Виведення всіх колонок для діагностики
        self.stdout.write(self.style.SUCCESS(f'\n📋 Колонки в Excel-файлі:'))
        for col in df.columns:
            self.stdout.write(f'   - {col}')

        required_columns = ['Article', 'Name', 'RetailPrice', 'CategoryName']
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            self.stderr.write(self.style.ERROR(f'Відсутні обов’язкові колонки: {missing}'))
            return

        created = 0
        updated = 0
        errors = 0

        for index, row in df.iterrows():
            try:
                with transaction.atomic():
                    article = str(row.get('Article', '')).strip()
                    if not article or article.lower() == 'nan':
                        errors += 1
                        continue

                    title = str(row.get('Name', '')).strip()[:250]
                    category_name = str(row.get('CategoryName', '')).strip()
                    vendor_name = str(row.get('Vendor', '')).strip()

                    # =========================================================
                    # ДІАГНОСТИКА ЦІН (виводимо ВСІ можливі джерела)
                    # =========================================================
                    if debug_prices:
                        self.stdout.write(self.style.WARNING(f'\n🔍 Діагностика цін для артикула: {article}'))
                        
                        # Всі можливі колонки з цінами
                        price_columns = ['RetailPrice', 'PriceUAH', 'PriceUSD', 'RecommendedPrice']
                        
                        for pc in price_columns:
                            if pc in df.columns:
                                raw_value = row.get(pc, '')
                                self.stdout.write(f'   📊 {pc}: "{raw_value}"')
                                
                                # Спробуємо розпарсити
                                try:
                                    val_str = str(raw_value).strip().replace(',', '.').replace(' ', '')
                                    if val_str and val_str.lower() != 'nan':
                                        val_decimal = Decimal(val_str)
                                        self.stdout.write(f'      → Decimal: {val_decimal}')
                                        self.stdout.write(f'      → Заокруглено: {val_decimal.quantize(Decimal("1"), rounding="ROUND_HALF_UP")}')
                                except Exception as e:
                                    self.stdout.write(f'      → Помилка: {e}')
                            else:
                                self.stdout.write(f'   📊 {pc}: (колонка відсутня)')
                    
                    # =========================================================
                    # ЦІНА ПРОДАЖУ (тільки з RetailPrice)
                    # =========================================================
                    retail_price_str = str(row.get('RetailPrice', '0')).strip().replace(',', '.').replace(' ', '')
                    
                    # Додаткова очистка від нецифрових символів (крім крапки)
                    import re
                    retail_price_str = re.sub(r'[^\d.]', '', retail_price_str)
                    
                    self.stdout.write(f'\n💰 Артикул: {article}')
                    self.stdout.write(f'   Сире RetailPrice: "{row.get("RetailPrice", "не знайдено")}"')
                    self.stdout.write(f'   Після очищення: "{retail_price_str}"')
                    
                    try:
                        if retail_price_str and retail_price_str.lower() != 'nan' and retail_price_str != '':
                            price_decimal = Decimal(retail_price_str)
                            # Заокруглюємо до цілого числа
                            price = price_decimal.quantize(Decimal('1'), rounding='ROUND_HALF_UP')
                            self.stdout.write(f'   ✅ Кінцева ціна: {price}₴ (заокруглено з {price_decimal})')
                        else:
                            price = Decimal('0')
                            self.stdout.write(self.style.WARNING(f'   ⚠️ RetailPrice порожній або 0, встановлено 0'))
                    except Exception as e:
                        price = Decimal('0')
                        self.stdout.write(self.style.ERROR(f'   ❌ Помилка парсингу: {e}'))

                    # =========================================================
                    # Категорія
                    # =========================================================
                    category, _ = Category.objects.get_or_create(
                        name=category_name or 'Без категорії',
                        defaults={'slug': slugify(category_name or 'bez-kategorii')}
                    )

                    # =========================================================
                    # Бренд
                    # =========================================================
                    brand = None
                    if vendor_name and vendor_name.lower() != 'nan':
                        brand_slug = slugify(vendor_name)
                        brand, _ = Brand.objects.get_or_create(
                            name=vendor_name,
                            defaults={'slug': brand_slug}
                        )

                    # =========================================================
                    # Пошук або створення товару
                    # =========================================================
                    product = None
                    if update_existing:
                        product = Product.objects.filter(article=article).first()
                        
                        if product and debug_prices:
                            self.stdout.write(f'   📊 Поточна ціна в БД: {product.price}₴')
                            if product.price != price:
                                self.stdout.write(self.style.WARNING(f'   ⚠️ Ціна змінюється: {product.price} → {price}₴'))

                    if product:
                        # Оновлення
                        product.category = category
                        product.brand = brand
                        product.title = title
                        product.price = price
                        product.article = article
                        product.save()
                        updated += 1
                        self.stdout.write(self.style.SUCCESS(f'   ✅ Оновлено: {article} - {title} (ціна: {price}₴)'))
                    else:
                        # Створення
                        product = Product.objects.create(
                            category=category,
                            brand=brand,
                            title=title,
                            article=article,
                            price=price,
                        )
                        created += 1
                        self.stdout.write(self.style.SUCCESS(f'   ✨ Створено: {article} - {title} (ціна: {price}₴)'))

                    # =========================================================
                    # Завантаження зображень
                    # =========================================================
                    if token and not no_images:
                        product_id_brain = str(row.get(product_id_col, '')).strip()
                        if product_id_brain and product_id_brain.lower() != 'nan':
                            self.process_product_images(product, product_id_brain, token)

            except Exception as e:
                self.stderr.write(self.style.ERROR(f'   ❌ Рядок {index + 2}: помилка - {str(e)}'))
                errors += 1

        # Підсумок
        self.stdout.write(self.style.SUCCESS(
            f'\n📊 Імпорт завершено! Створено: {created}, Оновлено: {updated}, Помилок: {errors}'
        ))

    def process_product_images(self, product, product_id_brain, token):
        """Завантажує зображення товару (головне + галерея)"""
        if has_main_image(product):
            logger.info(f'⏭️ Пропускаємо зображення для {product.article} — вже є')
            return

        images_data = self.download_product_images(product_id_brain, token)
        if not images_data or not isinstance(images_data, list):
            return

        image_urls = [img for img in images_data if isinstance(img, str) and img.startswith('http')]
        if not image_urls:
            return

        # Головне зображення
        main_file, main_filename = save_image_from_url(image_urls[0], product.article, product.id)
        if main_file:
            product.main_image.save(main_filename, main_file, save=True)
            logger.info(f'🖼️ Головне зображення додано для {product.article}')

        # Галерея (перші 5)
        if not product.gallery_images:
            gallery_paths = []
            for idx, url in enumerate(image_urls[1:6], 1):
                file, filename = save_image_from_url(url, f"{product.article}_gal_{idx}", product.id)
                if file:
                    gallery_paths.append(f"products/gallery/{filename}")
            if gallery_paths:
                product.gallery_images = gallery_paths
                product.save(update_fields=['gallery_images'])

    def download_product_images(self, product_id, token):
        if not token:
            return None
        try:
            url = f'{HOST}/product_pictures/{product_id}/{token}'
            r = requests.get(url, timeout=30)
            return r.json() if r.status_code == 200 else None
        except Exception as e:
            logger.error(f'Помилка завантаження зображень для {product_id}: {e}')
            return None


def has_main_image(product):
    return bool(product.main_image and product.main_image.name)