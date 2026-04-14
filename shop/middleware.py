# shop/middleware.py

from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta

class AdminStatsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_template_response(self, request, response):
        if request.path.startswith('/admin/') and hasattr(response, 'context_data'):
            from .models import Order, Product
            from django.contrib.auth.models import User

            total_orders = Order.objects.count()
            total_revenue = Order.objects.filter(is_paid=True).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            total_customers = User.objects.count()
            total_products = Product.objects.filter(available=True).count()
            recent_orders = Order.objects.order_by('-created_at')[:5]

            month_ago = timezone.now() - timedelta(days=30)
            orders_last_month = Order.objects.filter(created_at__gte=month_ago).count()
            orders_prev_month = Order.objects.filter(created_at__lt=month_ago).count()
            orders_growth = round((orders_last_month - orders_prev_month) / orders_prev_month * 100, 1) if orders_prev_month else 0

            response.context_data.update({
                'total_orders': total_orders,
                'total_revenue': int(total_revenue),
                'total_customers': total_customers,
                'total_products': total_products,
                'recent_orders': recent_orders,
                'orders_growth': orders_growth,
            })
        return response