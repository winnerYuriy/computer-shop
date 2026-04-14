# shop/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from mptt.admin import MPTTModelAdmin  # для зручного відображення дерева категорій
from .models import (
    Category, Brand, Promotion, Product, ProductImage,
    Property, PropertyValue, Review, Order, Cart
)


# -------------------------------------------------------------------
# Категорії (MPTT)
# -------------------------------------------------------------------
@admin.register(Category)
class CategoryAdmin(MPTTModelAdmin):
    list_display = ['name', 'slug', 'parent']
    list_filter = ['parent']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['parent']
    fields = ('name', 'slug', 'parent', 'image', 'description')
    mptt_level_indent = 20  # відступ для ієрархічного відображення


# -------------------------------------------------------------------
# Бренди
# -------------------------------------------------------------------
@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'logo_preview']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['logo_preview']

    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: contain;" />', obj.logo.url)
        return "—"
    logo_preview.short_description = 'Логотип'


# -------------------------------------------------------------------
# Акції
# -------------------------------------------------------------------
@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ['name', 'promotion_type', 'discount_percent', 'is_active', 'start_date', 'end_date', 'is_current']
    list_filter = ['promotion_type', 'is_active', 'start_date']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['discount_percent', 'is_active']
    readonly_fields = ['is_current']

    def is_current(self, obj):
        return obj.is_current
    is_current.boolean = True
    is_current.short_description = 'Активна зараз'


# -------------------------------------------------------------------
# Зображення товарів (Inline)
# -------------------------------------------------------------------
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'order']
    ordering = ['order']


# -------------------------------------------------------------------
# Товари
# -------------------------------------------------------------------
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
    'id', 'title', 'category', 'brand', 'price', 'final_price',
    'quantity', 'available', 'is_available', 'rating', 'created_at'
    ]
    list_filter = ['category', 'brand', 'available', 'promotions']
    search_fields = ['title', 'article', 'code']
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ['price', 'quantity', 'available']
    readonly_fields = ['created_at', 'updated_at', 'rating', 'reviews_count', 'final_price']
    inlines = [ProductImageInline]
    filter_horizontal = ['promotions', 'property_values']
    fieldsets = (
        ('Основна інформація', {
            'fields': ('title', 'slug', 'category', 'brand', 'article', 'code')
        }),
        ('Описи', {
            'fields': ('description', 'full_description')
        }),
        ('Ціна та наявність', {
            'fields': ('price', 'old_price', 'discount', 'final_price', 'quantity', 'available')
        }),
        ('Гарантія та виробництво', {
            'fields': ('warranty', 'country')
        }),
        ('Зображення', {
            'fields': ('main_image',)
        }),
        ('Характеристики', {
            'fields': ('attributes', 'property_values'),
            'classes': ('collapse',)
        }),
        ('Рейтинг', {
            'fields': ('rating', 'reviews_count'),
            'classes': ('collapse',)
        }),
        ('Службова інформація', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def final_price(self, obj):
        return obj.final_price
    final_price.short_description = 'Ціна зі знижкою'

    def is_available_display(self, obj):
        return obj.availability_text()
    is_available_display.short_description = 'Статус'
    is_available_display.boolean = True

    def save_model(self, request, obj, form, change):
        # Якщо це новий товар, спочатку зберігаємо, щоб створився id для шляху завантаження зображень
        if not change:
            obj.save()
        super().save_model(request, obj, form, change)


# -------------------------------------------------------------------
# Властивості (характеристики)
# -------------------------------------------------------------------
@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'category_list']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ['categories']

    def category_list(self, obj):
        return ", ".join([c.name for c in obj.categories.all()])
    category_list.short_description = 'Категорії'


@admin.register(PropertyValue)
class PropertyValueAdmin(admin.ModelAdmin):
    list_display = ['id', 'property', 'value']
    list_filter = ['property']
    search_fields = ['value']


# -------------------------------------------------------------------
# Відгуки
# -------------------------------------------------------------------
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_name', 'product_link', 'rating', 'comment_short', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'rating', 'created_at']
    search_fields = ['user_name', 'comment', 'product__title']
    list_editable = ['is_approved']
    readonly_fields = ['created_at']

    def product_link(self, obj):
        url = reverse('admin:shop_product_change', args=[obj.product.id])
        return format_html('<a href="{}">{}</a>', url, obj.product.title)
    product_link.short_description = 'Товар'

    def comment_short(self, obj):
        return obj.comment[:50] + '…' if len(obj.comment) > 50 else obj.comment
    comment_short.short_description = 'Коментар'

    actions = ['approve_reviews']

    @admin.action(description='Опублікувати вибрані відгуки')
    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        # Оновлюємо рейтинг товарів
        for review in queryset:
            review.product.update_rating()
        self.message_user(request, f'Опубліковано {updated} відгук(ів).')


# -------------------------------------------------------------------
# Замовлення
# -------------------------------------------------------------------
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'full_name', 'phone', 'total_amount', 'status', 'status_badge',
        'is_paid', 'delivery_method', 'created_at'
    ]
    list_filter = ['status', 'is_paid', 'delivery_method', 'created_at']
    search_fields = ['full_name', 'phone', 'email', 'id']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['status']  

    fieldsets = (
        ('Інформація про покупця', {
            'fields': ('full_name', 'phone', 'email')
        }),
        ('Доставка', {
            'fields': ('delivery_method', 'city', 'address', 'nova_post_office', 'comment')
        }),
        ('Замовлення', {
            'fields': ('products', 'total_amount', 'status')
        }),
        ('Оплата', {
            'fields': ('payment_id', 'is_paid', 'payment_method')
        }),
        ('Службова інформація', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        colors = {
            'new': '#007bff',
            'processing': '#ffc107',
            'paid': '#28a745',
            'shipped': '#6f42c1',
            'delivered': '#20c997',
            'cancelled': '#dc3545',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 12px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Статус'


# -------------------------------------------------------------------
# Кошик (тільки перегляд)
# -------------------------------------------------------------------
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['session_key', 'get_total_items', 'get_total_price', 'created_at', 'updated_at']
    search_fields = ['session_key']
    readonly_fields = ['created_at', 'updated_at']

    def get_total_items(self, obj):
        return obj.get_total_items()
    get_total_items.short_description = 'Кількість товарів'

    def get_total_price(self, obj):
        return f"{obj.get_total_price()} ₴"
    get_total_price.short_description = 'Загальна сума'