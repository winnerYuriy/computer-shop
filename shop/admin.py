# shop/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, Attribute, AttributeValue, ProductAttributeValue, Order, Cart


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
        'id', 'name', 'category', 'price', 'final_price_display', 
        'stock', 'is_active', 'is_new', 'is_bestseller', 'image_preview', 'created_at'
    ]
    list_filter = ['category', 'is_active', 'is_new', 'is_bestseller', 'created_at']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['price', 'stock', 'is_active', 'is_new', 'is_bestseller']
    readonly_fields = ['created_at', 'updated_at', 'image_preview']
    inlines = [ProductAttributeValueInline]
    
    fieldsets = (
        ('Основна інформація', {
            'fields': ('name', 'slug', 'category', 'description')
        }),
        ('Ціна та наявність', {
            'fields': ('price', 'old_price', 'stock')
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
        """Відображає акційну ціну зі знижкою (проста версія без format_html)"""
        if obj.old_price:
            discount = int(((obj.price - obj.old_price) / obj.price) * 100)
            return f"{obj.price}₴ → {obj.old_price}₴ (-{discount}%)"
        return f'{obj.price}₴'
    final_price_display.short_description = 'Ціна зі знижкою'
    
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