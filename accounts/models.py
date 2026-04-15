from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Розширена модель користувача"""
    phone = models.CharField('Телефон', max_length=20, blank=True)
    avatar = models.ImageField('Аватар', upload_to='avatars/', blank=True, null=True)
    address = models.TextField('Адреса', blank=True)
    city = models.CharField('Місто', max_length=100, blank=True)
    is_email_verified = models.BooleanField('Email підтверджено', default=False)
    email_verification_token = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField('Дата реєстрації', auto_now_add=True)
    updated_at = models.DateTimeField('Дата оновлення', auto_now=True)

    class Meta:
        verbose_name = 'Користувач'
        verbose_name_plural = 'Користувачі'
        ordering = ['-date_joined']

    def __str__(self):
        return self.email or self.username