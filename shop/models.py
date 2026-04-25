# shop/models.py

import os
from datetime import date, datetime
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone
from config import settings
from mptt.models import MPTTModel, TreeForeignKey


# -------------------------------------------------------------------
# Утиліти
# -------------------------------------------------------------------
def get_image_upload_path(instance, filename):
    """Формує шлях для збереження зображень товарів."""
    return os.path.join('products', str(instance.id), filename)


# -------------------------------------------------------------------
# Бренди
# -------------------------------------------------------------------
class Brand(models.Model):
    name = models.CharField('Бренд', max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    logo = models.ImageField('Логотип', upload_to='brands/', blank=True, null=True)

    class Meta:
        verbose_name = 'Бренд'
        verbose_name_plural = 'Бренди'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# -------------------------------------------------------------------
# Акції / Промоції
# -------------------------------------------------------------------
class Promotion(models.Model):
    TYPE_CHOICES = [
        ('new', 'Новинка'),
        ('bestseller', 'Хіт продажів'),
        ('sale', 'Розпродаж'),
        ('discount', 'Знижка'),
        ('seasonal', 'Сезонна'),
        ('black_friday', 'Чорна п\'ятниця'),
        ('recommended', 'Рекомендуємо'),
    ]

    name = models.CharField('Назва акції', max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    promotion_type = models.CharField('Тип акції', max_length=20, choices=TYPE_CHOICES)
    discount_percent = models.PositiveIntegerField('Відсоток знижки', default=0)
    is_active = models.BooleanField('Активна', default=True)
    start_date = models.DateTimeField('Дата початку')
    end_date = models.DateTimeField('Дата закінчення')
    description = models.TextField('Опис', blank=True)

    class Meta:
        verbose_name = 'Акція'
        verbose_name_plural = 'Акції'
        ordering = ['-start_date']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.get_promotion_type_display()})"

    @property
    def is_current(self):
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date


# -------------------------------------------------------------------
# Категорії (MPTT)
# -------------------------------------------------------------------
class Category(MPTTModel):
    name = models.CharField('Категорія', max_length=100, unique=True)
    slug = models.SlugField('URL', max_length=100, unique=True, blank=True)
    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Батьківська категорія'
    )
    image = models.ImageField('Зображення', upload_to='categories/', blank=True, null=True)
    description = models.TextField('Опис', blank=True)
    
    # ДОДАЙТЕ ЦЕ ПОЛЕ:
    external_id = models.CharField(
        'Зовнішній ID',
        max_length=100,
        blank=True,
        unique=True,
        null=True,
        help_text='ID з імпорту (наприклад, group_123, cat_456)'
    )

    class MPTTMeta:
        order_insertion_by = ['name']

    class Meta:
        verbose_name = 'Категорія'
        verbose_name_plural = 'Категорії'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('shop:category_detail', args=[self.slug])

# -------------------------------------------------------------------
# Властивості товарів (характеристики)
# -------------------------------------------------------------------
class Property(models.Model):
    """Характеристика (наприклад, «Оперативна пам'ять», «Колір»)."""
    name = models.CharField('Назва', max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    categories = models.ManyToManyField(Category, blank=True, related_name='properties', verbose_name='Категорії')

    class Meta:
        verbose_name = 'Властивість'
        verbose_name_plural = 'Властивості'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)   # виправлено: self.name
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name                     # виправлено: self.name


class PropertyValue(models.Model):
    """Значення властивості (наприклад, «16GB», «Червоний»)."""
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='values', verbose_name='Властивість')
    value = models.CharField('Значення', max_length=255)

    class Meta:
        verbose_name = 'Значення властивості'
        verbose_name_plural = 'Значення властивостей'
        unique_together = ['property', 'value']

    def __str__(self):
        return f"{self.property.name}: {self.value}"


# -------------------------------------------------------------------
# Зображення товарів
# -------------------------------------------------------------------
class ProductImage(models.Model):
    """Додаткові зображення товару."""
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='additional_images', verbose_name='Товар')
    image = models.ImageField('Зображення', upload_to=get_image_upload_path)
    alt_text = models.CharField('Альтернативний текст', max_length=200, blank=True)
    order = models.PositiveIntegerField('Порядок', default=0)
    created_at = models.DateTimeField('Дата додавання', auto_now_add=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'Додаткове зображення'
        verbose_name_plural = 'Додаткові зображення'

    def __str__(self):
        return f"Зображення #{self.order} для {self.product.title}"   # виправлено: .title


# -------------------------------------------------------------------
# Товари
# -------------------------------------------------------------------
class Product(models.Model):
    # Основна інформація
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', verbose_name='Категорія')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='products', verbose_name='Бренд')
    promotions = models.ManyToManyField(Promotion, blank=True, related_name='products', verbose_name='Акції')

    title = models.CharField('Назва', max_length=250)
    slug = models.SlugField('URL', max_length=250, unique=True, blank=True)
    article = models.CharField('Артикул', max_length=50, blank=True, null=True)
    code = models.CharField('Код товару', max_length=50, blank=True, null=True)

    description = models.TextField('Короткий опис', blank=True)
    full_description = models.TextField('Повний опис', blank=True)

    # Ціна та наявність
    price = models.DecimalField('Ціна', max_digits=12, decimal_places=2, default=0)
    old_price = models.DecimalField('Стара ціна', max_digits=12, decimal_places=2, blank=True, null=True)
    discount = models.PositiveIntegerField('Знижка, %', default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    quantity = models.PositiveIntegerField('Кількість на складі', default=1)
    available = models.BooleanField('Наявність', default=True)

    # Гарантія, виробництво
    warranty = models.PositiveIntegerField('Гарантія, місяців', default=0)
    country = models.CharField('Країна виробництва', max_length=50, blank=True, null=True)

    # Зображення
    main_image = models.ImageField('Головне зображення', upload_to=get_image_upload_path, blank=True, null=True)

    # Характеристики (динамічні)
    attributes = models.JSONField('Характеристики', blank=True, null=True, help_text='Додаткові характеристики у форматі JSON')
    # Зв'язок зі значеннями властивостей (альтернативний спосіб)
    property_values = models.ManyToManyField(PropertyValue, blank=True, related_name='products', verbose_name='Значення властивостей')

    # Службові поля
    created_at = models.DateTimeField('Дата створення', auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField('Дата оновлення', auto_now=True)

    # Рейтинг (для відгуків)
    rating = models.DecimalField('Рейтинг', max_digits=3, decimal_places=2, default=0)
    reviews_count = models.PositiveIntegerField('Кількість відгуків', default=0)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товари'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['category', 'available']),
            models.Index(fields=['price']),
            models.Index(fields=['brand']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            
            # Перевіряємо унікальність slug
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            self.slug = slug
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('shop:product_detail', args=[self.slug])

    @property
    def final_price(self):
        if self.old_price:
            return self.old_price
        if self.discount:
            return self.price - (self.price * self.discount / 100)
        return self.price

    @property
    def is_available(self):
        return self.available and self.quantity > 0

    def availability_text(self):
        if self.is_available:
            return "В наявності"
        return "Немає в наявності"

    def get_promotion_labels(self):
        labels = []
        for promo in self.promotions.filter(is_active=True):
            if promo.is_current:
                labels.append(promo.get_promotion_type_display())
        return labels

    def update_rating(self):
        from .models import Review
        reviews = self.reviews.filter(is_approved=True)
        if reviews.exists():
            avg = reviews.aggregate(models.Avg('rating'))['rating__avg']
            self.rating = round(avg, 2)
            self.reviews_count = reviews.count()
        else:
            self.rating = 0
            self.reviews_count = 0
        self.save(update_fields=['rating', 'reviews_count'])


# -------------------------------------------------------------------
# Відгуки
# -------------------------------------------------------------------
class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews', verbose_name='Товар')
    user_name = models.CharField('Ім\'я', max_length=100)
    email = models.EmailField('Email', blank=True)
    rating = models.PositiveSmallIntegerField('Оцінка', choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField('Коментар')
    is_approved = models.BooleanField('Опубліковано', default=False)
    created_at = models.DateTimeField('Створено', auto_now_add=True)

    class Meta:
        verbose_name = 'Відгук'
        verbose_name_plural = 'Відгуки'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user_name} - {self.product.title} ({self.rating}★)"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.product.update_rating()


# -------------------------------------------------------------------
# Замовлення
# -------------------------------------------------------------------
class Order(models.Model):
    STATUS_CHOICES = [
        ('new', 'Нове'),
        ('processing', 'Обробляється'),
        ('paid', 'Оплачено'),
        ('shipped', 'Відправлено'),
        ('delivered', 'Доставлено'),
        ('cancelled', 'Скасовано'),
    ]

    DELIVERY_CHOICES = [
        ('nova_post', 'Нова Пошта'),
        ('ukr_post', 'Укрпошта'),
        ('courier', 'Кур\'єр'),
        ('pickup', 'Самовивіз'),
    ]

    full_name = models.CharField('ПІБ', max_length=200)
    legal_entity = models.ForeignKey(
        'LegalEntity', 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True, 
        verbose_name='Юридична особа (покупець)'
    )
    invoice_required = models.BooleanField('Потрібен рахунок-фактура', default=False)
    phone = models.CharField('Телефон', max_length=20)
    email = models.EmailField('Email')
    address = models.TextField('Адреса доставки', blank=True)
    city = models.CharField('Місто', max_length=100, blank=True)
    nova_post_office = models.CharField('Відділення Нової Пошти', max_length=50, blank=True)
    delivery_method = models.CharField('Спосіб доставки', max_length=20, choices=DELIVERY_CHOICES, default='nova_post')
    comment = models.TextField('Коментар до замовлення', blank=True)

    products = models.JSONField('Товари', default=list, help_text='[{"id": 1, "name": "...", "price": 1000, "quantity": 2}]')
    total_amount = models.DecimalField('Сума замовлення', max_digits=10, decimal_places=2)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='new')

    payment_id = models.CharField('ID платежу', max_length=100, blank=True)
    is_paid = models.BooleanField('Оплачено', default=False)
    payment_method = models.CharField('Спосіб оплати', max_length=50, blank=True)

    created_at = models.DateTimeField('Створено', auto_now_add=True)
    updated_at = models.DateTimeField('Оновлено', auto_now=True)

    class Meta:
        verbose_name = 'Замовлення'
        verbose_name_plural = 'Замовлення'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['is_paid']),
        ]

    def __str__(self):
        return f'Замовлення #{self.id} - {self.full_name}'
    
    def save(self, *args, **kwargs):
        # Синхронізуємо is_paid зі статусом
        if self.status == 'paid' and not self.is_paid:
            self.is_paid = True
        elif self.status != 'paid' and self.is_paid:
            self.is_paid = False
        super().save(*args, **kwargs)


# -------------------------------------------------------------------
# Кошик
# -------------------------------------------------------------------
class Cart(models.Model):
    session_key = models.CharField('Ключ сесії', max_length=40, unique=True)
    items = models.JSONField('Товари в кошику', default=list)
    created_at = models.DateTimeField('Створено', auto_now_add=True)
    updated_at = models.DateTimeField('Оновлено', auto_now=True)

    class Meta:
        verbose_name = 'Кошик'
        verbose_name_plural = 'Кошики'

    def __str__(self):
        return f'Кошик {self.session_key[:10]}...'

    def get_total_items(self):
        return sum(item.get('quantity', 0) for item in self.items)

    def get_total_price(self):
        return sum(item.get('price', 0) * item.get('quantity', 0) for item in self.items)


# -------------------------------------------------------------------
# Логування відвідувань (опціонально)
# -------------------------------------------------------------------
class VisitLog(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    page = models.CharField(max_length=200)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    def __str__(self):
        return f'{self.user or "Анонім"} - {self.page} - {self.date}'
    

class RecentlyViewed(models.Model):
    """Модель для зберігання історії переглядів користувача"""
    session_key = models.CharField('Ключ сесії', max_length=40, db_index=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Товар', related_name='recently_viewed')
    viewed_at = models.DateTimeField('Дата перегляду', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Переглянутий товар'
        verbose_name_plural = 'Історія переглядів'
        ordering = ['-viewed_at']
        unique_together = ['session_key', 'product']  # Запобігає дублюванню
    
    def __str__(self):
        return f"{self.session_key} - {self.product.title}"
    
    # shop/models.py (додати в кінець файлу)

# ============================================================
# МОДЕЛІ ДЛЯ ЮРИДИЧНИХ ОСІБ ТА ДОКУМЕНТІВ
# ============================================================

class LegalEntity(models.Model):
    """Юридична особа (підприємство/організація)"""
    
    # Основна інформація
    name = models.CharField('Назва організації', max_length=250)
    short_name = models.CharField('Коротка назва', max_length=100, blank=True)
    code_edrpou = models.CharField('Код ЄДРПОУ', max_length=10, unique=True, help_text='Унікальний код підприємства')
    
    # Реквізити
    tax_number = models.CharField('ІПН', max_length=12, blank=True, help_text='Індивідуальний податковий номер')
    vat_number = models.CharField('Платник ПДВ', max_length=12, blank=True, help_text='Свідоцтво ПДВ')
    
    # Контактна інформація
    legal_address = models.TextField('Юридична адреса', blank=True)
    actual_address = models.TextField('Фактична адреса', blank=True)
    phone = models.CharField('Телефон', max_length=20, blank=True)
    email = models.EmailField('Email', blank=True)
    website = models.URLField('Веб-сайт', blank=True)
    
    # Банківські реквізити
    bank_name = models.CharField('Назва банку', max_length=200, blank=True)
    bank_account = models.CharField('Розрахунковий рахунок', max_length=29, blank=True)
    bank_mfo = models.CharField('МФО', max_length=6, blank=True)
    
    # Додатково
    director = models.CharField('Директор/Керівник', max_length=200, blank=True)
    accountant = models.CharField('Головний бухгалтер', max_length=200, blank=True)
    
    # Статус
    is_active = models.BooleanField('Активний', default=True)
    notes = models.TextField('Примітки', blank=True)
    
    created_at = models.DateTimeField('Дата створення', auto_now_add=True)
    updated_at = models.DateTimeField('Дата оновлення', auto_now=True)
    
    class Meta:
        verbose_name = 'Юридична особа'
        verbose_name_plural = 'Юридичні особи'
        ordering = ['name']
        indexes = [
            models.Index(fields=['code_edrpou']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.code_edrpou})"
    
    def get_full_address(self):
        if self.legal_address:
            return self.legal_address
        return self.actual_address


class ServiceCategory(models.Model):
    """Категорія послуг"""
    name = models.CharField('Назва категорії', max_length=150)
    slug = models.SlugField('URL', max_length=150, unique=True, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, verbose_name='Батьківська категорія')
    description = models.TextField('Опис', blank=True)
    icon = models.CharField('Іконка (Font Awesome)', max_length=50, blank=True, help_text='Наприклад: fa-print')
    sort_order = models.IntegerField('Порядок сортування', default=0)
    is_active = models.BooleanField('Активна', default=True)
    
    class Meta:
        verbose_name = 'Категорія послуг'
        verbose_name_plural = 'Категорії послуг'
        ordering = ['sort_order', 'name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.parent:
            return f"{self.parent} → {self.name}"
        return self.name


class Service(models.Model):
    """Послуга або робота"""
    SERVICE_TYPES = [
        ('service', 'Послуга'),
        ('spare_part', 'Комплектуюча'),
        ('consumable', 'Витратний матеріал'),
    ]
    
    name = models.CharField('Назва', max_length=250)
    slug = models.SlugField('URL', max_length=250, unique=True, blank=True)
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, verbose_name='Категорія', related_name='services')
    service_type = models.CharField('Тип', max_length=20, choices=SERVICE_TYPES, default='service')
    
    # Ціна
    price = models.DecimalField('Ціна', max_digits=12, decimal_places=2, default=0)
    cost_price = models.DecimalField('Собівартість', max_digits=12, decimal_places=2, blank=True, null=True, help_text='Для аналітики')
    
    # Опис
    description = models.TextField('Опис', blank=True)
    execution_time = models.CharField('Час виконання', max_length=100, blank=True, help_text='Наприклад: 1-2 дня, 1 година')
    
    # Характеристики (JSON)
    specifications = models.JSONField('Характеристики', default=dict, blank=True)
    
    # Статус
    is_active = models.BooleanField('Активна', default=True)
    is_popular = models.BooleanField('Популярна послуга', default=False)
    
    created_at = models.DateTimeField('Дата створення', auto_now_add=True)
    updated_at = models.DateTimeField('Дата оновлення', auto_now=True)
    
    class Meta:
        verbose_name = 'Послуга/Комплектуюча'
        verbose_name_plural = 'Послуги та комплектуючі'
        ordering = ['service_type', 'name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.get_service_type_display()}: {self.name} - {self.price}₴"


class Invoice(models.Model):
    """Рахунок-фактура для юридичної особи"""
    INVOICE_TYPES = [
        ('invoice', 'Рахунок-фактура'),
        ('tax_invoice', 'Податкова накладна'),
        ('proforma', 'Проформа-рахунок'),
    ]
    
    PAYMENT_STATUS = [
        ('unpaid', 'Не оплачений'),
        ('partial', 'Частково оплачений'),
        ('paid', 'Оплачений'),
        ('overdue', 'Прострочений'),
    ]
    
    # Номер і дата
    invoice_number = models.CharField('Номер рахунку', max_length=20, unique=True)
    invoice_date = models.DateField('Дата виставлення', default=date.today)  # використовуємо date.today
    due_date = models.DateField('Термін оплати', blank=True, null=True)

    # Контрагенти
    legal_entity = models.ForeignKey(LegalEntity, on_delete=models.CASCADE, verbose_name='Отримувач (Покупець)', related_name='invoices')
    seller = models.CharField('Продавець', max_length=250, default='ТОВ "TechShop"')
    seller_code = models.CharField('Код ЄДРПОУ продавця', max_length=10, default='12345678')
    seller_address = models.TextField('Адреса продавця', default='м. Київ, вул. Технічна, 1')
    
    # Суми
    subtotal = models.DecimalField('Сума без ПДВ', max_digits=12, decimal_places=2, default=0)
    vat_rate = models.DecimalField('Ставка ПДВ', max_digits=5, decimal_places=2, default=20)
    vat_amount = models.DecimalField('Сума ПДВ', max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField('Загальна сума', max_digits=12, decimal_places=2, default=0)
    
    # Оплата
    payment_status = models.CharField('Статус оплати', max_length=20, choices=PAYMENT_STATUS, default='unpaid')
    paid_amount = models.DecimalField('Сплачено', max_digits=12, decimal_places=2, default=0)
    payment_date = models.DateField('Дата оплати', blank=True, null=True)
    payment_method = models.CharField('Спосіб оплати', max_length=50, blank=True)
    
    # Додатково
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, blank=True, null=True, verbose_name='Замовлення')
    notes = models.TextField('Примітки', blank=True)
    
    # Терміни
    due_date = models.DateField('Термін оплати', blank=True, null=True)
    created_by = models.CharField('Створив', max_length=100, blank=True)
    
    created_at = models.DateTimeField('Дата створення', auto_now_add=True)
    updated_at = models.DateTimeField('Дата оновлення', auto_now=True)
    
    class Meta:
        verbose_name = 'Рахунок-фактура'
        verbose_name_plural = 'Рахунки-фактури'
        ordering = ['-invoice_date', '-invoice_number']
    
    def __str__(self):
        return f"Рахунок №{self.invoice_number} від {self.invoice_date}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            last_invoice = Invoice.objects.order_by('-id').first()
            if last_invoice:
                new_num = last_invoice.id + 1
            else:
                new_num = 1
            
            # Просто число без форматування
            self.invoice_number = str(new_num)
        
        super().save(*args, **kwargs)


class InvoiceItem(models.Model):
    """Позиція в рахунку"""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items', verbose_name='Рахунок')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, blank=True, null=True, verbose_name='Послуга/Товар')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, blank=True, null=True, verbose_name='Товар')
    
    name = models.CharField('Назва', max_length=250)
    quantity = models.DecimalField('Кількість', max_digits=10, decimal_places=2, default=1)
    unit = models.CharField('Одиниця виміру', max_length=20, default='шт')
    price = models.DecimalField('Ціна', max_digits=12, decimal_places=2)
    vat_rate = models.DecimalField('Ставка ПДВ', max_digits=5, decimal_places=2, default=20)
    total = models.DecimalField('Сума', max_digits=12, decimal_places=2, default=0)
    
    def save(self, *args, **kwargs):
        self.total = self.quantity * self.price
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} x {self.quantity} = {self.total}₴"

    
class AdminNotification(models.Model):
    """Сповіщення для адміністраторів"""
    
    NOTIFICATION_TYPES = [
        ('new_order', 'Нове замовлення'),
        ('new_review', 'Новий відгук'),
        ('low_stock', 'Товар закінчується'),
        ('new_user', 'Новий користувач'),
    ]
    
    notification_type = models.CharField('Тип сповіщення', max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField('Заголовок', max_length=200)
    message = models.TextField('Повідомлення')
    link = models.CharField('Посилання', max_length=200, blank=True)
    is_read = models.BooleanField('Прочитано', default=False)
    created_at = models.DateTimeField('Створено', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Сповіщення'
        verbose_name_plural = 'Сповіщення'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.created_at.strftime('%d.%m.%Y %H:%M')}"