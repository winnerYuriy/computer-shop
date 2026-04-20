# shop/admin.py

from django.contrib import admin, messages
from django.utils.html import mark_safe
from django.utils.text import slugify
from django import forms
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from mptt.admin import DraggableMPTTAdmin
import logging
import os
from django.conf import settings
from django.core.files.base import ContentFile

from .models import (
    Category, Brand, Promotion, Product, ProductImage,
    Property, PropertyValue, Order, Cart, Review, VisitLog
)
from .utils import get_token, download_product_images, save_product_image


logger = logging.getLogger(__name__)


# ===================================================================
# Inline для додаткових зображень
# ===================================================================

class ProductImageInline(admin.TabularInline):
    """Inline для додаткових зображень товару"""
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'order']
    ordering = ['order']


# ===================================================================
# Кастомний фільтр для товарів без зображень
# ===================================================================

class HasMainImageFilter(admin.SimpleListFilter):
    """Фільтр для товарів за наявністю головного зображення"""
    title = 'Головне зображення'
    parameter_name = 'has_image'
    
    def lookups(self, request, model_admin):
        return [
            ('yes', 'Є зображення'),
            ('no', 'Немає зображення'),
        ]
    
    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(main_image='')
        if self.value() == 'no':
            return queryset.filter(main_image='')
        return queryset


# ===================================================================
# Дія для завантаження зображень для вибраних товарів
# ===================================================================

@admin.action(description='📸 Завантажити зображення з API для вибраних товарів')
def download_images_from_api(modeladmin, request, queryset):
    """Завантаження зображень для вибраних товарів через API"""
    
    products_without_images = queryset.filter(main_image='')
    
    if not products_without_images.exists():
        messages.warning(request, 'Серед вибраних товарів немає товарів без зображень')
        return
    
    HOST = os.getenv('HOST')
    token_brain = get_token(f'{HOST}/auth')
    
    if not token_brain:
        messages.error(request, '❌ Не вдалося отримати доступ до API')
        return
    
    success_count = 0
    for product in products_without_images:
        image_data = download_product_images(product.id, token_brain)
        if image_data and image_data.get("status") == 1 and image_data.get("result"):
            images = image_data["result"]
            if images and len(images) > 0:
                main_image_url = images[0].get("full_image") or images[0].get("url")
                if main_image_url:
                    try:
                        save_product_image(product, main_image_url)
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Помилка: {e}")
    
    messages.success(request, f'✅ Зображення завантажено для {success_count} товарів')


# ===================================================================
# ProductAdmin
# ===================================================================

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('image_preview', 'title', 'category', 'brand', 'price', 'quantity', 'available')
    list_filter = ('available', 'category', 'brand', HasMainImageFilter, 'created_at')
    search_fields = ('title', 'code', 'article')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('price', 'quantity', 'available')
    readonly_fields = ('created_at', 'updated_at', 'rating', 'image_preview', 'reviews_count')
    inlines = [ProductImageInline]
    filter_horizontal = ('promotions', 'property_values')
    actions = [download_images_from_api]
    
    fieldsets = (
        ('Основна інформація', {
            'fields': ('title', 'slug', 'category', 'brand', 'code', 'article')
        }),
        ('Описи', {
            'fields': ('description', 'full_description')
        }),
        ('Ціна та наявність', {
            'fields': ('price', 'old_price', 'discount', 'quantity', 'available')
        }),
        ('Гарантія та виробництво', {
            'fields': ('warranty', 'country')
        }),
        ('Зображення', {
            'fields': ('main_image', 'image_preview')
        }),
        ('Характеристики', {
            'fields': ('attributes', 'property_values'),
            'classes': ('collapse',)
        }),
        ('Акції', {
            'fields': ('promotions',),
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
    
    def image_preview(self, obj):
        if obj.main_image:
            return mark_safe(f'<img src="{obj.main_image.url}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />')
        return mark_safe('<span style="color: #999;">📷 Немає фото</span>')
    image_preview.short_description = 'Фото'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('download-missing-images/', self.admin_site.admin_view(self.download_missing_images), name='download-missing-images'),
        ]
        return custom_urls + urls
    
    def download_missing_images(self, request):
        if request.method == 'POST':
            products = Product.objects.filter(main_image='')
            if not products.exists():
                messages.warning(request, 'Немає товарів без зображень')
                return redirect('admin:shop_product_changelist')
            
            HOST = os.getenv('HOST')
            token_brain = get_token(f'{HOST}/auth')
            
            if not token_brain:
                messages.error(request, '❌ Не вдалося отримати доступ до API')
                return redirect('admin:shop_product_changelist')
            
            success_count = 0
            for product in products:
                image_data = download_product_images(product.id, token_brain)
                if image_data and image_data.get("status") == 1 and image_data.get("result"):
                    images = image_data["result"]
                    if images and len(images) > 0:
                        main_image_url = images[0].get("full_image") or images[0].get("url")
                        if main_image_url:
                            try:
                                save_product_image(product, main_image_url)
                                success_count += 1
                            except Exception as e:
                                logger.error(f"Помилка: {e}")
            
            messages.success(request, f'✅ Зображення завантажено для {success_count} товарів')
            return redirect('admin:shop_product_changelist')
        
        products_count = Product.objects.filter(main_image='').count()
        return render(request, 'admin/confirm_download_images.html', {
            'products_count': products_count,
            'title': 'Завантаження зображень'
        })


# ===================================================================
# Інші реєстрації адміністраторів
# ===================================================================

@admin.register(Category)
class CategoryAdmin(DraggableMPTTAdmin):
    list_display = ('tree_actions', 'indented_title', 'slug')
    list_display_links = ('indented_title',)
    prepopulated_fields = {'slug': ('name',)}
    
    def save_model(self, request, obj, form, change):
        if not obj.slug:
            obj.slug = slugify(obj.name)
        super().save_model(request, obj, form, change)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'image_preview')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    
    def image_preview(self, obj):
        if obj.logo:
            return mark_safe(f'<img src="{obj.logo.url}" style="width: 50px; height: auto;" />')
        return "Немає логотипу"
    image_preview.short_description = 'Логотип'


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(PropertyValue)
class PropertyValueAdmin(admin.ModelAdmin):
    list_display = ('value', 'property')
    list_filter = ('property',)
    search_fields = ('value',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'phone', 'total_amount', 'status', 'is_paid', 'created_at')
    list_filter = ('status', 'is_paid', 'created_at')
    search_fields = ('full_name', 'phone', 'email')
    list_editable = ('status',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user_name', 'product', 'rating', 'comment_short', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'rating', 'created_at')
    search_fields = ('user_name', 'comment', 'product__title')
    list_editable = ('is_approved',)
    
    def comment_short(self, obj):
        return obj.comment[:50] + '…' if len(obj.comment) > 50 else obj.comment
    comment_short.short_description = 'Коментар'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')