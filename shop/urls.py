from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.home, name='home'),
    path('catalog/', views.CatalogView.as_view(), name='catalog'),
    path('catalog/<path:category_slug>/', views.CatalogView.as_view(), name='category_detail'),
    path('product/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),  
    path('product/<int:product_id>/review/', views.add_review, name='add_review'),
]