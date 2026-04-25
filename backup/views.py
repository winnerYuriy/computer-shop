# backup/views.py

import os
import subprocess
import json
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse, FileResponse, JsonResponse
from django.core.management import call_command


@staff_member_required
def backup_list(request):
    """Головна сторінка модуля бекапу (список бекапів)"""
    backups = get_backup_list()
    total_size = sum(b['size'] for b in backups)  # Додано: загальний розмір
    context = {
        'backups': backups,
        'total_size': total_size,  # Додано: передаємо в шаблон
        'title': 'Резервне копіювання',
    }
    return render(request, 'admin/backup_list.html', context)


@staff_member_required
def create_backup(request):
    """Створення резервної копії бази даних"""
    if request.method == 'POST':
        backup_type = request.POST.get('backup_type', 'full')
        
        # Формуємо ім'я файлу
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"backup_{timestamp}"
        
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        try:
            if backup_type == 'full':
                # Повний бекап через dumpdata
                backup_file = os.path.join(backup_dir, f"{backup_name}.json")
                with open(backup_file, 'w', encoding='utf-8') as f:
                    call_command('dumpdata', indent=2, stdout=f)
                messages.success(request, f'✅ JSON бекап створено: {backup_name}.json')
                
                # SQL дамп через pg_dump
                sql_file = os.path.join(backup_dir, f"{backup_name}.sql")
                db_settings = settings.DATABASES['default']
                
                cmd = [
                    'pg_dump',
                    '-h', db_settings['HOST'],
                    '-p', str(db_settings['PORT']),
                    '-U', db_settings['USER'],
                    '-d', db_settings['NAME'],
                    '-f', sql_file,
                ]
                
                env = os.environ.copy()
                env['PGPASSWORD'] = db_settings['PASSWORD']
                
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                
                if result.returncode == 0:
                    messages.success(request, f'✅ SQL дамп створено: {backup_name}.sql')
                else:
                    messages.warning(request, f'⚠️ SQL дамп створено з помилками: {result.stderr}')
                    
            elif backup_type == 'db':
                # Тільки SQL дамп
                sql_file = os.path.join(backup_dir, f"{backup_name}.sql")
                db_settings = settings.DATABASES['default']
                
                cmd = [
                    'pg_dump',
                    '-h', db_settings['HOST'],
                    '-p', str(db_settings['PORT']),
                    '-U', db_settings['USER'],
                    '-d', db_settings['NAME'],
                    '-f', sql_file,
                ]
                
                env = os.environ.copy()
                env['PGPASSWORD'] = db_settings['PASSWORD']
                
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                
                if result.returncode == 0:
                    messages.success(request, f'✅ SQL дамп створено: {backup_name}.sql')
                else:
                    messages.error(request, f'❌ Помилка створення SQL дампу: {result.stderr}')
                    
            elif backup_type == 'media':
                # Бекап медіа файлів
                media_dir = settings.MEDIA_ROOT
                backup_file = os.path.join(backup_dir, f"{backup_name}_media.tar.gz")
                
                # Перевіряємо, чи існує медіа директорія
                if not os.path.exists(media_dir):
                    messages.error(request, f'❌ Папка медіа не знайдена: {media_dir}')
                    return redirect('backup:list')
                
                cmd = ['tar', '-czf', backup_file, '-C', media_dir, '.']
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    messages.success(request, f'✅ Бекап медіа файлів створено: {backup_name}_media.tar.gz')
                else:
                    messages.error(request, f'❌ Помилка створення бекапу медіа: {result.stderr}')
            
            else:
                messages.error(request, 'Невідомий тип бекапу')
                
        except Exception as e:
            messages.error(request, f'❌ Помилка створення бекапу: {str(e)}')
        
        return redirect('backup:list')
    
    return redirect('backup:list')


@staff_member_required
def restore_backup(request, filename):
    """Відновлення бази даних з бекапу"""
    if request.method == 'POST':
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        backup_file = os.path.join(backup_dir, filename)
        
        if not os.path.exists(backup_file):
            messages.error(request, f'❌ Файл бекапу не знайдено: {filename}')
            return redirect('backup:list')
        
        try:
            if filename.endswith('.json'):
                # Відновлення з JSON
                messages.warning(request, '⚠️ Очищення бази даних перед відновленням...')
                call_command('flush', interactive=False)
                messages.info(request, '📥 Відновлення даних з JSON...')
                call_command('loaddata', backup_file)
                messages.success(request, f'✅ База даних відновлена з {filename}')
                
            elif filename.endswith('.sql'):
                # Відновлення з SQL
                db_settings = settings.DATABASES['default']
                
                cmd = [
                    'psql',
                    '-h', db_settings['HOST'],
                    '-p', str(db_settings['PORT']),
                    '-U', db_settings['USER'],
                    '-d', db_settings['NAME'],
                    '-f', backup_file,
                ]
                
                env = os.environ.copy()
                env['PGPASSWORD'] = db_settings['PASSWORD']
                
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                
                if result.returncode == 0:
                    messages.success(request, f'✅ База даних відновлена з {filename}')
                else:
                    messages.error(request, f'❌ Помилка відновлення: {result.stderr}')
                    
            elif filename.endswith('.tar.gz'):
                # Відновлення медіа файлів
                media_dir = settings.MEDIA_ROOT
                
                # Переконуємось, що папка існує
                os.makedirs(media_dir, exist_ok=True)
                
                cmd = ['tar', '-xzf', backup_file, '-C', media_dir]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    messages.success(request, f'✅ Медіа файли відновлено з {filename}')
                else:
                    messages.error(request, f'❌ Помилка відновлення медіа: {result.stderr}')
                    
            else:
                messages.error(request, 'Непідтримуваний формат файлу')
                
        except Exception as e:
            messages.error(request, f'❌ Помилка відновлення: {str(e)}')
        
        return redirect('backup:list')
    
    return redirect('backup:list')


@staff_member_required
def download_backup(request, filename):
    """Завантаження файлу бекапу"""
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    backup_file = os.path.join(backup_dir, filename)
    
    if os.path.exists(backup_file):
        response = FileResponse(open(backup_file, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    else:
        messages.error(request, f'❌ Файл не знайдено: {filename}')
        return redirect('backup:list')


@staff_member_required
def delete_backup(request, filename):
    """Видалення файлу бекапу"""
    if request.method == 'POST':
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        backup_file = os.path.join(backup_dir, filename)
        
        if os.path.exists(backup_file):
            os.remove(backup_file)
            messages.success(request, f'✅ Файл {filename} видалено')
        else:
            messages.error(request, f'❌ Файл не знайдено: {filename}')
    
    return redirect('backup:list')


def get_backup_list():
    """Отримання списку доступних бекапів"""
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    backups = []
    
    if os.path.exists(backup_dir):
        for filename in os.listdir(backup_dir):
            filepath = os.path.join(backup_dir, filename)
            if os.path.isfile(filepath):
                try:
                    stat = os.stat(filepath)
                    
                    # Визначаємо тип бекапу
                    if filename.endswith('.json'):
                        backup_type = 'json'
                    elif filename.endswith('.sql'):
                        backup_type = 'sql'
                    elif filename.endswith('.tar.gz'):
                        backup_type = 'gz'
                    else:
                        backup_type = 'other'
                    
                    backups.append({
                        'name': filename,
                        'path': filepath,
                        'size': stat.st_size,
                        'created': datetime.fromtimestamp(stat.st_mtime),
                        'type': backup_type,
                    })
                except Exception as e:
                    print(f"Помилка читання файлу {filename}: {e}")
    
    # Сортуємо за датою (новіші перші)
    backups.sort(key=lambda x: x['created'], reverse=True)
    return backups


@staff_member_required
def backup_info(request):
    """API для отримання інформації про бекапи (AJAX)"""
    backups = get_backup_list()
    total_size = sum(b['size'] for b in backups)
    data = {
        'backups': backups,
        'count': len(backups),
        'total_size': total_size,
        'total_size_formatted': f"{total_size / (1024*1024):.1f} Мб" if total_size > 0 else "0 байтів",
    }
    return JsonResponse(data)