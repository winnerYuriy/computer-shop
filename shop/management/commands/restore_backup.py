# shop/management/commands/restore_backup.py

import os
import subprocess
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Відновлення бази даних з бекапу'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=False,  # Змінили на False
            help='Назва файлу бекапу (наприклад: backup_20260425_191527.sql)'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='Показати список доступних бекапів'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Пропустити підтвердження'
        )

    def handle(self, *args, **options):
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        
        # Показати список бекапів
        if options['list']:
            self.show_backup_list(backup_dir)
            return
        
        filename = options.get('file')
        if not filename:
            self.stderr.write(self.style.ERROR('❌ Вкажіть --file для відновлення або --list для перегляду списку'))
            self.show_backup_list(backup_dir)
            return
        
        backup_file = os.path.join(backup_dir, filename)
        
        # Перевірка існування файлу
        if not os.path.exists(backup_file):
            self.stderr.write(self.style.ERROR(f'❌ Файл бекапу не знайдено: {filename}'))
            self.show_backup_list(backup_dir)
            return
        
        # Підтвердження
        if not options['force']:
            self.stdout.write(self.style.WARNING(f'\n⚠️  Увага! Відновлення з файлу: {filename}'))
            self.stdout.write(self.style.WARNING('Ця дія видалить ВСІ поточні дані та замінить їх даними з бекапу!'))
            self.stdout.write(self.style.WARNING('Цю дію НЕ МОЖНА скасувати!\n'))
            
            confirm = input('Введіть "ТАК" для підтвердження: ')
            if confirm != 'ТАК':
                self.stdout.write(self.style.ERROR('❌ Відновлення скасовано'))
                return
        
        # Відновлення залежно від типу файлу
        try:
            if filename.endswith('.json'):
                self.restore_from_json(backup_file)
            elif filename.endswith('.sql') or filename.endswith('.sql.gz'):
                self.restore_from_sql(backup_file)
            elif filename.endswith('.tar.gz'):
                self.restore_from_media(backup_file)
            else:
                self.stderr.write(self.style.ERROR('❌ Непідтримуваний формат файлу'))
                return
            
            self.stdout.write(self.style.SUCCESS(f'\n✅ База даних успішно відновлена з {filename}'))
            
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'❌ Помилка відновлення: {str(e)}'))

    def show_backup_list(self, backup_dir):
        """Показати список доступних бекапів"""
        if not os.path.exists(backup_dir):
            self.stdout.write(self.style.WARNING('Папка з бекапами не знайдена'))
            return
        
        backups = []
        for filename in os.listdir(backup_dir):
            filepath = os.path.join(backup_dir, filename)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                size_mb = stat.st_size / (1024 * 1024)
                backups.append({
                    'name': filename,
                    'size': size_mb,
                    'created': datetime.fromtimestamp(stat.st_mtime),
                })
        
        if not backups:
            self.stdout.write(self.style.WARNING('Немає доступних бекапів'))
            return
        
        backups.sort(key=lambda x: x['created'], reverse=True)
        
        self.stdout.write(self.style.SUCCESS('\n📋 Доступні бекапи:\n'))
        self.stdout.write(f"{'Назва файлу':<55} {'Розмір':<12} {'Дата створення':<20}")
        self.stdout.write('-' * 87)
        
        for b in backups:
            size_str = f"{b['size']:.1f} Мб" if b['size'] < 1000 else f"{b['size']/1024:.1f} Гб"
            date_str = b['created'].strftime('%d.%m.%Y %H:%M:%S')
            self.stdout.write(f"{b['name']:<55} {size_str:<12} {date_str:<20}")

    def restore_from_json(self, backup_file):
        """Відновлення з JSON файлу"""
        self.stdout.write('🔄 Очищення бази даних...')
        call_command('flush', interactive=False, verbosity=0)
        
        self.stdout.write('📥 Відновлення даних з JSON...')
        call_command('loaddata', backup_file, verbosity=0)
        
        self.stdout.write(self.style.SUCCESS('✅ Дані відновлено'))

    def restore_from_sql(self, backup_file):
        """Відновлення з SQL файлу (PostgreSQL)"""
        import gzip
        import tempfile
        
        db_settings = settings.DATABASES['default']
        
        self.stdout.write('🔄 Відновлення бази даних з SQL дампу...')
        
        # Якщо файл стиснутий, розпаковуємо
        if backup_file.endswith('.gz'):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as tmp:
                with gzip.open(backup_file, 'rt') as f_in:
                    tmp.write(f_in.read())
                sql_file = tmp.name
        else:
            sql_file = backup_file
        
        cmd = [
            'psql',
            '-h', db_settings['HOST'],
            '-p', str(db_settings['PORT']),
            '-U', db_settings['USER'],
            '-d', db_settings['NAME'],
            '-f', sql_file,
        ]
        
        env = os.environ.copy()
        env['PGPASSWORD'] = db_settings['PASSWORD']
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        # Видаляємо тимчасовий файл
        if backup_file.endswith('.gz'):
            os.unlink(sql_file)
        
        if result.returncode != 0:
            raise Exception(f"Помилка SQL: {result.stderr}")

    def restore_from_media(self, backup_file):
        """Відновлення медіа файлів з tar.gz архіву"""
        import tarfile
        media_dir = settings.MEDIA_ROOT
        
        self.stdout.write('🔄 Відновлення медіа файлів...')
        
        # Створюємо папку якщо не існує
        os.makedirs(media_dir, exist_ok=True)
        
        with tarfile.open(backup_file, 'r:gz') as tar:
            tar.extractall(path=media_dir)
        
        self.stdout.write(self.style.SUCCESS('✅ Медіа файли відновлено'))