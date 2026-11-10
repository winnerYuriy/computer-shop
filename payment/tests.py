import base64
import json
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from shop.models import Brand, Category, Order, Product
from .views import generate_liqpay_signature


@override_settings(
	LIQPAY_PUBLIC_KEY='public-test-key',
	LIQPAY_PRIVATE_KEY='private-test-key',
	LIQPAY_SANDBOX=True,
	LIQPAY_SERVER_URL='',
)
class LiqPayTests(TestCase):
	def setUp(self):
		category = Category.objects.create(name='Ноутбуки', slug='laptops')
		brand = Brand.objects.create(name='Тест', slug='test')
		self.product = Product.objects.create(
			title='Тестовий ноутбук',
			slug='test-laptop-payment',
			category=category,
			brand=brand,
			description='Тестовий товар',
			price=Decimal('100.00'),
			quantity=3,
		)
		self.order = Order.objects.create(
			full_name='Тест Покупець',
			phone='+380501234567',
			email='buyer@example.com',
			products=[{
				'id': self.product.id,
				'name': self.product.title,
				'price': '100.00',
				'quantity': 1,
			}],
			total_amount=Decimal('100.00'),
		)

	def make_callback(self, **overrides):
		payload = {
			'public_key': 'public-test-key',
			'action': 'pay',
			'amount': '100.00',
			'currency': 'UAH',
			'order_id': str(self.order.id),
			'status': 'sandbox',
			'payment_id': 'payment-test-id',
		}
		payload.update(overrides)
		encoded_data = base64.b64encode(json.dumps(payload).encode()).decode()
		signature = generate_liqpay_signature(encoded_data, 'private-test-key')
		return self.client.post(
			reverse('payment:callback'),
			{'data': encoded_data, 'signature': signature},
		)

	def test_checkout_form_requests_sandbox_payment(self):
		response = self.client.get(reverse('payment:process', args=[self.order.id]))

		payload = json.loads(base64.b64decode(response.context['liqpay_data']))
		self.assertEqual(payload['sandbox'], 1)
		self.assertEqual(payload['server_url'], 'http://testserver/payment/callback/')
		self.assertEqual(response.status_code, 200)

	def test_browser_return_does_not_mark_order_paid(self):
		response = self.client.get(
			reverse('payment:result'),
			{'order_id': self.order.id, 'status': 'success'},
		)

		self.order.refresh_from_db()
		self.assertEqual(response.status_code, 200)
		self.assertFalse(self.order.is_paid)

	def test_signed_sandbox_callback_marks_order_paid_once(self):
		first_response = self.make_callback()
		second_response = self.make_callback()

		self.order.refresh_from_db()
		self.product.refresh_from_db()
		self.assertEqual(first_response.status_code, 200)
		self.assertEqual(second_response.status_code, 200)
		self.assertTrue(self.order.is_paid)
		self.assertEqual(self.product.quantity, 2)

	def test_callback_rejects_amount_mismatch(self):
		response = self.make_callback(amount='99.00')

		self.order.refresh_from_db()
		self.assertEqual(response.status_code, 400)
		self.assertFalse(self.order.is_paid)
