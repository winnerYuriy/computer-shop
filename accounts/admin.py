from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User
from django.contrib.auth import get_user_model


User = get_user_model()

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['id', 'username', 'email', 'phone', 'avatar_preview', 'is_active', 'is_staff', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'date_joined']
    search_fields = ['username', 'email', 'phone']
    list_editable = ['is_active']
    readonly_fields = ['date_joined', 'last_login', 'avatar_preview']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Персональна інформація', {'fields': ('first_name', 'last_name', 'email', 'phone', 'avatar', 'avatar_preview', 'address', 'city')}),
        ('Статуси', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_email_verified')}),
        ('Важливі дати', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'phone', 'password1', 'password2'),
        }),
    )
    
    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 50%; object-fit: cover;" />', obj.avatar.url)
        return format_html('<i class="fas fa-user-circle fa-2x text-muted"></i>')
    avatar_preview.short_description = 'Аватар'