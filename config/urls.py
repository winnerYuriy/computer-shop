# config/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from shop.admin_views import (
    export_products_page, import_products, export_products, pricelist_settings, 
    download_pricelist_file, service_calculator, generate_invoice_ajax, 
    download_invoice_pdf, invoice_list, download_missing_images, create_invoice_from_order
)
# НОВІ ІМПОРТИ ДЛЯ ВИПИСКИ РАХУНКІВ
from shop.views_invoice import get_product_price, invoice_form, create_invoice, print_invoice, search_products_api

urlpatterns = [
    # Кастомні адмін-URL мають бути перед admin.site.urls
    path('admin/import-products/', import_products, name='import_products'),
    path('admin/export-products/', export_products_page, name='admin_export_products_page'),
    path('admin/export-products/csv/', export_products, name='admin_export_products_csv'),
    path('admin/pricelist/', pricelist_settings, name='admin_pricelist_settings'),
    path('admin/pricelist/download/<str:filename>/', download_pricelist_file, name='admin_download_pricelist'), 
    
    # Калькулятор послуг
    path('admin/service-calculator/', service_calculator, name='admin_service_calculator'),
    path('admin/generate-invoice/', generate_invoice_ajax, name='admin_generate_invoice'),
    path('admin/download-invoice/<int:invoice_id>/', download_invoice_pdf, name='admin_download_invoice'),
    path('admin/invoices/', invoice_list, name='admin_invoice_list'),
    path('admin/shop/product/download-missing-images/', download_missing_images, name='admin_download_missing_images'),
    path('admin/order/<int:order_id>/create-invoice/', create_invoice_from_order, name='admin_create_invoice_from_order'),
    
    # НОВІ МАРШРУТИ ДЛЯ ВИПИСКИ РАХУНКІВ (стиль 1С)
    path('admin/invoice-form/', invoice_form, name='invoice_form'),
    path('admin/create-invoice/', create_invoice, name='create_invoice'),
    path('admin/print-invoice/<int:invoice_id>/', print_invoice, name='print_invoice'),

     # AJAX для пошуку товарів
    path('admin/search-products/', search_products_api, name='search_products_api'),
    path('admin/get-product-price/', get_product_price, name='get_product_price'),

    # Стандартна адмінка Django
    path('admin/', admin.site.urls),
    
    path('accounts/', include('accounts.urls')),
    path('', include('shop.urls')),
    path('cart/', include('cart.urls')),
    path('payment/', include('payment.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)