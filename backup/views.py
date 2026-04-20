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
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile


@staff_member_required
def backup_dashboard(request):
    """Головна сторінка модуля бекапу"""
    backups = get_backup_list()
    context = {
        'backups': backups,
        'title': 'Резервне копіювання',
    }
    return render(request, 'backup/dashboard.html', context)


@staff_member_required
def create_backup(request):
    """Створення резервної копії бази даних"""
    if request.method == 'POST':
        backup_type = request.POST.get('backup_type', 'full')
        backup_name = request.POST.get('backup_name', '')
        
        # Формуємо ім'я файлу
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if not backup_name:
            backup_name = f"backup_{timestamp}"
        
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        try:
            if backup_type == 'full':
                # Повний бекап через dumpdata
                backup_file = os.path.join(backup_dir, f"{backup_name}.json")
                with open(backup_file, 'w', encoding='utf-8') as f:
                    call_command('dumpdata', indent=2, stdout=f)
                
                # Додатково створюємо SQL дамп через pg_dump
                sql_file = os.path.join(backup_dir, f"{backup_name}.sql")
                db_settings = settings.DATABASES['default']
                
                cmd = [
                    'pg_dump',
                    '-h', db_settings['HOST'],
                    '-p', db_settings['PORT'],
                    '-U', db_settings['USER'],
                    '-d', db_settings['NAME'],
                    '-f', sql_file,
                ]
                
                env = os.environ.copy()
                env['PGPASSWORD'] = db_settings['PASSWORD']
                
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                
                if result.returncode != 0:
                    messages.warning(request, f'SQL дамп створено з помилками: {result.stderr}')
                else:
                    messages.success(request, f'✅ Повний бекап створено: {backup_name}.json та {backup_name}.sql')
                    
            elif backup_type == 'db':
                # Тільки SQL дамп
                sql_file = os.path.join(backup_dir, f"{backup_name}.sql")
                db_settings = settings.DATABASES['default']
                
                cmd = [
                    'pg_dump',
                    '-h', db_settings['HOST'],
                    '-p', db_settings['PORT'],
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
        
        return redirect('backup:dashboard')
    
    return redirect('backup:dashboard')


@staff_member_required
def restore_backup(request, backup_name):
    """Відновлення бази даних з бекапу"""
    if request.method == 'POST':
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        backup_file = os.path.join(backup_dir, backup_name)
        
        if not os.path.exists(backup_file):
            messages.error(request, f'❌ Файл бекапу не знайдено: {backup_name}')
            return redirect('backup:dashboard')
        
        try:
            if backup_name.endswith('.json'):
                # Відновлення з JSON
                confirm = request.POST.get('confirm', False)
                if not confirm:
                    return render(request, 'backup/confirm_restore.html', {
                        'backup_name': backup_name,
                        'title': 'Підтвердження відновлення'
                    })
                
                # Очищаємо БД перед відновленням
                call_command('flush', interactive=False)
                
                # Відновлюємо дані
                call_command('loaddata', backup_file)
                messages.success(request, f'✅ База даних відновлена з {backup_name}')
                
            elif backup_name.endswith('.sql'):
                # Відновлення з SQL
                db_settings = settings.DATABASES['default']
                
                cmd = [
                    'psql',
                    '-h', db_settings['HOST'],
                    '-p', db_settings['PORT'],
                    '-U', db_settings['USER'],
                    '-d', db_settings['NAME'],
                    '-f', backup_file,
                ]
                
                env = os.environ.copy()
                env['PGPASSWORD'] = db_settings['PASSWORD']
                
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                
                if result.returncode == 0:
                    messages.success(request, f'✅ База даних відновлена з {backup_name}')
                else:
                    messages.error(request, f'❌ Помилка відновлення: {result.stderr}')
                    
            else:
                messages.error(request, 'Непідтримуваний формат файлу')
                
        except Exception as e:
            messages.error(request, f'❌ Помилка відновлення: {str(e)}')
        
        return redirect('backup:dashboard')
    
    return redirect('backup:dashboard')


@staff_member_required
def download_backup(request, backup_name):
    """Завантаження файлу бекапу"""
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    backup_file = os.path.join(backup_dir, backup_name)
    
    if os.path.exists(backup_file):
        response = FileResponse(open(backup_file, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="{backup_name}"'
        return response
    else:
        messages.error(request, f'❌ Файл не знайдено: {backup_name}')
        return redirect('backup:dashboard')


@staff_member_required
def delete_backup(request, backup_name):
    """Видалення файлу бекапу"""
    if request.method == 'POST':
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        backup_file = os.path.join(backup_dir, backup_name)
        
        if os.path.exists(backup_file):
            os.remove(backup_file)
            messages.success(request, f'✅ Файл {backup_name} видалено')
        else:
            messages.error(request, f'❌ Файл не знайдено: {backup_name}')
    
    return redirect('backup:dashboard')


def get_backup_list():
    """Отримання списку доступних бекапів"""
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    backups = []
    
    if os.path.exists(backup_dir):
        for filename in os.listdir(backup_dir):
            filepath = os.path.join(backup_dir, filename)
            stat = os.stat(filepath)
            backups.append({
                'name': filename,
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_mtime),
                'type': filename.split('.')[-1],
            })
    
    # Сортуємо за датою (новіші перші)
    backups.sort(key=lambda x: x['created'], reverse=True)
    return backups


@staff_member_required
def backup_info(request):
    """API для отримання інформації про бекапи (AJAX)"""
    backups = get_backup_list()
    data = {
        'backups': backups,
        'count': len(backups),
        'total_size': sum(b['size'] for b in backups),
    }
    return JsonResponse(data)