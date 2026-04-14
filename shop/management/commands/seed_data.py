# shop/management/commands/seed_data.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from shop.models import (
    Category, Brand, Promotion, Product, ProductImage,
    Property, PropertyValue
)


class Command(BaseCommand):
    help = 'Наповнює базу даних тестовими даними для нової структури магазину'

    def handle(self, *args, **options):
        self.stdout.write('Починаємо наповнення бази даних...')

        # ========== 1. Бренди ==========
        self.stdout.write('1. Створюємо бренди...')
        brands_data = [
            {'name': 'ASUS', 'slug': 'asus'},
            {'name': 'Dell', 'slug': 'dell'},
            {'name': 'HP', 'slug': 'hp'},
            {'name': 'Lenovo', 'slug': 'lenovo'},
            {'name': 'Apple', 'slug': 'apple'},
            {'name': 'A4Tech', 'slug': 'a4tech'},
            {'name': 'Logitech', 'slug': 'logitech'},
        ]
        brand_objs = {}
        for data in brands_data:
            brand, created = Brand.objects.get_or_create(slug=data['slug'], defaults=data)
            brand_objs[data['slug']] = brand
            if created:
                self.stdout.write(f'   ✓ Створено бренд: {brand.name}')
        self.stdout.write(f'   ✓ Брендів: {Brand.objects.count()}')

        # ========== 2. Акції (Promotions) ==========
        self.stdout.write('2. Створюємо акції...')
        now = timezone.now()
        promotions_data = [
            {'name': 'Новинка', 'slug': 'new', 'promotion_type': 'new', 'discount_percent': 0,
             'start_date': now - timezone.timedelta(days=30), 'end_date': now + timezone.timedelta(days=365)},
            {'name': 'Хіт продажів', 'slug': 'bestseller', 'promotion_type': 'bestseller', 'discount_percent': 0,
             'start_date': now - timezone.timedelta(days=30), 'end_date': now + timezone.timedelta(days=365)},
            {'name': 'Розпродаж', 'slug': 'sale', 'promotion_type': 'sale', 'discount_percent': 15,
             'start_date': now - timezone.timedelta(days=10), 'end_date': now + timezone.timedelta(days=20)},
            {'name': 'Знижка на мишки', 'slug': 'mouse-discount', 'promotion_type': 'discount', 'discount_percent': 10,
             'start_date': now - timezone.timedelta(days=5), 'end_date': now + timezone.timedelta(days=15)},
        ]
        promo_objs = {}
        for data in promotions_data:
            promo, created = Promotion.objects.get_or_create(slug=data['slug'], defaults=data)
            promo_objs[data['slug']] = promo
            if created:
                self.stdout.write(f'   ✓ Створено акцію: {promo.name}')
        self.stdout.write(f'   ✓ Акцій: {Promotion.objects.count()}')

        # ========== 3. Категорії (MPTT) ==========
        self.stdout.write('3. Створюємо категорії...')
        # Кореневі категорії (рівень 0)
        root_cats = {}
        root_data = [
            {'name': 'Ноутбуки та комп\'ютери', 'slug': 'notebooks'},
            {'name': 'Периферія', 'slug': 'peripherals'},
            {'name': 'Мережеве обладнання', 'slug': 'networking'},
            {'name': 'Офісне приладдя', 'slug': 'office'},
        ]
        for data in root_data:
            cat, created = Category.objects.get_or_create(slug=data['slug'], defaults={'name': data['name']})
            root_cats[data['slug']] = cat
            if created:
                self.stdout.write(f'   ✓ Створено категорію: {cat.name}')

        # Підкатегорії
        subcats_data = [
            # Ноутбуки та комп'ютери
            {'name': 'Ноутбуки', 'slug': 'laptops', 'parent_slug': 'notebooks'},
            {'name': 'Ігрові ноутбуки', 'slug': 'gaming-laptops', 'parent_slug': 'laptops'},
            {'name': 'Офісні ноутбуки', 'slug': 'office-laptops', 'parent_slug': 'laptops'},
            {'name': 'Моноблоки', 'slug': 'all-in-one', 'parent_slug': 'notebooks'},
            {'name': 'Системні блоки', 'slug': 'pcs', 'parent_slug': 'notebooks'},
            # Периферія
            {'name': 'Мишки', 'slug': 'mice', 'parent_slug': 'peripherals'},
            {'name': 'Клавіатури', 'slug': 'keyboards', 'parent_slug': 'peripherals'},
            {'name': 'Монітори', 'slug': 'monitors', 'parent_slug': 'peripherals'},
            {'name': 'Навушники', 'slug': 'headphones', 'parent_slug': 'peripherals'},
        ]
        for data in subcats_data:
            parent = root_cats.get(data['parent_slug']) or Category.objects.get(slug=data['parent_slug'])
            cat, created = Category.objects.get_or_create(
                slug=data['slug'],
                defaults={
                    'name': data['name'],
                    'parent': parent
                }
            )
            if created:
                self.stdout.write(f'   ✓ Створено підкатегорію: {cat.name} (батько: {parent.name})')
        self.stdout.write(f'   ✓ Категорій: {Category.objects.count()}')

        # ========== 4. Властивості (характеристики) ==========
        self.stdout.write('4. Створюємо властивості...')
        properties_data = [
            {'name': 'Бренд', 'slug': 'brand'},
            {'name': 'Колір', 'slug': 'color'},
            {'name': 'Оперативна пам\'ять (GB)', 'slug': 'ram'},
            {'name': 'Накопичувач', 'slug': 'storage'},
            {'name': 'Процесор', 'slug': 'cpu'},
            {'name': 'Діагональ екрану (")', 'slug': 'screen-size'},
        ]
        prop_objs = {}
        for data in properties_data:
            prop, created = Property.objects.get_or_create(slug=data['slug'], defaults={'name': data['name']})
            prop_objs[data['slug']] = prop
            if created:
                self.stdout.write(f'   ✓ Створено властивість: {prop.name}')

        # Значення властивостей
        self.stdout.write('   Додаємо значення властивостей...')
        prop_values_data = [
            ('brand', 'ASUS'), ('brand', 'Dell'), ('brand', 'Logitech'), ('brand', 'A4Tech'),
            ('color', 'Чорний'), ('color', 'Білий'), ('color', 'Сірий'),
            ('ram', '8'), ('ram', '16'), ('ram', '32'),
            ('storage', '256GB SSD'), ('storage', '512GB SSD'), ('storage', '1TB SSD'),
            ('cpu', 'Intel Core i5'), ('cpu', 'Intel Core i7'), ('cpu', 'AMD Ryzen 5'),
            ('screen-size', '13.3'), ('screen-size', '15.6'), ('screen-size', '27'),
        ]
        for slug, value in prop_values_data:
            prop = prop_objs.get(slug)
            if prop:
                pv, created = PropertyValue.objects.get_or_create(property=prop, value=value)
                if created:
                    self.stdout.write(f'      - {prop.name}: {value}')
        self.stdout.write(f'   ✓ Значень властивостей: {PropertyValue.objects.count()}')

        # ========== 5. Товари ==========
        self.stdout.write('5. Створюємо товари...')
        products_data = [
            {
                'title': 'Ноутбук ASUS VivoBook 15',
                'slug': 'asus-vivobook-15',
                'category_slug': 'office-laptops',
                'brand_slug': 'asus',
                'price': Decimal('18999'),
                'old_price': Decimal('15999'),
                'quantity': 25,
                'available': True,
                'description': 'Потужний ноутбук для роботи та навчання.',
                'full_description': 'Intel Core i5, 16GB RAM, 512GB SSD, Windows 11.',
                'promotions': ['new'],
                'main_image': 'products/asus_vivobook_15.jpg',  # Файл має бути в media/
                'additional_images': ['products/asus_vivobook_15_2.jpg', 'products/asus_vivobook_15_3.jpg'],
                'property_values': [('brand', 'ASUS'), ('ram', '16'), ('storage', '512GB SSD'), ('cpu', 'Intel Core i5')]
            },
            {
                'title': 'Мишка A4Tech Bloody V7M',
                'slug': 'a4tech-bloody-v7m',
                'category_slug': 'mice',
                'brand_slug': 'a4tech',
                'price': Decimal('899'),
                'quantity': 50,
                'available': True,
                'description': 'Ігрова мишка з підсвіткою та додатковими кнопками.',
                'promotions': ['bestseller'],
                'main_image': 'products/a4tech_bloody_v7m.jpg',
                'property_values': [('brand', 'A4Tech'), ('color', 'Чорний')]
            },
            {
                'title': 'Мишка Logitech MX Master 3',
                'slug': 'logitech-mx-master-3',
                'category_slug': 'mice',
                'brand_slug': 'logitech',
                'price': Decimal('3999'),
                'old_price': Decimal('3499'),
                'quantity': 30,
                'available': True,
                'description': 'Бездротова мишка для професіоналів.',
                'promotions': ['new'],
                'main_image': 'products/logitech_mx_master_3.jpg',
                'property_values': [('brand', 'Logitech'), ('color', 'Сірий')]
            },
            {
                'title': 'Монітор Dell 27" S2721H',
                'slug': 'dell-s2721h',
                'category_slug': 'monitors',
                'brand_slug': 'dell',
                'price': Decimal('8999'),
                'quantity': 15,
                'available': True,
                'description': '27-дюймовий IPS монітор для роботи та розваг.',
                'promotions': [],
                'main_image': 'products/dell_s2721h.jpg',
                'property_values': [('brand', 'Dell'), ('screen-size', '27'), ('color', 'Чорний')]
            },
        ]

        for data in products_data:
            # Отримуємо категорію та бренд
            category = Category.objects.get(slug=data['category_slug'])
            brand = Brand.objects.get(slug=data['brand_slug'])
            # Створюємо або оновлюємо товар
            product, created = Product.objects.get_or_create(
                slug=data['slug'],
                defaults={
                    'title': data['title'],
                    'category': category,
                    'brand': brand,
                    'price': data['price'],
                    'old_price': data.get('old_price'),
                    'quantity': data['quantity'],
                    'available': data['available'],
                    'description': data['description'],
                    'full_description': data.get('full_description', ''),
                }
            )
            if created:
                self.stdout.write(f'   ✓ Створено товар: {product.title}')
            else:
                self.stdout.write(f'   ! Товар вже існує: {product.title}')

            # Додаємо акції
            for promo_slug in data.get('promotions', []):
                promo = promo_objs.get(promo_slug)
                if promo:
                    product.promotions.add(promo)

            # Додаємо значення властивостей
            for prop_slug, value in data.get('property_values', []):
                try:
                    prop = prop_objs[prop_slug]
                    prop_value = PropertyValue.objects.get(property=prop, value=value)
                    product.property_values.add(prop_value)
                except (KeyError, PropertyValue.DoesNotExist):
                    pass

            # Додаємо зображення (якщо є файли, потрібно їх фізично завантажити)
            # Тут ми просто створюємо записи ProductImage, але файли мають існувати в media/products/
            if data.get('main_image'):
                product.main_image = data['main_image']
                product.save(update_fields=['main_image'])

            for idx, img_path in enumerate(data.get('additional_images', [])):
                ProductImage.objects.get_or_create(
                    product=product,
                    order=idx,
                    defaults={'image': img_path, 'alt_text': f'{product.title} фото {idx+1}'}
                )

        self.stdout.write(f'   ✓ Товарів: {Product.objects.count()}')

        # ========== 6. Суперкористувач ==========
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
            self.stdout.write('   ✓ Створено суперкористувача (логін: admin, пароль: admin123)')
        else:
            self.stdout.write('   ✓ Суперкористувач вже існує')

        self.stdout.write(self.style.SUCCESS('✅ Базу даних успішно наповнено тестовими даними!'))