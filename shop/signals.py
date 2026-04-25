from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils.text import slugify
from .models import Category, Order, AdminNotification, Review, Product
from django.urls import reverse


@receiver(pre_save, sender=Category)
def generate_category_slug(sender, instance, **kwargs):
    """Автоматично генерує slug для категорії, якщо він порожній"""
    if not instance.slug or instance.slug == '':
        instance.slug = slugify(instance.name)


@receiver(post_save, sender=Order)
def create_order_notification(sender, instance, created, **kwargs):
    """Створює сповіщення при новому замовленні"""
    if created:
        AdminNotification.objects.create(
            notification_type='new_order',
            title=f'Нове замовлення #{instance.id}',
            message=f'Клієнт {instance.full_name} зробив замовлення на суму {instance.total_amount}₴',
            link=reverse('admin:shop_order_change', args=[instance.id])
        )


@receiver(post_save, sender=Review)
def create_review_notification(sender, instance, created, **kwargs):
    """Створює сповіщення при новому відгуку"""
    if created and not instance.is_approved:
        AdminNotification.objects.create(
            notification_type='new_review',
            title=f'Новий відгук на товар "{instance.product.title}"',
            message=f'Користувач {instance.user_name} залишив відгук з оцінкою {instance.rating}★',
            link=reverse('admin:shop_review_change', args=[instance.id])
        )


@receiver(post_save, sender=Product)
def create_low_stock_notification(sender, instance, **kwargs):
    """Створює сповіщення при низькому залишку товару"""
    if instance.quantity <= 5 and instance.available:
        # Перевіряємо, чи вже є таке сповіщення за останню годину
        from django.utils import timezone
        from datetime import timedelta
        
        hour_ago = timezone.now() - timedelta(hours=1)
        exists = AdminNotification.objects.filter(
            notification_type='low_stock',
            title__icontains=instance.title,
            created_at__gte=hour_ago
        ).exists()
        
        if not exists:
            AdminNotification.objects.create(
                notification_type='low_stock',
                title=f'Товар закінчується: {instance.title}',
                message=f'Залишилось всього {instance.quantity} шт. на складі',
                link=reverse('admin:shop_product_change', args=[instance.id])
            )