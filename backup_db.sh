#!/bin/bash

# Налаштування
DB_NAME="computer_shop"
DB_USER="shop_user"
DB_PASSWORD="shop_password123"
BACKUP_DIR="/home/yuri/PROJECTS/computer-shop/backups"
DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/computer_shop_$DATE.sql"

# Створюємо папку для бекапів, якщо її немає
mkdir -p $BACKUP_DIR

# Експортуємо БД (використовуємо PGPASSWORD для уникнення введення пароля)
export PGPASSWORD=$DB_PASSWORD
pg_dump -U $DB_USER -h localhost $DB_NAME > $BACKUP_FILE
unset PGPASSWORD

# Видаляємо бекапи старіші за 30 днів
find $BACKUP_DIR -name "computer_shop_*.sql" -type f -mtime +30 -delete

# Опціонально: стискаємо бекап
gzip $BACKUP_FILE

echo "Бекап створено: $BACKUP_FILE.gz"