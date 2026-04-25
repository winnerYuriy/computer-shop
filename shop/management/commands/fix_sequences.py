# shop/management/commands/fix_sequences.py

from django.core.management.base import BaseCommand
from django.db import connection
from django.apps import apps


class Command(BaseCommand):
    help = 'Виправляє послідовності ID після відновлення бекапу'

    def handle(self, *args, **options):
        self.stdout.write('🔄 Виправлення послідовностей ID...')
        
        # Список таблиць для виправлення
        tables = [
            'django_admin_log',
            'django_content_type',
            'django_migrations',
            'auth_permission',
            'auth_group',
            'auth_group_permissions',
            'accounts_user',
            'accounts_user_groups',
            'accounts_user_user_permissions',
            'shop_product',
            'shop_category',
            'shop_brand',
            'shop_order',
            'shop_invoice',
            'shop_invoiceitem',
            'shop_legalentity',
            'shop_review',
            'shop_cart',
            'shop_property',
            'shop_propertyvalue',
            'shop_service',
            'shop_servicecategory',
            'shop_recentlyviewed',
            'shop_adminnotification',
            'shop_promotion',
            'shop_productimage',
            'shop_visitlog',
        ]
        
        fixed = 0
        with connection.cursor() as cursor:
            for table in tables:
                try:
                    # Перевіряємо чи існує таблиця
                    cursor.execute(f"""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = '{table}'
                        );
                    """)
                    if not cursor.fetchone()[0]:
                        continue
                    
                    # Отримуємо максимальний ID
                    cursor.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table};")
                    max_id = cursor.fetchone()[0]
                    
                    if max_id > 0:
                        # Скидаємо послідовність
                        cursor.execute(f"SELECT setval('{table}_id_seq', {max_id});")
                        self.stdout.write(f"  ✅ {table}_id_seq → {max_id}")
                        fixed += 1
                    else:
                        # Якщо таблиця порожня, скидаємо до 1
                        cursor.execute(f"SELECT setval('{table}_id_seq', 1);")
                        self.stdout.write(f"  ⚠️ {table} порожня, скинуто до 1")
                        fixed += 1
                except Exception as e:
                    self.stdout.write(f"  ❌ Помилка для {table}: {e}")
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Виправлено {fixed} послідовностей'))