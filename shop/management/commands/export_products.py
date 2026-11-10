import pandas as pd
from django.core.management.base import BaseCommand
from shop.models import Product


class Command(BaseCommand):
    help = 'Експорт товарів у Excel файл'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Шлях для збереження Excel файлу')

    def handle(self, *args, **options):
        file_path = options['file_path']

        products = Product.objects.all().select_related('category', 'brand')

        data = []
        for product in products:
            data.append({
                'title': product.title,
                'category': product.category.name if product.category else '',
                'brand': product.brand.name if product.brand else '',
                'price': float(product.price),
                'quantity': product.quantity,
                'description': product.description,
                'full_description': product.full_description,
                'article': product.article,
                'code': product.code,
                'old_price': float(product.old_price) if product.old_price else '',
                'discount': product.discount,
                'warranty': product.warranty,
                'country': product.country,
                'promotions': ', '.join([p.name for p in product.promotions.all()]),
                'attributes': product.attributes,
            })

        df = pd.DataFrame(data)
        df.to_excel(file_path, index=False)

        self.stdout.write(self.style.SUCCESS(f'✅ Експортовано {len(data)} товарів у {file_path}'))