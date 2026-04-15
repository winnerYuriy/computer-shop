from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify
from .models import Category


@receiver(pre_save, sender=Category)
def generate_category_slug(sender, instance, **kwargs):
    """Автоматично генерує slug для категорії, якщо він порожній"""
    if not instance.slug or instance.slug == '':
        instance.slug = slugify(instance.name)