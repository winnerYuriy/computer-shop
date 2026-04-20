# config/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from shop.admin_views import import_products, export_products, export_template

urlpatterns = [
    # Кастомні адмін-URL мають бути перед admin.site.urls
    path('admin/import-products/', import_products, name='import_products'),
    path('admin/export-products/', export_products, name='export_products'),
    path('admin/export-template/', export_template, name='export_template'),
    
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