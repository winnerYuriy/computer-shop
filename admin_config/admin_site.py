# admin_config/admin_site.py

from django.contrib.admin import AdminSite
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

User = get_user_model()

# Правильний імпорт моделей - Order з shop.models
from shop.models import Order, Product, Category


class TechShopAdminSite(AdminSite):
    site_header = 'TechShop Адміністрування'
    site_title = 'TechShop Admin'
    index_title = 'Панель керування магазином'

    def index(self, request, extra_context=None):
        # Статистика для замовлень
        total_orders = Order.objects.count()
        total_revenue = Order.objects.filter(is_paid=True).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        # Розрахунок зростання замовлень за місяць
        month_ago = timezone.now() - timedelta(days=30)
        orders_last_month = Order.objects.filter(created_at__gte=month_ago).count()
        orders_prev_month = Order.objects.filter(created_at__lt=month_ago).count()
        if orders_prev_month:
            orders_growth = round((orders_last_month - orders_prev_month) / orders_prev_month * 100, 1)
        else:
            orders_growth = 100 if orders_last_month else 0
        
        recent_orders = Order.objects.order_by('-created_at')[:5]
        
        # Статистика для товарів
        total_products = Product.objects.filter(available=True).count()
        total_products_all = Product.objects.count()
        low_stock = Product.objects.filter(quantity__lt=5, available=True).count()
        no_image = Product.objects.filter(main_image='').count()
        
        # Статистика для категорій
        total_categories = Category.objects.count()
        
        # Статистика для користувачів
        total_customers = User.objects.count()
        
        # Статистика для відгуків (якщо є модель Review)
        try:
            from shop.models import Review
            total_reviews = Review.objects.filter(is_approved=True).count()
            avg_rating = Review.objects.filter(is_approved=True).aggregate(Avg('rating'))['rating__avg'] or 0
        except ImportError:
            total_reviews = 0
            avg_rating = 0
        
        extra_context = extra_context or {}
        extra_context.update({
            'total_orders': total_orders,
            'total_revenue': int(total_revenue),
            'total_customers': total_customers,
            'total_products': total_products,
            'total_products_all': total_products_all,
            'total_categories': total_categories,
            'total_reviews': total_reviews,
            'avg_rating': round(avg_rating, 1),
            'recent_orders': recent_orders,
            'orders_growth': orders_growth,
            'low_stock': low_stock,
            'no_image': no_image,
        })
        
        return super().index(request, extra_context)