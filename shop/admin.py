# shop/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Category, Product, Attribute, AttributeValue, ProductAttributeValue, Order, Cart, Review
from django.contrib.admin import AdminSite


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'full_slug', 'parent', 'level', 'created_at']
    list_filter = ['parent', 'created_at']
    search_fields = ['name', 'slug', 'full_slug']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['parent']
    readonly_fields = ['full_slug', 'level']
    
    fieldsets = (
        ('Основна інформація', {
            'fields': ('name', 'slug', 'parent', 'description')
        }),
        ('Зображення', {
            'fields': ('image',),
            'classes': ('collapse',)
        }),
        ('Системні поля', {
            'fields': ('full_slug', 'level', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def level(self, obj):
        return obj.level
    level.short_description = 'Рівень вкладеності'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent')


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'type', 'unit', 'is_filterable', 'is_visible', 'sort_order']
    list_filter = ['type', 'is_filterable', 'is_visible', 'categories']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_filterable', 'is_visible', 'sort_order']
    filter_horizontal = ['categories']


@admin.register(AttributeValue)
class AttributeValueAdmin(admin.ModelAdmin):
    list_display = ['id', 'attribute', 'get_display_value', 'value_text', 'value_number', 'value_boolean']
    list_filter = ['attribute', 'attribute__type']
    search_fields = ['value_text', 'value_color']
    
    def get_display_value(self, obj):
        return obj.get_display_value()
    get_display_value.short_description = 'Відображення'


class ProductAttributeValueInline(admin.TabularInline):
    model = ProductAttributeValue
    extra = 1
    autocomplete_fields = ['attribute_value']
    fields = ['attribute_value', 'extra_price']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'image_preview', 'name', 'category', 'price', 'final_price_display', 
        'stock', 'rating_display', 'reviews_count', 'is_active'
    ]
    list_filter = ['category', 'is_active', 'is_new', 'is_bestseller']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['price', 'stock', 'is_active']
    readonly_fields = ['created_at', 'updated_at', 'image_preview', 'rating_display']
    inlines = [ProductAttributeValueInline]
    
    fieldsets = (
        ('Основна інформація', {
            'fields': ('name', 'slug', 'category', 'description')
        }),
        ('Ціна та наявність', {
            'fields': ('price', 'old_price', 'stock')
        }),
        ('Рейтинг', {
            'fields': ('rating_display', 'reviews_count'),
            'classes': ('collapse',)
        }),
        ('Зображення', {
            'fields': ('image', 'gallery_images', 'image_preview'),
            'classes': ('wide',),
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Статус', {
            'fields': ('is_active', 'is_new', 'is_bestseller')
        }),
        ('Системні поля', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def final_price_display(self, obj):
        if obj.old_price:
            discount = int(((obj.price - obj.old_price) / obj.price) * 100)
            return f"{obj.price}₴ → {obj.old_price}₴ (-{discount}%)"
        return f'{obj.price}₴'
    final_price_display.short_description = 'Ціна зі знижкою'
    
    def rating_display(self, obj):
        """Відображає рейтинг зірками"""
        if obj.rating > 0:
            stars = ''.join(['★' for _ in range(int(obj.rating))])
            stars += ''.join(['☆' for _ in range(5 - int(obj.rating))])
            # ВИПРАВЛЕНО: використовуємо f-string замість format_html
            return f'<span style="color: #f59e0b;">{stars}</span> ({obj.rating})'
        return 'Немає оцінок'
    rating_display.short_description = 'Рейтинг'
    rating_display.allow_tags = True  # Дозволяє HTML теги
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 5px;" />',
                obj.image.url
            )
        return 'Немає фото'
    image_preview.short_description = 'Фото'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.save()
        super().save_model(request, obj, form, change)
    
    def get_form(self, request, obj=None, **kwargs):
        request._obj_ = obj
        return super().get_form(request, obj, **kwargs)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_name', 'product_link', 'rating_stars', 'comment_short', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'rating', 'created_at']
    search_fields = ['user_name', 'comment', 'product__name']
    list_editable = ['is_approved']
    list_display_links = ['id', 'user_name']
    readonly_fields = ['created_at', 'product_link', 'rating_stars']
    
    fieldsets = (
        ('Інформація про відгук', {
            'fields': ('product_link', 'user_name', 'email', 'rating_stars', 'comment')
        }),
        ('Модерація', {
            'fields': ('is_approved', 'created_at')
        }),
    )
    
    def product_link(self, obj):
        url = reverse('admin:shop_product_change', args=[obj.product.id])
        return format_html('<a href="{}">{}</a>', url, obj.product.name)
    product_link.short_description = 'Товар'
    
    def rating_stars(self, obj):
        """Відображає рейтинг зірками (без format_html)"""
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        # ВИПРАВЛЕНО: повертаємо звичайний рядок
        return f"{stars} ({obj.rating})"
    rating_stars.short_description = 'Оцінка'
    
    def comment_short(self, obj):
        return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
    comment_short.short_description = 'Коментар'
    
    actions = ['approve_reviews', 'reject_reviews']
    
    @admin.action(description='Опублікувати вибрані відгуки')
    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} відгук(ів) опубліковано.')
        # Оновлюємо рейтинг товарів
        for review in queryset:
            product = review.product
            approved_reviews = product.reviews.filter(is_approved=True)
            if approved_reviews.exists():
                from django.db.models import Avg
                avg_rating = approved_reviews.aggregate(Avg('rating'))['rating__avg']
                product.rating = round(avg_rating, 2)
                product.reviews_count = approved_reviews.count()
                product.save()
    
    @admin.action(description='Відхилити вибрані відгуки')
    def reject_reviews(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} відгук(ів) відхилено.')
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Оновлюємо рейтинг товару після зміни статусу
        product = obj.product
        approved_reviews = product.reviews.filter(is_approved=True)
        if approved_reviews.exists():
            from django.db.models import Avg
            avg_rating = approved_reviews.aggregate(Avg('rating'))['rating__avg']
            product.rating = round(avg_rating, 2)
            product.reviews_count = approved_reviews.count()
        else:
            product.rating = 0
            product.reviews_count = 0
        product.save()
    
    @admin.action(description='Опублікувати вибрані відгуки')
    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} відгук(ів) опубліковано.')
        # Оновлюємо рейтинг товарів
        for review in queryset:
            product = review.product
            approved_reviews = product.reviews.filter(is_approved=True)
            if approved_reviews.exists():
                from django.db.models import Avg
                avg_rating = approved_reviews.aggregate(Avg('rating'))['rating__avg']
                product.rating = round(avg_rating, 2)
                product.reviews_count = approved_reviews.count()
                product.save()
    
    @admin.action(description='Відхилити вибрані відгуки')
    def reject_reviews(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} відгук(ів) відхилено.')
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Оновлюємо рейтинг товару після зміни статусу
        product = obj.product
        approved_reviews = product.reviews.filter(is_approved=True)
        if approved_reviews.exists():
            from django.db.models import Avg
            avg_rating = approved_reviews.aggregate(Avg('rating'))['rating__avg']
            product.rating = round(avg_rating, 2)
            product.reviews_count = approved_reviews.count()
        else:
            product.rating = 0
            product.reviews_count = 0
        product.save()


@admin.register(ProductAttributeValue)
class ProductAttributeValueAdmin(admin.ModelAdmin):
    list_display = ['product', 'attribute_value', 'extra_price']
    list_filter = ['attribute_value__attribute']
    search_fields = ['product__name', 'attribute_value__value_text']
    autocomplete_fields = ['product', 'attribute_value']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'full_name', 'phone', 'total_amount', 'status_badge', 
        'is_paid', 'delivery_method', 'created_at'
    ]
    list_filter = ['status', 'is_paid', 'delivery_method', 'created_at']
    search_fields = ['full_name', 'phone', 'email', 'id']
    readonly_fields = ['created_at', 'updated_at']
    
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
        ('Системні поля', {
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
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 12px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Статус'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['session_key', 'get_total_items', 'get_total_price', 'created_at', 'updated_at']
    search_fields = ['session_key']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_total_items(self, obj):
        return obj.get_total_items()
    get_total_items.short_description = 'Товарів'
    
    def get_total_price(self, obj):
        return f'{obj.get_total_price()}₴'
    get_total_price.short_description = 'Сума'

class TechShopAdminSite(AdminSite):
    site_header = 'TechShop Адміністрування'
    site_title = 'TechShop Admin'
    index_title = 'Панель керування магазином'
    
    def get_app_list(self, request):
        app_list = super().get_app_list(request)
        # Додаємо статистику на головну
        from shop.models import Order, Product
        from django.contrib.auth.models import User
        
        request.total_orders = Order.objects.count()
        request.total_revenue = Order.objects.filter(is_paid=True).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        request.total_customers = User.objects.count()
        request.total_products = Product.objects.filter(is_active=True).count()
        
        return app_list


# Кастомізація заголовків адмінки
admin.site.site_header = 'TechShop Адміністрування'
admin.site.site_title = 'TechShop Admin'
admin.site.index_title = 'Панель керування магазином'