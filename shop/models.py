# shop/models.py

from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.core.exceptions import ValidationError


class Category(models.Model):
    """Категорія товарів з підтримкою вкладеності (дерево)"""
    name = models.CharField('Назва', max_length=100)
    slug = models.SlugField('URL', max_length=100, blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name='Батьківська категорія',
        related_name='children'
    )
    description = models.TextField('Опис', blank=True)
    image = models.ImageField('Зображення', upload_to='categories/', blank=True)
    created_at = models.DateTimeField('Створено', auto_now_add=True)
    
    # Повний шлях для URL
    full_slug = models.CharField(
        'Повний URL-шлях',
        max_length=500,
        blank=True,
        unique=True,
        editable=False
    )
    
    class Meta:
        verbose_name = 'Категорія'
        verbose_name_plural = 'Категорії'
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        
        if self.parent:
            self.full_slug = f"{self.parent.full_slug}{self.slug}/"
        else:
            self.full_slug = f"{self.slug}/"
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.parent:
            return f"{self.parent} → {self.name}"
        return self.name
    
    def get_absolute_url(self):
        return reverse('shop:category_detail', args=[self.full_slug])
    
    def get_children(self):
        return self.children.all()
    
    def get_all_descendants(self):
        return Category.objects.filter(full_slug__startswith=self.full_slug).exclude(id=self.id)
    
    def get_all_products(self):
        descendants_slugs = Category.objects.filter(
            full_slug__startswith=self.full_slug
        ).values_list('full_slug', flat=True)
        
        return Product.objects.filter(
            category__full_slug__in=descendants_slugs,
            is_active=True
        )
    
    @property
    def level(self):
        if not self.full_slug:
            return 0
        return self.full_slug.count('/') - 1


class Attribute(models.Model):
    """
    Властивість/характеристика товару
    Наприклад: "Колір", "Розмір екрану", "Об'єм пам'яті", "Гарантія", "Країна виробник"
    """
    TYPE_CHOICES = [
        ('text', 'Текст'),
        ('number', 'Число'),
        ('boolean', 'Так/Ні'),
        ('color', 'Колір'),
        ('date', 'Дата'),
    ]
    
    name = models.CharField('Назва атрибута', max_length=100)
    slug = models.SlugField('URL-ідентифікатор', max_length=100, unique=True, blank=True)
    type = models.CharField('Тип даних', max_length=20, choices=TYPE_CHOICES, default='text')
    unit = models.CharField('Одиниця виміру', max_length=20, blank=True, help_text='наприклад: GB, GHz, см, років')
    is_filterable = models.BooleanField('Використовувати у фільтрах', default=True)
    is_visible = models.BooleanField('Показувати на картці товару', default=True)
    categories = models.ManyToManyField(
        Category,
        verbose_name='Категорії',
        blank=True,
        related_name='attributes',
        help_text='Якщо не вибрано жодної, атрибут доступний для всіх категорій'
    )
    sort_order = models.IntegerField('Порядок сортування', default=0)
    
    class Meta:
        verbose_name = 'Атрибут'
        verbose_name_plural = 'Атрибути'
        ordering = ['sort_order', 'name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class AttributeValue(models.Model):
    """
    Значення атрибута (наприклад: "червоний", "16GB", "2 роки", "Китай")
    Це значення може використовуватись багатьма товарами
    """
    attribute = models.ForeignKey(
        Attribute,
        on_delete=models.CASCADE,
        verbose_name='Атрибут',
        related_name='values'
    )
    value_text = models.CharField('Значення (текст)', max_length=255, blank=True)
    value_number = models.DecimalField('Значення (число)', max_digits=10, decimal_places=2, blank=True, null=True)
    value_boolean = models.BooleanField('Значення (так/ні)', default=False)
    value_color = models.CharField('Значення (колір)', max_length=7, blank=True, help_text='HEX код, наприклад #FF0000')
    
    class Meta:
        verbose_name = 'Значення атрибута'
        verbose_name_plural = 'Значення атрибутів'
        unique_together = ['attribute', 'value_text']
    
    def __str__(self):
        if self.attribute.type == 'text':
            return f"{self.attribute.name}: {self.value_text}"
        elif self.attribute.type == 'number':
            return f"{self.attribute.name}: {self.value_number} {self.attribute.unit}"
        elif self.attribute.type == 'boolean':
            return f"{self.attribute.name}: {'Так' if self.value_boolean else 'Ні'}"
        elif self.attribute.type == 'color':
            return f"{self.attribute.name}: {self.value_color}"
        return f"{self.attribute.name}: {self.value_text}"
    
    def get_display_value(self):
        """Повертає відформатоване значення для відображення"""
        if self.attribute.type == 'text':
            return self.value_text
        elif self.attribute.type == 'number':
            return f"{self.value_number} {self.attribute.unit}" if self.attribute.unit else str(self.value_number)
        elif self.attribute.type == 'boolean':
            return 'Так' if self.value_boolean else 'Ні'
        elif self.attribute.type == 'color':
            return f'<span style="background-color: {self.value_color}; padding: 0 15px;">&nbsp;&nbsp;</span> {self.value_color}'
        return ''


class Product(models.Model):
    """Товар (ноутбук, монітор, клавіатура, мишка тощо)"""
    
    # Основна інформація
    name = models.CharField('Назва', max_length=200)
    slug = models.SlugField('URL', max_length=200, unique=True, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        verbose_name='Категорія',
        related_name='products'
    )
    description = models.TextField('Опис')
    
    # Ціна та наявність
    price = models.DecimalField('Ціна', max_digits=10, decimal_places=2)
    old_price = models.DecimalField(
        'Стара ціна',
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Заповніть, якщо товар зі знижкою'
    )
    stock = models.PositiveIntegerField('Кількість на складі', default=0)
    
    # Зображення
    image = models.ImageField('Головне зображення', upload_to='products/', blank=True)
    gallery_images = models.JSONField(
        'Галерея зображень',
        default=list,
        blank=True,
        help_text='Список шляхів до додаткових зображень'
    )

    # Рейтинг та відгуки
    rating = models.DecimalField('Рейтинг', max_digits=3, decimal_places=2, default=0)
    reviews_count = models.PositiveIntegerField('Кількість відгуків', default=0)
    
    # Статус
    is_active = models.BooleanField('Активний', default=True)
    is_new = models.BooleanField('Новинка', default=False)
    is_bestseller = models.BooleanField('Хіт продажів', default=False)
    
    # SEO
    meta_title = models.CharField('SEO заголовок', max_length=200, blank=True)
    meta_description = models.TextField('SEO опис', max_length=500, blank=True)
    
    # Зв'язок зі значеннями атрибутів (через проміжну таблицю)
    attribute_values = models.ManyToManyField(
        AttributeValue,
        verbose_name='Значення характеристик',
        blank=True,
        related_name='products',
        through='ProductAttributeValue'
    )
    
    created_at = models.DateTimeField('Створено', auto_now_add=True)
    updated_at = models.DateTimeField('Оновлено', auto_now=True)
    
    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товари'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['is_new']),
            models.Index(fields=['is_bestseller']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('shop:product_detail', args=[self.slug])
    
    @property
    def final_price(self):
        return self.old_price if self.old_price else self.price
    
    @property
    def is_in_stock(self):
        return self.stock > 0
    
    @property
    def discount_percent(self):
        if self.old_price and self.price > 0:
            return int(((self.price - self.old_price) / self.price) * 100)
        return 0
    
    def get_attributes_by_category(self):
        """Отримує всі атрибути для категорії товару з їх значеннями"""
        # Атрибути, які належать до категорії товару (або глобальні)
        category_attributes = self.category.attributes.all()
        
        # Якщо немає специфічних для категорії, беремо всі
        if not category_attributes.exists():
            category_attributes = Attribute.objects.filter(categories__isnull=True)
        
        result = []
        for attr in category_attributes:
            # Знаходимо значення цього атрибута для поточного товару
            product_value = self.productattributevalue_set.filter(
                attribute_value__attribute=attr
            ).first()
            
            if product_value:
                result.append({
                    'attribute': attr,
                    'value': product_value.attribute_value,
                })
        
        return result


class Review(models.Model):
    """Відгук про товар"""
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
        return f'{self.user_name} - {self.product.name} - {self.rating}★'


class ProductAttributeValue(models.Model):
    """
    Проміжна таблиця: товар → значення атрибута
    Дозволяє додавати додаткову інформацію (наприклад, ціну за опцію)
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Товар')
    attribute_value = models.ForeignKey(AttributeValue, on_delete=models.CASCADE, verbose_name='Значення атрибута')
    extra_price = models.DecimalField('Додаткова ціна', max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        verbose_name = 'Значення характеристики товару'
        verbose_name_plural = 'Значення характеристик товарів'
        unique_together = ['product', 'attribute_value']
    
    def __str__(self):
        return f"{self.product.name} - {self.attribute_value}"


class Order(models.Model):
    """Замовлення користувача"""
    
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
    
    # Інформація про покупця
    full_name = models.CharField('ПІБ', max_length=200)
    phone = models.CharField('Телефон', max_length=20)
    email = models.EmailField('Email')
    address = models.TextField('Адреса доставки', blank=True)
    city = models.CharField('Місто', max_length=100, blank=True)
    nova_post_office = models.CharField('Відділення Нової Пошти', max_length=50, blank=True)
    delivery_method = models.CharField(
        'Спосіб доставки',
        max_length=20,
        choices=DELIVERY_CHOICES,
        default='nova_post'
    )
    
    comment = models.TextField('Коментар до замовлення', blank=True)
    
    # Дані замовлення
    products = models.JSONField(
        'Товари',
        default=list,
        help_text='[{"id": 1, "name": "...", "price": 1000, "quantity": 2, "image": "...", "attributes": [...]}]'
    )
    total_amount = models.DecimalField('Сума замовлення', max_digits=10, decimal_places=2)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='new')
    
    # Оплата
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
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f'Замовлення #{self.id} - {self.full_name} ({self.get_status_display()})'
    
    @property
    def status_badge_color(self):
        colors = {
            'new': 'primary',
            'processing': 'warning',
            'paid': 'info',
            'shipped': 'success',
            'delivered': 'success',
            'cancelled': 'danger',
        }
        return colors.get(self.status, 'secondary')


class Cart(models.Model):
    """Кошик для неавторизованих користувачів"""
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