# admin_config/urls.py

from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'admin_config'

urlpatterns = [
    path('import-products/', views.import_products_view, name='import_products'),
    path('export-products/', views.export_products_view, name='export_products'),
    path('export-template/', views.export_template_view, name='export_template'),
]
