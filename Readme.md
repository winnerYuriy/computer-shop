# 🛒 TechShop - Інтернет-магазин комп'ютерної техніки

[![Django](https://img.shields.io/badge/Django-6.0-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.14-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Сучасний інтернет-магазин комп'ютерної та офісної техніки, розроблений на Django з використанням PostgreSQL, Bootstrap 5 та інтеграцією з LiqPay та Новою Поштою.

![TechShop Demo](https://via.placeholder.com/800x400?text=TechShop+Screenshot)

## ✨ Функціонал

### 🛍️ Для покупців
- **Каталог товарів** з вкладеними категоріями (необмежена глибина)
- **Фільтрація** за ціною, брендом, характеристиками (RAM, тощо)
- **Пошук** товарів за назвою та описом
- **Сортування** за новизною, ціною, рейтингом
- **Кошик** на основі сесій
- **Оформлення замовлення** з валідацією
- **Інтеграція з LiqPay** (оплата банківськими картками)
- **Інтеграція з Новою Поштою** (автоматичний розрахунок доставки)
- **Відгуки та рейтинги** (5-зіркова система)
- **Галерея зображень** товарів (основне + додаткові фото)

### 👨‍💼 Для адміністратора
- **Кастомна адмінпанель** з сучасним дизайном
- **Управління товарами** (CRUD, характеристики в JSON)
- **Управління категоріями** (деревовидна структура)
- **Модерація відгуків** (публікація/відхилення)
- **Управління замовленнями** (зміна статусів)
- **Статистика** на головній сторінці
- **Масові дії** (опублікувати/відхилити відгуки)

## 🛠 Технології

### Backend
- **Django 6.0** - основний фреймворк
- **PostgreSQL 18** - база даних
- **Python 3.14** - мова програмування

### Frontend
- **Bootstrap 5** - CSS фреймворк
- **Font Awesome 6** - іконки
- **Select2** - красиві випадаючі списки
- **jQuery** - AJAX запити

### API та інтеграції
- **LiqPay API** - прийом платежів
- **Нова Пошта API** - розрахунок доставки, пошук відділень

## 📦 Встановлення

### Передумови
- Python 3.14+
- PostgreSQL 18+
- Git

### Крок 1: Клонування репозиторію

git clone https://github.com/winnerYuriy/computer-shop.git
cd computer-shop

### Крок 2: Створення віртуального середовища
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

### Крок 3: Встановлення залежностей
pip install -r requirements.txt

### Крок 4: Налаштування змінних середовища
cp .env.example .env
# Відредагуйте .env файл, додавши свої ключі
Приклад .env файлу:
SECRET_KEY=your-secret-key-here
DEBUG=True

# База даних
DB_NAME=computer_shop
DB_USER=shop_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# LiqPay
LIQPAY_PUBLIC_KEY=sandbox_i1234567890
LIQPAY_PRIVATE_KEY=sandbox_1234567890
LIQPAY_SANDBOX=True

# Нова Пошта
NOVA_POSHTA_API_KEY=your_api_key

# Кошик
CART_SESSION_ID=cart

### Крок 5: Налаштування бази даних

# Створіть базу даних в PostgreSQL
sudo -u postgres psql
CREATE DATABASE computer_shop;
CREATE USER shop_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE computer_shop TO shop_user;
\q

# Виконайте міграції
python manage.py makemigrations
python manage.py migrate
Крок 6: Завантаження тестових даних
bash
python manage.py seed_data
Крок 7: Створення суперкористувача
bash
python manage.py createsuperuser
Крок 8: Запуск сервера
bash
python manage.py runserver
Відкрийте в браузері: http://127.0.0.1:8000

### 🗂 Структура проекту

computer-shop/
├── config/                 # Налаштування Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── shop/                   # Головний додаток
│   ├── models.py           # Моделі (Product, Category, Review)
│   ├── views.py            # Контролери (фільтри, пошук)
│   ├── admin.py            # Адмінпанель
│   └── urls.py
├── cart/                   # Додаток кошика
│   ├── cart.py             # Логіка кошика
│   ├── views.py
│   └── urls.py
├── payment/                # Додаток оплати
│   ├── views.py            # LiqPay інтеграція
│   └── urls.py
├── services/               # Сервіси
│   └── nova_poshta.py      # API Нової Пошти
├── templates/              # Шаблони
│   ├── base.html
│   ├── shop/
│   ├── cart/
│   └── payment/
├── static/                 # Статичні файли
│   └── css/
├── media/                  # Завантажені файли
├── requirements.txt
└── README.md

### 🔧 API Ендпоінти
Метод	URL	Опис
GET	/cart/api/search-cities/	Пошук міст Нової Пошти
GET	/cart/api/search-warehouses/	Пошук відділень
GET	/cart/api/calculate-delivery/	Розрахунок вартості доставки
POST	/cart/add/<int:product_id>/	Додавання в кошик
POST	/cart/remove/<int:product_id>/	Видалення з кошика
POST	/cart/update/<int:product_id>/	Оновлення кількості
GET	/cart/checkout/	Оформлення замовлення
GET	/payment/process/<int:order_id>/	Оплата LiqPay

### 🧪 Тестування
Тестова картка LiqPay
Номер: 4111 1111 1111 1111
Термін: будь-який в майбутньому
CVV: 111

### Тестові дані

python manage.py seed_data
Створює:

13 категорій (з вкладеністю)

10 атрибутів (бренд, RAM, тощо)

7 товарів з характеристиками

Суперкористувача (admin/admin123)

### 📸 Скріншоти
Головна сторінка
https://via.placeholder.com/600x300?text=Home+Page

Каталог з фільтрами
https://via.placeholder.com/600x300?text=Catalog+with+Filters

Кошик
https://via.placeholder.com/600x300?text=Shopping+Cart

Адмінпанель
https://via.placeholder.com/600x300?text=Admin+Panel

### 🚀 Деплой
Налаштування для продакшну
Змініть DEBUG = False в .env

Додайте свій домен в ALLOWED_HOSTS

Налаштуйте реальні ключі LiqPay

Зберіть статичні файли:

python manage.py collectstatic
Приклад для PythonAnywhere
bash
# Налаштування WSGI
# Налаштування статичних файлів
# Налаштування медіа файлів

### 🤝 Внесок
Форкніть репозиторій

Створіть гілку для фічі (git checkout -b feature/amazing-feature)

Закомітьте зміни (git commit -m 'Add amazing feature')

Пушніть гілку (git push origin feature/amazing-feature)

Відкрийте Pull Request

### 📝 Ліцензія
GNU GENERAL PUBLIC LICENSE. Дивіться файл LICENSE для деталей.

### 📧 Контакти
Розробник: winnerYuriy

GitHub: github.com/winnerYuriy

Проект: github.com/winnerYuriy/computer-shop

### 🙏 Подяки
Django Community

LiqPay for payment gateway

Nova Poshta for delivery API

Bootstrap team

⭐ Якщо вам сподобався проект, поставте зірку на GitHub!

