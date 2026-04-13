from django.db import models
from django.shortcuts import redirect, render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.db.models import Q, Min, Max
from django.core.paginator import Paginator
from .models import Category, Product, Review
from django.contrib import messages 

def home(request):
    """Головна сторінка"""
    new_products = Product.objects.filter(is_active=True, is_new=True)[:8]
    bestsellers = Product.objects.filter(is_active=True, is_bestseller=True)[:8]
    
    context = {
        'new_products': new_products,
        'bestsellers': bestsellers,
    }
    return render(request, 'shop/index.html', context)


class CatalogView(ListView):
    """Каталог товарів з фільтрами та пошуком"""
    model = Product
    template_name = 'shop/catalog.html'
    context_object_name = 'products'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True)
        
        # Фільтр за категорією
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            category = get_object_or_404(Category, full_slug=category_slug)
            queryset = category.get_all_products()
        
        # Пошук
        search_query = self.request.GET.get('q', '')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Фільтр за ціною
        price_min = self.request.GET.get('price_min', '')
        price_max = self.request.GET.get('price_max', '')
        if price_min:
            queryset = queryset.filter(price__gte=float(price_min))
        if price_max:
            queryset = queryset.filter(price__lte=float(price_max))
        
        # Фільтр за брендом (атрибут)
        brand = self.request.GET.get('brand', '')
        if brand:
            queryset = queryset.filter(
                attribute_values__attribute__slug='brand',
                attribute_values__value_text=brand
            )
        
        # Фільтр за RAM (числовий атрибут)
        ram = self.request.GET.get('ram', '')
        if ram:
            queryset = queryset.filter(
                attribute_values__attribute__slug='ram',
                attribute_values__value_number=int(ram)
            )
        
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
        
        # Категорії для сайдбару
        context['categories'] = Category.objects.filter(parent__isnull=True)
        
        # Поточна категорія
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            context['current_category'] = get_object_or_404(Category, full_slug=category_slug)
        
        # Значення для фільтрів
        context['search_query'] = self.request.GET.get('q', '')
        context['price_min'] = self.request.GET.get('price_min', '')
        context['price_max'] = self.request.GET.get('price_max', '')
        context['selected_brand'] = self.request.GET.get('brand', '')
        context['selected_ram'] = self.request.GET.get('ram', '')
        context['current_sort'] = self.request.GET.get('sort', '-created_at')
        
        # Діапазон цін для фільтра
        price_range = Product.objects.filter(is_active=True).aggregate(
            min_price=Min('price'), max_price=Max('price')
        )
        context['min_price'] = int(price_range['min_price'] or 0)
        context['max_price'] = int(price_range['max_price'] or 10000)
        
        # Список брендів для фільтра
        brands = Product.objects.filter(
            is_active=True,
            attribute_values__attribute__slug='brand'
        ).values_list('attribute_values__value_text', flat=True).distinct()
        context['brands'] = [b for b in brands if b]
        
        # Список RAM для фільтра
        rams = Product.objects.filter(
            is_active=True,
            attribute_values__attribute__slug='ram'
        ).values_list('attribute_values__value_number', flat=True).distinct()
        context['rams'] = sorted([int(r) for r in rams if r])
        
        return context


class ProductDetailView(DetailView):
    """Детальна сторінка товару з відгуками"""
    model = Product
    template_name = 'shop/product_detail.html'
    context_object_name = 'product'
    
    def get_object(self, queryset=None):
        slug = self.kwargs.get('slug')
        return get_object_or_404(Product, slug=slug, is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Схожі товари
        context['related_products'] = Product.objects.filter(
            category=self.object.category,
            is_active=True
        ).exclude(id=self.object.id)[:4]
        
        # Відгуки
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
            review = Review.objects.create(
                product=product,
                user_name=user_name,
                rating=int(rating),
                comment=comment,
                is_approved=False  # Потребує модерації
            )
            
            # Оновлюємо середній рейтинг товару
            approved_reviews = product.reviews.filter(is_approved=True)
            if approved_reviews.exists():
                avg_rating = approved_reviews.aggregate(models.Avg('rating'))['rating__avg']
                product.rating = round(avg_rating, 2)
                product.reviews_count = approved_reviews.count()
            else:
                product.rating = review.rating
                product.reviews_count = 1
            product.save()
            
            messages.success(request, 'Дякуємо за відгук! Він буде опублікований після перевірки.')
        else:
            messages.error(request, 'Будь ласка, заповніть всі поля')
        
        return redirect('shop:product_detail', slug=product.slug)