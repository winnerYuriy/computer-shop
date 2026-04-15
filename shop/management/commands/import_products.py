# shop/management/commands/import_products.py

import pandas as pd
from django.core.management.base import BaseCommand
from django.core.files import File
from django.utils.text import slugify
from shop.models import Product, Category, Brand, Promotion, ProductImage
from decimal import Decimal
import os
from django.conf import settings


class Command(BaseCommand):
    help = 'Імпорт товарів з Excel файлу'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Шлях до Excel файлу')
        parser.add_argument('--update', action='store_true', help='Оновлювати існуючі товари')

    def handle(self, *args, **options):
        file_path = options['file_path']
        update_existing = options['update']

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'Файл не знайдено: {file_path}'))
            return

        self.stdout.write(f'Читання файлу: {file_path}')
        
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Помилка читання файлу: {e}'))
            return

        # Очікувані колонки
        expected_columns = [
            'title', 'category', 'brand', 'price', 'quantity', 
            'description', 'full_description', 'article', 'code',
            'old_price', 'discount', 'warranty', 'country',
            'promotions', 'attributes', 'main_image_url'
        ]

        # Перевіряємо наявність колонок
        for col in expected_columns:
            if col not in df.columns:
                self.stdout.write(self.style.WARNING(f'Колонка "{col}" відсутня, буде пропущена'))

        created_count = 0
        updated_count = 0
        error_count = 0

        for index, row in df.iterrows():
            try:
                # Отримуємо або створюємо категорію
                category_name = row.get('category', '')
                if not category_name:
                    self.stdout.write(self.style.WARNING(f'Рядок {index+2}: пропущено категорію'))
                    continue

                category, _ = Category.objects.get_or_create(
                    name=category_name,
                    defaults={'slug': slugify(category_name)}
                )

                # Отримуємо або створюємо бренд
                brand_name = row.get('brand', '')
                if brand_name:
                    brand, _ = Brand.objects.get_or_create(
                        name=brand_name,
                        defaults={'slug': slugify(brand_name)}
                    )
                else:
                    brand = None

                # Slug для товару
                base_slug = slugify(row['title'])
                slug = base_slug
                counter = 1
                while Product.objects.filter(slug=slug).exists() and not update_existing:
                    slug = f"{base_slug}-{counter}"
                    counter += 1

                # Дані товару
                product_data = {
                    'title': row['title'],
                    'slug': slug,
                    'category': category,
                    'brand': brand,
                    'price': Decimal(str(row.get('price', 0))),
                    'quantity': int(row.get('quantity', 0)),
                    'available': int(row.get('quantity', 0)) > 0,
                    'description': row.get('description', ''),
                    'full_description': row.get('full_description', ''),
                    'article': row.get('article', ''),
                    'code': row.get('code', ''),
                    'old_price': Decimal(str(row.get('old_price', 0))) if row.get('old_price') else None,
                    'discount': int(row.get('discount', 0)),
                    'warranty': int(row.get('warranty', 0)),
                    'country': row.get('country', ''),
                }

                # Оновлюємо або створюємо товар
                product, created = Product.objects.update_or_create(
                    slug=slug,
                    defaults=product_data
                ) if update_existing else Product.objects.get_or_create(
                    slug=slug,
                    defaults=product_data
                )

                # Додаємо акції
                promotions_str = row.get('promotions', '')
                if promotions_str:
                    promo_names = [p.strip() for p in promotions_str.split(',')]
                    for promo_name in promo_names:
                        promo, _ = Promotion.objects.get_or_create(
                            name=promo_name,
                            defaults={
                                'slug': slugify(promo_name),
                                'promotion_type': 'sale',
                                'start_date': timezone.now(),
                                'end_date': timezone.now() + timezone.timedelta(days=365)
                            }
                        )
                        product.promotions.add(promo)

                # Додаємо атрибути (JSON)
                attributes_str = row.get('attributes', '')
                if attributes_str:
                    try:
                        import json
                        product.attributes = json.loads(attributes_str)
                        product.save(update_fields=['attributes'])
                    except:
                        pass

                # Додаємо головне зображення (якщо вказано URL)
                main_image_url = row.get('main_image_url', '')
                if main_image_url and not product.main_image:
                    # Тут можна завантажити зображення за URL
                    # Або просто вказати шлях
                    product.main_image = main_image_url
                    product.save(update_fields=['main_image'])

                if created:
                    created_count += 1
                    self.stdout.write(f'  ✓ Створено: {product.title}')
                else:
                    updated_count += 1
                    self.stdout.write(f'  ✓ Оновлено: {product.title}')

            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'Помилка в рядку {index+2}: {e}'))

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Імпорт завершено! Створено: {created_count}, Оновлено: {updated_count}, Помилок: {error_count}'
        ))