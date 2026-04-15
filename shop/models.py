# shop/models.py

import os
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
            self.slug = slugify(self.title)
        if self.discount and not self.old_price:
            self.old_price = self.price - (self.price * self.discount / 100)
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