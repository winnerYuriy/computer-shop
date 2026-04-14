# shop/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.db.models import Q, Min, Max
from django.contrib import messages
from .models import Category, Product, Brand, Promotion, Review


def home(request):
    """Головна сторінка"""
    # Новинки: товари з активною акцією типу 'new'
    new_promo = Promotion.objects.filter(promotion_type='new', is_active=True).first()
    if new_promo:
        new_products = new_promo.products.filter(available=True)[:8]
    else:
        new_products = Product.objects.filter(available=True)[:8]

    # Хіти продажів: товари з акцією 'bestseller'
    best_promo = Promotion.objects.filter(promotion_type='bestseller', is_active=True).first()
    if best_promo:
        bestsellers = best_promo.products.filter(available=True)[:8]
    else:
        bestsellers = Product.objects.filter(available=True)[:8]

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
                Q(full_description__icontains=search_query)
            )

        # Фільтр за ціною
        price_min = self.request.GET.get('price_min', '')
        price_max = self.request.GET.get('price_max', '')
        if price_min:
            queryset = queryset.filter(price__gte=float(price_min))
        if price_max:
            queryset = queryset.filter(price__lte=float(price_max))

        # Фільтр за брендом
        brand_slug = self.request.GET.get('brand', '')
        if brand_slug:
            queryset = queryset.filter(brand__slug=brand_slug)

        # Сортування
        sort_by = self.request.GET.get('sort', '-created_at')
        if sort_by == 'price_asc':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_desc':
            queryset = queryset.order_by('-price')
        elif sort_by == 'rating':
            queryset = queryset.order_by('-rating')
        else:
            queryset = queryset.order_by('-created_at')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Всі кореневі категорії (для меню)
        context['categories'] = Category.objects.filter(level=0)

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

        # Діапазон цін
        price_range = Product.objects.filter(available=True).aggregate(
            min_price=Min('price'), max_price=Max('price')
        )
        context['min_price'] = int(price_range['min_price'] or 0)
        context['max_price'] = int(price_range['max_price'] or 10000)

        # Список брендів для фільтра
        context['brands'] = Brand.objects.all()

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

        return context


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
            messages.success(request, 'Дякуємо за відгук! Він буде опублікований після перевірки.')
        else:
            messages.error(request, 'Будь ласка, заповніть всі поля')

        return redirect('shop:product_detail', slug=product.slug)

    return redirect('shop:home')