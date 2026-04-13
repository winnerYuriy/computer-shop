from django.urls import path
from . import views

app_name = 'payment'

urlpatterns = [
    path('process/<int:order_id>/', views.payment_process, name='process'),
    path('callback/', views.payment_callback, name='callback'),
    path('complete/', views.payment_complete, name='complete'),
    path('cancel/', views.payment_cancel, name='cancel'),
]