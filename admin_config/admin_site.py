# admin_config/admin_site.py

from django.contrib.admin import AdminSite
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model


class TechShopAdminSite(AdminSite):
    site_header = 'TechShop Адміністрування'
    site_title = 'TechShop Admin'
    index_title = 'Панель керування магазином'
    login_template = 'admin/login.html'
    
    def get_app_list(self, request):
        """
        Повертає список додатків для бокового меню
        """
        app_list = super().get_app_list(request)
        
        # Сортуємо додатки в потрібному порядку
        ordered_app_labels = ['shop', 'accounts', 'auth']
        ordered_app_list = []
        
        for label in ordered_app_labels:
            for app in app_list:
                if app['app_label'] == label:
                    ordered_app_list.append(app)
                    break
        
        # Додаємо решту додатків
        for app in app_list:
            if app not in ordered_app_list:
                ordered_app_list.append(app)
        
        return ordered_app_list
    
    def index(self, request, extra_context=None):
        from shop.models import Order, Product, Category, Invoice, LegalEntity, Service, Review
        from django.contrib.auth import get_user_model
        from django.db.models import Sum, Count, Avg
        from django.utils import timezone
        from datetime import timedelta
        
        User = get_user_model()
        
        # ============================================================
        # СТАТИСТИКА ЗАМОВЛЕНЬ
        # ============================================================
        total_orders = Order.objects.count()
        paid_orders = Order.objects.filter(status='paid').count()
        total_revenue = Order.objects.filter(status='paid').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        month_ago = timezone.now() - timedelta(days=30)
        orders_last_month = Order.objects.filter(created_at__gte=month_ago).count()
        orders_prev_month = Order.objects.filter(created_at__lt=month_ago).count()
        if orders_prev_month:
            orders_growth = round((orders_last_month - orders_prev_month) / orders_prev_month * 100, 1)
        else:
            orders_growth = 100 if orders_last_month else 0
        
        recent_orders = Order.objects.select_related('legal_entity').order_by('-created_at')[:10]
        order_status_counts = {
            'new': Order.objects.filter(status='new').count(),
            'processing': Order.objects.filter(status='processing').count(),
            'paid': Order.objects.filter(status='paid').count(),
            'shipped': Order.objects.filter(status='shipped').count(),
            'delivered': Order.objects.filter(status='delivered').count(),
            'cancelled': Order.objects.filter(status='cancelled').count(),
        }
        
        # ============================================================
        # СТАТИСТИКА ТОВАРІВ
        # ============================================================
        total_products = Product.objects.filter(available=True).count()
        total_products_all = Product.objects.count()
        low_stock = Product.objects.filter(quantity__lt=5, available=True).count()
        no_image = Product.objects.filter(main_image='').count()
        top_rated = Product.objects.filter(available=True, rating__gt=0).order_by('-rating')[:5]
        
        # ============================================================
        # СТАТИСТИКА РАХУНКІВ
        # ============================================================
        total_invoices = Invoice.objects.count()
        unpaid_invoices = Invoice.objects.filter(payment_status='unpaid').count()
        paid_invoices = Invoice.objects.filter(payment_status='paid').count()
        recent_invoices = Invoice.objects.select_related('legal_entity').order_by('-invoice_date')[:5]
        
        # ============================================================
        # СТАТИСТИКА КАТЕГОРІЙ ТА ЮРОСІБ
        # ============================================================
        total_categories = Category.objects.count()
        total_legal_entities = LegalEntity.objects.filter(is_active=True).count()
        total_services = Service.objects.filter(is_active=True).count()
        
        # ============================================================
        # СТАТИСТИКА КОРИСТУВАЧІВ ТА ВІДГУКІВ
        # ============================================================
        total_customers = User.objects.count()
        total_reviews = Review.objects.filter(is_approved=True).count()
        pending_reviews = Review.objects.filter(is_approved=False).count()
        avg_rating = Review.objects.filter(is_approved=True).aggregate(Avg('rating'))['rating__avg'] or 0
        
        # Форматуємо дохід
        formatted_revenue = f"{int(total_revenue):,}".replace(",", " ")
        
        # ============================================================
        # ФОРМУЄМО КОНТЕКСТ
        # ============================================================
        extra_context = extra_context or {}
        extra_context.update({
            'total_orders': total_orders,
            'paid_orders': paid_orders,
            'total_revenue': total_revenue,
            'total_revenue_formatted': formatted_revenue,
            'orders_growth': orders_growth,
            'recent_orders': recent_orders,
            'order_status_counts': order_status_counts,
            'total_products': total_products,
            'total_products_all': total_products_all,
            'low_stock': low_stock,
            'no_image': no_image,
            'top_rated': top_rated,
            'total_invoices': total_invoices,
            'unpaid_invoices': unpaid_invoices,
            'paid_invoices': paid_invoices,
            'recent_invoices': recent_invoices,
            'total_categories': total_categories,
            'total_legal_entities': total_legal_entities,
            'total_services': total_services,
            'total_customers': total_customers,
            'total_reviews': total_reviews,
            'pending_reviews': pending_reviews,
            'avg_rating': round(avg_rating, 1),
        })
        
        return super().index(request, extra_context)


# Створюємо екземпляр
admin_site = TechShopAdminSite(name='myadmin')


# ============================================================
# РЕЄСТРАЦІЯ ВСІХ МОДЕЛЕЙ
# ============================================================

from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin

# Імпортуємо адмін-класи з shop.admin
from shop.admin import (
    ProductAdmin, CategoryAdmin, BrandAdmin, OrderAdmin, 
    ReviewAdmin, LegalEntityAdmin, PropertyAdmin, PropertyValueAdmin,
    CartAdmin, InvoiceAdmin
)

# Імпортуємо сервісні адміни (якщо вони є)
try:
    from shop.admin import ServiceAdmin, ServiceCategoryAdmin
    service_admin_available = True
except ImportError:
    service_admin_available = False

from shop.models import (
    Product, Category, Brand, Order, Invoice, 
    Review, LegalEntity, Property, PropertyValue, Service, ServiceCategory, Cart
)

# Реєстрація стандартних моделей Django
admin_site.register(User, UserAdmin)
admin_site.register(Group, GroupAdmin)

# Реєстрація моделей shop
admin_site.register(Product, ProductAdmin)
admin_site.register(Category, CategoryAdmin)
admin_site.register(Brand, BrandAdmin)
admin_site.register(Order, OrderAdmin)
admin_site.register(Review, ReviewAdmin)
admin_site.register(LegalEntity, LegalEntityAdmin)
admin_site.register(Property, PropertyAdmin)
admin_site.register(PropertyValue, PropertyValueAdmin)
admin_site.register(Cart, CartAdmin)
admin_site.register(Invoice, InvoiceAdmin)

# Реєстрація сервісних моделей (якщо вони є)
if service_admin_available:
    admin_site.register(Service, ServiceAdmin)
    admin_site.register(ServiceCategory, ServiceCategoryAdmin)