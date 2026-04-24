# shop/admin.py

import os
import logging
from datetime import date
from django.contrib import admin, messages
from django.utils.html import mark_safe
from django.utils.text import slugify
from django import forms
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import path, reverse
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from mptt.admin import DraggableMPTTAdmin
from django.conf import settings
from django.core.files.base import ContentFile
from .models import (
    Category, Brand, Promotion, Product, ProductImage,Property, 
    PropertyValue, Order, Cart, Review, VisitLog, LegalEntity, 
    ServiceCategory, Service, Invoice, InvoiceItem
)
from .utils import (
    download_product_images_by_code, get_token, 
    get_product_data_by_code, get_product_images_by_product_id,
    save_image_from_url, get_image_url_by_product_code
)

logger = logging.getLogger(__name__)

# Константи
HOST = os.getenv('BRAIN_HOST', 'http://api.brain.com.ua')


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
# Масові дії для товарів
# ===================================================================

@admin.action(description='📸 Завантажити зображення з API для вибраних товарів')
def download_images_from_api(modeladmin, request, queryset):
    """Завантаження зображень для вибраних товарів через API"""
    
    # Беремо товари без зображень
    products_without_images = queryset.filter(main_image='')
    
    if not products_without_images.exists():
        messages.warning(request, 'Серед вибраних товарів немає товарів без зображень')
        return
    
    # Отримуємо токен
    auth_url = f'{HOST}/auth'
    token_brain = get_token(auth_url)
    
    if not token_brain:
        messages.error(request, '❌ Не вдалося отримати доступ до API')
        return
    
    success_count = 0
    for product in products_without_images:
        if not product.code:
            logger.warning(f'Товар {product.id} не має code (product_code)')
            continue
        
        # Використовуємо функцію завантаження зображень за кодом
        if download_product_images_by_code(product, token_brain):
            success_count += 1
    
    messages.success(request, f'✅ Зображення завантажено для {success_count} товарів')


@admin.action(description='🗑️ Видалити головні зображення у вибраних товарах')
def delete_main_images(modeladmin, request, queryset):
    """Видаляє головні зображення у вибраних товарах"""
    count = 0
    for product in queryset:
        if product.main_image:
            # Видаляємо фізичний файл
            product.main_image.delete(save=False)
            product.main_image = None
            product.save(update_fields=['main_image'])
            count += 1
    
    if count:
        messages.success(request, f'✅ Головні зображення видалено для {count} товарів.')
    else:
        messages.warning(request, '⚠️ У вибраних товарах не було головних зображень.')


@admin.action(description='🗑️ Видалити всі зображення (головні та додаткові) у вибраних товарах')
def delete_all_images(modeladmin, request, queryset):
    """Видаляє головні та додаткові зображення у вибраних товарах"""
    main_count = 0
    gallery_count = 0
    
    for product in queryset:
        # Видаляємо головне зображення
        if product.main_image:
            product.main_image.delete(save=False)
            product.main_image = None
            main_count += 1
        
        # Видаляємо додаткові зображення (ProductImage)
        product_images = ProductImage.objects.filter(product=product)
        for img in product_images:
            if img.image:
                img.image.delete(save=False)
            img.delete()
            gallery_count += 1
        
        product.save()
    
    messages.success(
        request, 
        f'✅ Видалено головні зображення: {main_count}, додаткові: {gallery_count}'
    )


# ===================================================================
# ProductAdmin
# ===================================================================

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('image_preview_with_delete', 'title', 'category', 'brand', 'price', 'quantity', 'available')
    list_filter = ('available', 'category', 'brand', HasMainImageFilter, 'created_at')
    search_fields = ('title', 'code', 'article')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('price', 'quantity', 'available')
    readonly_fields = ('created_at', 'updated_at', 'rating', 'image_preview', 'reviews_count')
    inlines = [ProductImageInline]
    filter_horizontal = ('promotions', 'property_values')
    actions = [download_images_from_api, delete_main_images, delete_all_images]
    
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
        """Відображення мініатюри зображення"""
        if obj.main_image:
            return mark_safe(f'<img src="{obj.main_image.url}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />')
        return mark_safe('<span style="color: #999;">📷 Немає фото</span>')
    image_preview.short_description = 'Фото'
    
    def image_preview_with_delete(self, obj):
        """Відображення мініатюри з кнопкою видалення поруч"""
        if obj.main_image:
            image_html = mark_safe(f'<img src="{obj.main_image.url}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />')
            delete_url = reverse('admin:delete_single_main_image', args=[obj.id])
            button_html = mark_safe(
                f'<a href="{delete_url}" style="margin-left: 8px; background: #dc3545; color: white; padding: 4px 8px; border-radius: 4px; text-decoration: none; font-size: 11px; display: inline-block;" onclick="return confirm(\'Ви впевнені, що хочете видалити зображення?\')">🗑️</a>'
            )
            return mark_safe(f'{image_html} {button_html}')
        return mark_safe('<span style="color: #999;">📷 Немає фото</span>')
    image_preview_with_delete.short_description = 'Фото'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('download-missing-images/', self.admin_site.admin_view(self.download_missing_images), name='download-missing-images'),
            path('<int:product_id>/delete-main-image/', self.admin_site.admin_view(self.delete_single_main_image), name='delete_single_main_image'),
        ]
        return custom_urls + urls
    
    def download_missing_images(self, request):
        """Завантаження зображень для всіх товарів без фото"""
        if request.method == 'POST':
            products = Product.objects.filter(main_image='')
            if not products.exists():
                messages.warning(request, 'Немає товарів без зображень')
                return redirect('admin:shop_product_changelist')
            
            auth_url = f'{HOST}/auth'
            token_brain = get_token(auth_url)
            
            if not token_brain:
                messages.error(request, '❌ Не вдалося отримати доступ до API')
                return redirect('admin:shop_product_changelist')
            
            success_count = 0
            for product in products:
                if not product.code:
                    continue
                
                if download_product_images_by_code(product, token_brain):
                    success_count += 1
            
            messages.success(request, f'✅ Зображення завантажено для {success_count} товарів')
            return redirect('admin:shop_product_changelist')
        
        products_count = Product.objects.filter(main_image='').count()
        return render(request, 'admin/confirm_download_images.html', {
            'products_count': products_count,
            'title': 'Завантаження зображень'
        })
    
    def delete_single_main_image(self, request, product_id):
        """Видалення головного зображення для одного товару"""
        product = get_object_or_404(Product, id=product_id)
        
        if product.main_image:
            product.main_image.delete(save=False)
            product.main_image = None
            product.save(update_fields=['main_image'])
            messages.success(request, f'✅ Головне зображення видалено для товару "{product.title}"')
        else:
            messages.warning(request, f'⚠️ У товару "{product.title}" немає головного зображення')
        
        return redirect(request.META.get('HTTP_REFERER', 'admin:shop_product_changelist'))
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Додаємо контекст для відображення кнопки видалення на сторінці редагування"""
        extra_context = extra_context or {}
        product = self.get_object(request, object_id)
        extra_context['has_main_image'] = bool(product and product.main_image)
        extra_context['delete_image_url'] = reverse('admin:delete_single_main_image', args=[object_id])
        return super().change_view(request, object_id, form_url, extra_context=extra_context)


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
    list_display = ('id', 'full_name', 'phone', 'total_amount', 'status', 'is_paid', 'legal_entity', 'created_at')
    list_filter = ('status', 'is_paid', 'created_at', 'legal_entity')
    search_fields = ('full_name', 'phone', 'email', 'id')
    list_editable = ('status',)
    readonly_fields = ('created_at', 'updated_at')
    
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
        ('Юридична особа', {
            'fields': ('legal_entity', 'invoice_required'),
            'classes': ('collapse',)
        }),
        ('Оплата', {
            'fields': ('payment_id', 'is_paid', 'payment_method')
        }),
        ('Системні поля', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['create_invoice_for_selected']
    
    @admin.action(description='📄 Створити рахунок-фактуру для вибраних замовлень')
    def create_invoice_for_selected(self, request, queryset):
        from .models import Invoice, InvoiceItem
        from decimal import Decimal
        
        created_count = 0
        for order in queryset:
            if not order.legal_entity:
                self.message_user(request, f'Замовлення #{order.id}: не обрано юридичну особу', level='ERROR')
                continue
            
            if not order.invoice_required:
                self.message_user(request, f'Замовлення #{order.id}: не потрібен рахунок', level='WARNING')
                continue
            
            # Перевіряємо, чи вже є рахунок
            if Invoice.objects.filter(order=order).exists():
                self.message_user(request, f'Замовлення #{order.id}: рахунок вже створено', level='WARNING')
                continue
            
            # Розраховуємо суми
            subtotal = Decimal(str(order.total_amount))
            vat_amount = subtotal * Decimal('0.2')
            total_amount = subtotal + vat_amount
            
            # Створюємо рахунок
            invoice = Invoice.objects.create(
                legal_entity=order.legal_entity,
                order=order,
                subtotal=subtotal,
                vat_amount=vat_amount,
                total_amount=total_amount,
                created_by=request.user.username,
            )
            
            # Додаємо позиції з замовлення
            for item in order.products:
                InvoiceItem.objects.create(
                    invoice=invoice,
                    name=item.get('name', 'Товар'),
                    quantity=Decimal(str(item.get('quantity', 1))),
                    price=Decimal(str(item.get('price', 0))),
                    total=Decimal(str(item.get('quantity', 1))) * Decimal(str(item.get('price', 0))),
                )
            
            created_count += 1
        
        self.message_user(request, f'✅ Створено рахунків: {created_count}')

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

# ============================================================
# АДМІНІСТРУВАННЯ ЮРИДИЧНИХ ОСІБ
# ============================================================

@admin.register(LegalEntity)
class LegalEntityAdmin(admin.ModelAdmin):
    list_display = ['code_edrpou', 'name', 'short_name', 'phone', 'email', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code_edrpou', 'short_name', 'phone', 'email']
    list_editable = ['is_active']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Основна інформація', {
            'fields': ('name', 'short_name', 'code_edrpou', 'is_active')
        }),
        ('Реквізити', {
            'fields': ('tax_number', 'vat_number')
        }),
        ('Контактна інформація', {
            'fields': ('legal_address', 'actual_address', 'phone', 'email', 'website')
        }),
        ('Банківські реквізити', {
            'fields': ('bank_name', 'bank_account', 'bank_mfo')
        }),
        ('Керівництво', {
            'fields': ('director', 'accountant')
        }),
        ('Додатково', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent', 'sort_order', 'is_active']
    list_filter = ['is_active', 'parent']
    search_fields = ['name', 'slug']
    list_editable = ['sort_order', 'is_active']
    prepopulated_fields = {'slug': ('name',)}


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    fields = ['service', 'product', 'name', 'quantity', 'unit', 'price', 'vat_rate']
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'service':
            kwargs['queryset'] = Service.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'invoice_date', 'legal_entity', 'total_amount', 'payment_status', 'due_date']
    list_filter = ['payment_status', 'invoice_date', 'due_date']
    search_fields = ['invoice_number', 'legal_entity__name', 'legal_entity__code_edrpou']
    list_editable = ['payment_status']
    readonly_fields = ['invoice_number', 'created_at', 'updated_at']  
    inlines = [InvoiceItemInline]
    
    fieldsets = (
        ('Інформація про документ', {
            'fields': ('invoice_number', 'legal_entity', 'due_date')  
        }),
        ('Реквізити продавця', {
            'fields': ('seller', 'seller_code', 'seller_address')
        }),
        ('Фінанси', {
            'fields': ('subtotal', 'vat_rate', 'vat_amount', 'total_amount')
        }),
        ('Оплата', {
            'fields': ('payment_status', 'paid_amount', 'payment_date', 'payment_method')
        }),
        ('Додатково', {
            'fields': ('order', 'notes', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user.username
        if not obj.invoice_date:
            obj.invoice_date = datetime.date.today()
        super().save_model(request, obj, form, change)