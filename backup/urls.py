# backup/urls.py

from django.urls import path
from . import views

app_name = 'backup'

urlpatterns = [
    path('', views.backup_list, name='list'),
    path('create/', views.create_backup, name='create'),
    path('download/<str:filename>/', views.download_backup, name='download'),
    path('restore/<str:filename>/', views.restore_backup, name='restore'),
    path('delete/<str:filename>/', views.delete_backup, name='delete'),
    path('info/', views.backup_info, name='info'),
]