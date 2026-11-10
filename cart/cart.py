# cart/cart.py

from decimal import Decimal
from django.conf import settings
from shop.models import Product


class Cart:
    """Клас для роботи з кошиком у сесії"""
    
    def __init__(self, request):
        """Ініціалізація кошика"""
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart
    
    def add(self, product, quantity=1, override_quantity=False):
        """Додати товар до кошика або оновити кількість"""
        quantity = int(quantity)
        if quantity <= 0:
            raise ValueError('Кількість має бути більшою за нуль.')
        if not product.is_available:
            raise ValueError('Товар більше недоступний.')

        product_id = str(product.id)
        current_quantity = self.get_quantities().get(product_id, 0)
        requested_quantity = quantity if override_quantity else current_quantity + quantity
        if requested_quantity > product.quantity:
            raise ValueError(f'Доступно лише {product.quantity} шт. товару.')

        self.cart[product_id] = {'quantity': requested_quantity}
        
        self.save()

    def get_quantities(self):
        """Повертає лише коректні ідентифікатори й додатні кількості із сесії."""
        quantities = {}
        for product_id, item in self.cart.items():
            try:
                normalized_id = str(int(product_id))
                quantity = int(item['quantity'])
            except (TypeError, ValueError, KeyError):
                continue
            if int(normalized_id) > 0 and quantity > 0:
                quantities[normalized_id] = quantity
        return quantities
    
    def save(self):
        """Зберігає кошик у сесію"""
        self.session[settings.CART_SESSION_ID] = self.cart
        self.session.modified = True
    
    def remove(self, product):
        """Видалити товар з кошика"""
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()
    
    def __iter__(self):
        """Перебирає товари в кошику"""
        quantities = self.get_quantities()
        products = Product.objects.filter(id__in=quantities).order_by('id')

        for product in products:
            quantity = quantities[str(product.id)]
            price = product.final_price
            yield {
                'product': product,
                'quantity': quantity,
                'price': price,
                'total_price': price * quantity,
                'available': product.is_available and quantity <= product.quantity,
            }
    
    def __len__(self):
        """Повертає загальну кількість товарів у кошику"""
        return sum(self.get_quantities().values())
    
    def get_total_price(self):
        """Повертає загальну суму кошика"""
        return sum((item['total_price'] for item in self), Decimal('0.00'))
    
    def clear(self):
        """Очищає кошик"""
        self.session.pop(settings.CART_SESSION_ID, None)
        self.session.modified = True