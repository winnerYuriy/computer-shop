#!/bin/bash

# ============================================================
# Скрипт для відновлення бази даних з бекапу
# ============================================================

# Отримуємо директорію, де знаходиться скрипт
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Налаштування кольорів
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Налаштування бази даних
DB_NAME="computer_shop"
DB_USER="shop_user"
DB_PASSWORD="shop_password123"
DB_HOST="localhost"
DB_PORT="5432"

# Папка з бекапами (за замовчуванням - backups в папці проекту)
DEFAULT_BACKUP_DIR="$SCRIPT_DIR/backups"

# ============================================================
# Функції
# ============================================================

print_color() {
    echo -e "${2}${1}${NC}"
}

show_help() {
    print_color "============================================================" "$BLUE"
    print_color "    Скрипт для відновлення бази даних з бекапу" "$BLUE"
    print_color "============================================================" "$BLUE"
    echo ""
    print_color "Використання:" "$YELLOW"
    echo "  ./restore_backup.sh [ОПЦІЇ]"
    echo ""
    print_color "Опції:" "$YELLOW"
    echo "  -f, --file FILE        Назва файлу бекапу (в папці backups)"
    echo "  -p, --path PATH        Повний шлях до файлу бекапу"
    echo "  -d, --dir DIR          Папка з бекапами (за замовчуванням: $DEFAULT_BACKUP_DIR)"
    echo "  -l, --list             Показати список доступних бекапів"
    echo "  -L, --latest           Відновити останній бекап"
    echo "  -h, --help             Показати цю допомогу"
    echo ""
    print_color "Приклади:" "$YELLOW"
    echo "  ./restore_backup.sh --list"
    echo "  ./restore_backup.sh --file computer_shop_20260425_191527.sql.gz"
    echo "  ./restore_backup.sh --path /home/user/backups/my_backup.sql"
    echo "  ./restore_backup.sh --latest"
    echo "  ./restore_backup.sh --dir /custom/backup/path --latest"
    echo ""
}

show_backup_list() {
    local backup_dir="${1:-$DEFAULT_BACKUP_DIR}"
    
    print_color "\n📋 Список доступних бекапів в $backup_dir:\n" "$BLUE"
    
    if [ ! -d "$backup_dir" ]; then
        print_color "❌ Папка з бекапами не знайдена: $backup_dir" "$RED"
        exit 1
    fi
    
    # Знаходимо всі файли бекапів
    backups=$(find "$backup_dir" -maxdepth 1 \( -name "*.sql" -o -name "*.sql.gz" -o -name "*.tar.gz" -o -name "*.json" \) -type f | sort -r)
    
    if [ -z "$backups" ]; then
        print_color "❌ Немає доступних бекапів" "$RED"
        exit 1
    fi
    
    printf "%-55s %-15s %-20s\n" "НАЗВА ФАЙЛУ" "РОЗМІР" "ДАТА"
    printf "%.0s-" {1..90}
    echo ""
    
    for backup in $backups; do
        filename=$(basename "$backup")
        size=$(du -h "$backup" | cut -f1)
        date=$(stat -c "%y" "$backup" | cut -d' ' -f1,2 | cut -d'.' -f1)
        printf "%-55s %-15s %-20s\n" "$filename" "$size" "$date"
    done
}

get_latest_backup() {
    local backup_dir="${1:-$DEFAULT_BACKUP_DIR}"
    
    # Знаходимо найсвіжіший файл бекапу
    latest=$(find "$backup_dir" -maxdepth 1 \( -name "*.sql" -o -name "*.sql.gz" -o -name "*.tar.gz" -o -name "*.json" \) -type f -printf "%T@ %p\n" 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
    
    if [ -z "$latest" ]; then
        print_color "❌ Немає доступних бекапів" "$RED"
        exit 1
    fi
    
    echo "$latest"
}

restore_backup() {
    local backup_file="$1"
    
    # Перевірка існування файлу
    if [ ! -f "$backup_file" ]; then
        print_color "❌ Файл бекапу не знайдено: $backup_file" "$RED"
        exit 1
    fi
    
    filename=$(basename "$backup_file")
    size=$(du -h "$backup_file" | cut -f1)
    
    print_color "\n⚠️  УВАГА!" "$YELLOW"
    print_color "============================================================" "$YELLOW"
    print_color "Відновлення бази даних з файлу: $filename" "$YELLOW"
    print_color "Розмір файлу: $size" "$YELLOW"
    print_color "============================================================" "$YELLOW"
    print_color "\nЦя дія ВИДАЛИТЬ всі поточні дані в базі даних $DB_NAME" "$RED"
    print_color "та ЗАМІНИТЬ їх даними з бекапу!" "$RED"
    print_color "Цю дію НЕ МОЖНА скасувати!\n" "$RED"
    
    read -p "Введіть 'ТАК' для підтвердження: " confirm
    if [ "$confirm" != "ТАК" ]; then
        print_color "❌ Відновлення скасовано" "$RED"
        exit 0
    fi
    
    # Попереднє очищення бази даних
    print_color "\n🗑️  Очищення поточної бази даних..." "$BLUE"
    export PGPASSWORD=$DB_PASSWORD
    psql -U $DB_USER -h $DB_HOST -p $DB_PORT -d $DB_NAME -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" 2>/dev/null
    unset PGPASSWORD
    
    print_color "\n🔄 Починаємо відновлення бази даних..." "$BLUE"
    
    # Розпаковуємо якщо файл стиснутий
    if [[ "$backup_file" == *.gz ]]; then
        print_color "📦 Розпаковуємо архів..." "$BLUE"
        gunzip -c "$backup_file" > /tmp/restore_temp.sql
        restore_file="/tmp/restore_temp.sql"
    else
        restore_file="$backup_file"
    fi
    
    # Відновлення бази даних
    export PGPASSWORD=$DB_PASSWORD
    
    print_color "📥 Відновлення даних..." "$BLUE"
    psql -U $DB_USER -h $DB_HOST -p $DB_PORT -d $DB_NAME < "$restore_file" 2>&1 | grep -v "ERROR:  relation.*already exists\|ERROR:  constraint.*already exists\|ERROR:  multiple primary keys\|NOTICE:"
    
    PSQL_EXIT_CODE=$?
    
    unset PGPASSWORD
    
    # Видаляємо тимчасовий файл
    if [[ "$backup_file" == *.gz ]]; then
        rm -f /tmp/restore_temp.sql
    fi
    
    if [ $PSQL_EXIT_CODE -eq 0 ]; then
        print_color "\n✅ База даних успішно відновлена з файлу: $filename" "$GREEN"
        
        # Виправлення послідовностей ID
        print_color "\n🔄 Виправлення послідовностей ID..." "$BLUE"
        
        cd "$SCRIPT_DIR"
        
        # Створюємо тимчасовий Python скрипт (виправлено: додано import os)
        cat > /tmp/fix_sequences.py << 'EOF'
import os
import sys
import django
from django.db import connection

# Налаштовуємо Django
sys.path.append('/home/yuri/projects/computer-shop')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Список таблиць для виправлення
tables = [
    'django_admin_log',
    'django_content_type', 
    'django_migrations',
    'django_session',
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
                cursor.execute(f"SELECT setval('{table}_id_seq', {max_id});")
                print(f"  ✅ {table}_id_seq → {max_id}")
                fixed += 1
            else:
                cursor.execute(f"SELECT setval('{table}_id_seq', 1);")
                print(f"  ⚠️ {table} порожня, скинуто до 1")
                fixed += 1
        except Exception as e:
            print(f"  ❌ Помилка для {table}: {e}")

print(f"\n✅ Виправлено {fixed} послідовностей")
EOF
        
        # Виконуємо скрипт
        if [ -f "venv/bin/python" ]; then
            ./venv/bin/python /tmp/fix_sequences.py
        else
            python3 /tmp/fix_sequences.py
        fi
        
        rm -f /tmp/fix_sequences.py
        
    else
        print_color "\n❌ Помилка при відновленні бази даних!" "$RED"
        exit 1
    fi
    
    print_color "\n✅ Відновлення завершено успішно!" "$GREEN"
}

# ============================================================
# Головна логіка
# ============================================================

BACKUP_DIR="$DEFAULT_BACKUP_DIR"
BACKUP_FILE=""

# Парсинг аргументів
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--file)
            BACKUP_FILE="$BACKUP_DIR/$2"
            shift 2
            ;;
        -p|--path)
            BACKUP_FILE="$2"
            shift 2
            ;;
        -d|--dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        -l|--list)
            show_backup_list "$BACKUP_DIR"
            exit 0
            ;;
        -L|--latest)
            LATEST_BACKUP=$(get_latest_backup "$BACKUP_DIR")
            restore_backup "$LATEST_BACKUP"
            exit 0
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_color "❌ Невідома опція: $1" "$RED"
            show_help
            exit 1
            ;;
    esac
done

# Якщо вказано файл - відновлюємо
if [ -n "$BACKUP_FILE" ]; then
    restore_backup "$BACKUP_FILE"
else
    # Якщо немає аргументів - показуємо допомогу
    show_help
fi