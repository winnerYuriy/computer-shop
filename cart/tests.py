from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from shop.models import Category, Order, Product
from .cart import Cart


class CartCheckoutTests(TestCase):
	def setUp(self):
		category = Category.objects.create(name='Ноутбуки', slug='laptops')
		self.product = Product.objects.create(
			name='Тестовий ноутбук',
			slug='test-laptop',
			category=category,
			description='Тестовий товар',
			price=Decimal('150.00'),
			sale_price=Decimal('100.00'),
			stock=5,
		)
		self.checkout_data = {
			'full_name': 'Тест Покупець',
			'phone': '+380501234567',
			'email': 'buyer@example.com',
			'delivery_method': 'nova_post',
			'city': 'Київ',
			'nova_post_office': '1',
		}

	def put_items_in_session(self, items):
		session = self.client.session
		session['cart'] = items
		session.save()

	def test_cart_uses_current_product_price_instead_of_session_price(self):
		self.put_items_in_session({
			str(self.product.id): {'quantity': 2, 'price': '1.00'},
		})

		response = self.client.post(reverse('cart:checkout'), self.checkout_data)

		order = Order.objects.get()
		self.assertEqual(order.total_amount, Decimal('200.00'))
		self.assertEqual(order.products[0]['price'], '100.00')
		self.assertEqual(response.status_code, 302)

	def test_checkout_rejects_quantity_above_stock(self):
		self.put_items_in_session({
			str(self.product.id): {'quantity': 6, 'price': '100.00'},
		})

		response = self.client.post(reverse('cart:checkout'), self.checkout_data)

		self.assertEqual(response.status_code, 200)
		self.assertFalse(Order.objects.exists())
		self.assertEqual(Cart(self.client.get('/cart/').wsgi_request).get_quantities()[str(self.product.id)], 6)

	def test_checkout_rejects_inactive_product(self):
		self.product.is_active = False
		self.product.save(update_fields=['is_active'])
		self.put_items_in_session({
			str(self.product.id): {'quantity': 1, 'price': '100.00'},
		})

		response = self.client.post(reverse('cart:checkout'), self.checkout_data)

		self.assertEqual(response.status_code, 200)
		self.assertFalse(Order.objects.exists())

	def test_cart_add_rejects_quantity_above_stock(self):
		request = self.client.get('/cart/').wsgi_request
		cart = Cart(request)

		with self.assertRaises(ValueError):
			cart.add(self.product, quantity=6)

	def test_sale_price_is_the_current_price(self):
		self.assertEqual(self.product.final_price, Decimal('100.00'))
		self.assertEqual(self.product.discount_percent, 33)
