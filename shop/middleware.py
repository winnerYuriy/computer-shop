from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from .models import Order, Product

User = get_user_model()  # Отримуємо правильну модель користувача


class AdminStatsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_template_response(self, request, response):
        if request.path.startswith('/admin/') and hasattr(response, 'context_data'):
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
            low_stock = Product.objects.filter(quantity__lt=5, available=True).count()
            
            # Статистика для категорій
            from .models import Category
            total_categories = Category.objects.count()
            
            # Статистика для користувачів (використовуємо get_user_model)
            total_customers = User.objects.count()
            
            response.context_data.update({
                'total_orders': total_orders,
                'total_revenue': int(total_revenue),
                'total_customers': total_customers,
                'total_products': total_products,
                'total_categories': total_categories,
                'recent_orders': recent_orders,
                'orders_growth': orders_growth,
                'low_stock': low_stock,
            })
        
        return response