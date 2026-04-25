# shop/management/commands/fix_admin_log.py

from django.core.management.base import BaseCommand
from django.db import connection
from django.contrib.admin.models import LogEntry


class Command(BaseCommand):
    help = 'Виправляє проблему з дублюванням ключів в django_admin_log'

    def handle(self, *args, **options):
        self.stdout.write('🔄 Виправлення django_admin_log...')
        
        # Отримуємо максимальний ID
        max_id = LogEntry.objects.aggregate(max_id=models.Max('id'))['max_id'] or 0
        
        self.stdout.write(f'📊 Поточний максимальний ID: {max_id}')
        
        # Скидаємо послідовність
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT setval('django_admin_log_id_seq', {max_id});")
            
        self.stdout.write(self.style.SUCCESS(f'✅ Послідовність скинуто до {max_id}'))
        
        # Перевіряємо наступний ID
        with connection.cursor() as cursor:
            cursor.execute("SELECT nextval('django_admin_log_id_seq');")
            next_id = cursor.fetchone()[0]
            
        self.stdout.write(self.style.SUCCESS(f'✅ Наступний ID буде: {next_id}'))
        