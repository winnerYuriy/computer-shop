# shop/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.db.models import Q, Min, Max, Count
from django.contrib import messages
from decimal import Decimal
from .models import Category, Order, Product, Brand, Promotion, Review, RecentlyViewed


def home(request):
    """Головна сторінка"""
    # Новинки: товари з активною акцією типу 'new'
    new_promo = Promotion.objects.filter(promotion_type='new', is_active=True).first()
    if new_promo:
        new_products = new_promo.products.filter(available=True)[:8]
    else:
        new_products = Product.objects.filter(available=True).order_by('-created_at')[:8]

    # Хіти продажів: товари з акцією 'bestseller'
    best_promo = Promotion.objects.filter(promotion_type='bestseller', is_active=True).first()
    if best_promo:
        bestsellers = best_promo.products.filter(available=True)[:8]
    else:
        bestsellers = Product.objects.filter(available=True).order_by('-rating')[:8]

    context = {
        'new_products': new_products,
        'bestsellers': bestsellers,
    }
    return render(request, 'shop/index.html', context)


class CatalogView(ListView):
    """Каталог товарів з фільтрами, пошуком та сортуванням"""
    model = Product
    template_name = 'shop/catalog.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.filter(available=True)

        # Фільтр за категорією (MPTT)
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            # Отримуємо всі підкатегорії включаючи поточну
            descendant_categories = category.get_descendants(include_self=True)
            queryset = queryset.filter(category__in=descendant_categories)

        # Пошук
        search_query = self.request.GET.get('q', '')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(full_description__icontains=search_query) |
                Q(article__icontains=search_query) |
                Q(code__icontains=search_query)
            )

        # Фільтр за ціною
        price_min = self.request.GET.get('price_min', '')
        price_max = self.request.GET.get('price_max', '')
        if price_min:
            try:
                queryset = queryset.filter(price__gte=Decimal(str(price_min).replace(',', '.')))
            except:
                pass
        if price_max:
            try:
                queryset = queryset.filter(price__lte=Decimal(str(price_max).replace(',', '.')))
            except:
                pass

        # Фільтр за брендом
        brand_slug = self.request.GET.get('brand', '')
        if brand_slug:
            queryset = queryset.filter(brand__slug=brand_slug)

        # Фільтр за наявністю
        in_stock = self.request.GET.get('in_stock', '')
        if in_stock == 'yes':
            queryset = queryset.filter(quantity__gt=0)

        # Сортування
        sort_by = self.request.GET.get('sort', '-created_at')
        if sort_by == 'price_asc':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_desc':
            queryset = queryset.order_by('-price')
        elif sort_by == 'rating':
            queryset = queryset.order_by('-rating')
        elif sort_by == 'title_asc':
            queryset = queryset.order_by('title')
        elif sort_by == 'title_desc':
            queryset = queryset.order_by('-title')
        else:
            queryset = queryset.order_by('-created_at')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Всі кореневі категорії (для меню)
        context['categories'] = Category.objects.filter(parent=None)

        # Поточна категорія
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            context['current_category'] = get_object_or_404(Category, slug=category_slug)

        # Значення для фільтрів
        context['search_query'] = self.request.GET.get('q', '')
        context['price_min'] = self.request.GET.get('price_min', '')
        context['price_max'] = self.request.GET.get('price_max', '')
        context['selected_brand'] = self.request.GET.get('brand', '')
        context['current_sort'] = self.request.GET.get('sort', '-created_at')
        context['in_stock_filter'] = self.request.GET.get('in_stock', '')

        # Діапазон цін (тільки для доступних товарів)
        price_range = Product.objects.filter(available=True).aggregate(
            min_price=Min('price'), max_price=Max('price')
        )
        context['min_price'] = int(price_range['min_price'] or 0)
        context['max_price'] = int(price_range['max_price'] or 100000)

        # Список брендів для фільтра
        context['brands'] = Brand.objects.filter(
            products__available=True
        ).distinct().annotate(product_count=Count('products'))

        # Кількість знайдених товарів
        context['total_products'] = self.get_queryset().count()

        return context


class ProductDetailView(DetailView):
    """Детальна сторінка товару"""
    model = Product
    template_name = 'shop/product_detail.html'
    context_object_name = 'product'

    def get_object(self, queryset=None):
        slug = self.kwargs.get('slug')
        return get_object_or_404(Product, slug=slug, available=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Схожі товари (з тієї ж категорії)
        context['related_products'] = Product.objects.filter(
            category=self.object.category,
            available=True
        ).exclude(id=self.object.id)[:4]

        # Відгуки (тільки опубліковані)
        context['reviews'] = self.object.reviews.filter(is_approved=True)

        # Отримуємо середній рейтинг
        if context['reviews'].exists():
            from django.db.models import Avg
            avg_rating = context['reviews'].aggregate(Avg('rating'))['rating__avg']
            context['avg_rating'] = round(avg_rating, 1)
        else:
            context['avg_rating'] = 0

        return context

    def get(self, request, *args, **kwargs):
        # Отримуємо товар
        self.object = self.get_object()
        
        # Додаємо до історії переглядів
        add_to_recently_viewed(request, self.object)
        
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)


def add_review(request, product_id):
    """Додавання відгуку"""
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)

        user_name = request.POST.get('user_name')
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        if user_name and rating and comment:
            Review.objects.create(
                product=product,
                user_name=user_name,
                rating=int(rating),
                comment=comment,
                is_approved=False
            )
            # Оновлюємо рейтинг товару
            product.update_rating()
            messages.success(request, 'Дякуємо за відгук! Він буде опублікований після перевірки.')
        else:
            messages.error(request, 'Будь ласка, заповніть всі поля')

        return redirect('shop:product_detail', slug=product.slug)

    return redirect('shop:home')


# ===================================================================
# Функції для історії переглядів
# ===================================================================

def add_to_recently_viewed(request, product):
    """Додає товар до історії переглядів"""
    if not request.session.session_key:
        request.session.create()
    
    session_key = request.session.session_key
    
    # Видаляємо старий запис, якщо він є
    RecentlyViewed.objects.filter(session_key=session_key, product=product).delete()
    
    # Додаємо новий запис
    RecentlyViewed.objects.create(session_key=session_key, product=product)
    
    # Залишаємо тільки останні 10 товарів
    recent_count = RecentlyViewed.objects.filter(session_key=session_key).count()
    if recent_count > 10:
        oldest = RecentlyViewed.objects.filter(session_key=session_key).order_by('viewed_at').first()
        if oldest:
            oldest.delete()


def get_recently_viewed(request, limit=8):
    """Отримує список нещодавно переглянутих товарів"""
    if not request.session.session_key:
        return []
    
    recent_items = RecentlyViewed.objects.filter(
        session_key=request.session.session_key
    ).select_related('product')[:limit]
    
    return [item.product for item in recent_items if item.product.available]


def order_detail(request, order_id):
    """Детальна сторінка замовлення"""
    order = get_object_or_404(Order, id=order_id)
    
    # Перевіряємо, що замовлення належить поточному користувачу
    if request.user.is_authenticated and order.email != request.user.email:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Ви не маєте доступу до цього замовлення")
    
    context = {
        'order': order,
    }
    return render(request, 'shop/order_detail.html', context)