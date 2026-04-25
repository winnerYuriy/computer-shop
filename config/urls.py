# config/urls.py
from admin_config.admin_site import admin_site  # Імпортуємо кастомний admin_site
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
# from django.contrib import admin
from shop.admin_views import (create_invoice_from_order, download_invoice_pdf, download_missing_images, 
                              download_pricelist_file, export_products, export_products_page, generate_invoice_ajax, 
                              import_products, invoice_list, pricelist_settings, service_calculator,get_notifications, 
                              mark_notification_read, mark_all_notifications_read
                            )  
from shop.views_invoice import create_invoice, invoice_form, print_invoice, search_products_api


urlpatterns = [
    # Кастомні адмін-URL
    path('admin/import-products/', import_products, name='import_products'),
    path('admin/export-products/', export_products_page, name='admin_export_products_page'),
    path('admin/export-products/csv/', export_products, name='admin_export_products_csv'),
    path('admin/pricelist/', pricelist_settings, name='admin_pricelist_settings'),
    path('admin/pricelist/download/<str:filename>/', download_pricelist_file, name='admin_download_pricelist'),
    path('admin/service-calculator/', service_calculator, name='admin_service_calculator'),
    path('admin/generate-invoice/', generate_invoice_ajax, name='admin_generate_invoice'),
    path('admin/download-invoice/<int:invoice_id>/', download_invoice_pdf, name='admin_download_invoice'),
    path('admin/invoices/', invoice_list, name='admin_invoice_list'),
    path('admin/invoice-form/', invoice_form, name='invoice_form'),
    path('admin/create-invoice/', create_invoice, name='create_invoice'),
    path('admin/print-invoice/<int:invoice_id>/', print_invoice, name='print_invoice'),
    path('admin/shop/product/download-missing-images/', download_missing_images, name='admin_download_missing_images'),
    path('admin/order/<int:order_id>/create-invoice/', create_invoice_from_order, name='admin_create_invoice_from_order'),
    path('admin/search-products/', search_products_api, name='search_products_api'),
    path('admin/api/notifications/', get_notifications, name='admin_notifications'),
    path('admin/api/notifications/mark/<int:notification_id>/', mark_notification_read, name='admin_mark_notification'),
    path('admin/api/notifications/mark-all/', mark_all_notifications_read, name='admin_mark_all_notifications'),
    path('admin/backup/', include('backup.urls')),    
  
    path('admin/', admin_site.urls),
    
    path('accounts/', include('accounts.urls')),
    path('', include('shop.urls')),
    path('cart/', include('cart.urls')),
    path('payment/', include('payment.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)