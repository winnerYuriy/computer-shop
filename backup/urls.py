from django.urls import path
from . import views

app_name = 'backup'

urlpatterns = [
    path('', views.backup_dashboard, name='dashboard'),
    path('create/', views.create_backup, name='create'),
    path('restore/<str:backup_name>/', views.restore_backup, name='restore'),
    path('download/<str:backup_name>/', views.download_backup, name='download'),
    path('delete/<str:backup_name>/', views.delete_backup, name='delete'),
    path('info/', views.backup_info, name='info'),
]