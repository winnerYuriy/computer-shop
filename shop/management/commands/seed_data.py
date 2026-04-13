# shop/management/commands/seed_data.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from shop.models import Category, Attribute, AttributeValue, Product, ProductAttributeValue


class Command(BaseCommand):
    help = 'Наповнює базу даних тестовими даними для інтернет-магазину'

    def get_or_create_attribute_value(self, attribute, **kwargs):
        """Безпечне створення значення атрибута з урахуванням типу"""
        try:
            # Спроба знайти існуюче значення
            if attribute.type == 'number':
                obj, created = AttributeValue.objects.get_or_create(
                    attribute=attribute,
                    value_number=kwargs.get('value_number'),
                    defaults=kwargs
                )
            elif attribute.type == 'boolean':
                obj, created = AttributeValue.objects.get_or_create(
                    attribute=attribute,
                    value_boolean=kwargs.get('value_boolean'),
                    defaults=kwargs
                )
            else:  # text, color
                obj, created = AttributeValue.objects.get_or_create(
                    attribute=attribute,
                    value_text=kwargs.get('value_text'),
                    defaults=kwargs
                )
            return obj, created
        except Exception as e:
            self.stdout.write(f'   ! Помилка при створенні {attribute.name}: {e}')
            return None, False

    def handle(self, *args, **options):
        self.stdout.write('Починаємо наповнення бази даних...')
        
        # === 1. СТВОРЮЄМО КАТЕГОРІЇ ===
        self.stdout.write('1. Створюємо категорії...')
        
        # Кореневі категорії
        notebooks_root, _ = Category.objects.get_or_create(
            slug='notebooks',
            defaults={
                'name': 'Ноутбуки та комп\'ютери',
                'description': 'Ноутбуки, комп\'ютери, моноблоки'
            }
        )
        
        peripherals_root, _ = Category.objects.get_or_create(
            slug='peripherals',
            defaults={
                'name': 'Периферія',
                'description': 'Монітори, мишки, клавіатури, навушники'
            }
        )
        
        networking_root, _ = Category.objects.get_or_create(
            slug='networking',
            defaults={
                'name': 'Мережеве обладнання',
                'description': 'Роутери, комутатори, мережеві карти'
            }
        )
        
        office_root, _ = Category.objects.get_or_create(
            slug='office',
            defaults={
                'name': 'Офісне приладдя',
                'description': 'Папір, ручки, канцтовари'
            }
        )
        
        # Підкатегорії для Ноутбуки та комп'ютери
        laptops, _ = Category.objects.get_or_create(
            slug='laptops',
            defaults={
                'name': 'Ноутбуки',
                'parent': notebooks_root,
                'description': 'Всі види ноутбуків'
            }
        )
        
        gaming_laptops, _ = Category.objects.get_or_create(
            slug='gaming-laptops',
            defaults={
                'name': 'Ігрові ноутбуки',
                'parent': laptops,
                'description': 'Потужні ноутбуки для ігор'
            }
        )
        
        office_laptops, _ = Category.objects.get_or_create(
            slug='office-laptops',
            defaults={
                'name': 'Офісні ноутбуки',
                'parent': laptops,
                'description': 'Ноутбуки для роботи та навчання'
            }
        )
        
        all_in_one, _ = Category.objects.get_or_create(
            slug='all-in-one',
            defaults={
                'name': 'Моноблоки',
                'parent': notebooks_root,
                'description': 'Комп\'ютер-все-в-одному'
            }
        )
        
        pcs, _ = Category.objects.get_or_create(
            slug='pcs',
            defaults={
                'name': 'Системні блоки',
                'parent': notebooks_root,
                'description': 'Стаціонарні комп\'ютери'
            }
        )
        
        # Підкатегорії для Периферія
        mice, _ = Category.objects.get_or_create(
            slug='mice',
            defaults={
                'name': 'Мишки',
                'parent': peripherals_root,
                'description': 'Комп\'ютерні миші'
            }
        )
        
        keyboards, _ = Category.objects.get_or_create(
            slug='keyboards',
            defaults={
                'name': 'Клавіатури',
                'parent': peripherals_root,
                'description': 'Клавіатури'
            }
        )
        
        monitors, _ = Category.objects.get_or_create(
            slug='monitors',
            defaults={
                'name': 'Монітори',
                'parent': peripherals_root,
                'description': 'Монітори та дисплеї'
            }
        )
        
        headphones, _ = Category.objects.get_or_create(
            slug='headphones',
            defaults={
                'name': 'Навушники',
                'parent': peripherals_root,
                'description': 'Навушники та гарнітури'
            }
        )
        
        self.stdout.write(f'   ✓ Категорій: {Category.objects.count()}')
        
        # === 2. СТВОРЮЄМО АТРИБУТИ ===
        self.stdout.write('2. Створюємо атрибути...')
        
        brand, _ = Attribute.objects.get_or_create(
            slug='brand',
            defaults={
                'name': 'Бренд',
                'type': 'text',
                'is_filterable': True,
                'is_visible': True,
                'sort_order': 1
            }
        )
        
        color, _ = Attribute.objects.get_or_create(
            slug='color',
            defaults={
                'name': 'Колір',
                'type': 'color',
                'is_filterable': True,
                'is_visible': True,
                'sort_order': 2
            }
        )
        
        material, _ = Attribute.objects.get_or_create(
            slug='material',
            defaults={
                'name': 'Матеріал',
                'type': 'text',
                'is_filterable': True,
                'is_visible': True,
                'sort_order': 3
            }
        )
        
        ram, _ = Attribute.objects.get_or_create(
            slug='ram',
            defaults={
                'name': 'Оперативна пам\'ять',
                'type': 'number',
                'unit': 'GB',
                'is_filterable': True,
                'is_visible': True,
                'sort_order': 4
            }
        )
        
        storage, _ = Attribute.objects.get_or_create(
            slug='storage',
            defaults={
                'name': 'Накопичувач',
                'type': 'text',
                'is_filterable': True,
                'is_visible': True,
                'sort_order': 5
            }
        )
        
        cpu, _ = Attribute.objects.get_or_create(
            slug='cpu',
            defaults={
                'name': 'Процесор',
                'type': 'text',
                'is_filterable': True,
                'is_visible': True,
                'sort_order': 6
            }
        )
        
        screen_size, _ = Attribute.objects.get_or_create(
            slug='screen-size',
            defaults={
                'name': 'Діагональ екрану',
                'type': 'number',
                'unit': '"',
                'is_filterable': True,
                'is_visible': True,
                'sort_order': 7
            }
        )
        
        warranty, _ = Attribute.objects.get_or_create(
            slug='warranty',
            defaults={
                'name': 'Гарантія',
                'type': 'text',
                'unit': 'місяців',
                'is_filterable': True,
                'is_visible': True,
                'sort_order': 8
            }
        )
        
        country, _ = Attribute.objects.get_or_create(
            slug='country',
            defaults={
                'name': 'Країна виробник',
                'type': 'text',
                'is_filterable': True,
                'is_visible': True,
                'sort_order': 9
            }
        )
        
        connection, _ = Attribute.objects.get_or_create(
            slug='connection',
            defaults={
                'name': 'Тип підключення',
                'type': 'text',
                'is_filterable': True,
                'is_visible': True,
                'sort_order': 10
            }
        )
        
        self.stdout.write(f'   ✓ Атрибутів: {Attribute.objects.count()}')
        
        # === 3. СТВОРЮЄМО ЗНАЧЕННЯ АТРИБУТІВ ===
        self.stdout.write('3. Створюємо значення атрибутів...')
        
        # Бренди
        brand_asus, _ = self.get_or_create_attribute_value(brand, value_text='ASUS')
        brand_dell, _ = self.get_or_create_attribute_value(brand, value_text='Dell')
        brand_hp, _ = self.get_or_create_attribute_value(brand, value_text='HP')
        brand_lenovo, _ = self.get_or_create_attribute_value(brand, value_text='Lenovo')
        brand_apple, _ = self.get_or_create_attribute_value(brand, value_text='Apple')
        brand_a4tech, _ = self.get_or_create_attribute_value(brand, value_text='A4Tech')
        brand_logitech, _ = self.get_or_create_attribute_value(brand, value_text='Logitech')
        
        # Кольори
        color_black, _ = self.get_or_create_attribute_value(color, value_text='Чорний', value_color='#000000')
        color_white, _ = self.get_or_create_attribute_value(color, value_text='Білий', value_color='#FFFFFF')
        color_gray, _ = self.get_or_create_attribute_value(color, value_text='Сірий', value_color='#808080')
        color_silver, _ = self.get_or_create_attribute_value(color, value_text='Сріблястий', value_color='#C0C0C0')
        
        # Матеріали
        material_plastic, _ = self.get_or_create_attribute_value(material, value_text='Пластик')
        material_aluminum, _ = self.get_or_create_attribute_value(material, value_text='Алюміній')
        
        # RAM (числові значення)
        ram_8gb, _ = self.get_or_create_attribute_value(ram, value_number=8)
        ram_16gb, _ = self.get_or_create_attribute_value(ram, value_number=16)
        ram_32gb, _ = self.get_or_create_attribute_value(ram, value_number=32)
        
        # Накопичувачі
        storage_256, _ = self.get_or_create_attribute_value(storage, value_text='256GB SSD')
        storage_512, _ = self.get_or_create_attribute_value(storage, value_text='512GB SSD')
        storage_1tb, _ = self.get_or_create_attribute_value(storage, value_text='1TB SSD')
        
        # Процесори
        cpu_i5, _ = self.get_or_create_attribute_value(cpu, value_text='Intel Core i5')
        cpu_i7, _ = self.get_or_create_attribute_value(cpu, value_text='Intel Core i7')
        cpu_ryzen5, _ = self.get_or_create_attribute_value(cpu, value_text='AMD Ryzen 5')
        
        # Діагоналі (числові значення)
        screen_14, _ = self.get_or_create_attribute_value(screen_size, value_number=14)
        screen_156, _ = self.get_or_create_attribute_value(screen_size, value_number=15.6)
        screen_27, _ = self.get_or_create_attribute_value(screen_size, value_number=27)
        
        # Гарантії
        warranty_12, _ = self.get_or_create_attribute_value(warranty, value_text='12')
        warranty_24, _ = self.get_or_create_attribute_value(warranty, value_text='24')
        
        # Країни
        country_china, _ = self.get_or_create_attribute_value(country, value_text='Китай')
        country_taiwan, _ = self.get_or_create_attribute_value(country, value_text='Тайвань')
        
        # Типи підключення
        connection_usb, _ = self.get_or_create_attribute_value(connection, value_text='USB')
        connection_wireless, _ = self.get_or_create_attribute_value(connection, value_text='Бездротовий')
        connection_bluetooth, _ = self.get_or_create_attribute_value(connection, value_text='Bluetooth')
        
        self.stdout.write(f'   ✓ Значень атрибутів: {AttributeValue.objects.count()}')
        
        # === 4. СТВОРЮЄМО ТОВАРИ ===
        self.stdout.write('4. Створюємо товари...')
        
        # Товар 1: Ноутбук ASUS VivoBook
        product1, _ = Product.objects.get_or_create(
            slug='asus-vivobook-15',
            defaults={
                'name': 'Ноутбук ASUS VivoBook 15',
                'category': office_laptops,
                'description': 'Потужний ноутбук для роботи та навчання. Intel Core i5, 16GB RAM, 512GB SSD.',
                'price': 18999,
                'old_price': 15999,
                'stock': 25,
                'is_active': True,
                'is_new': True,
                'meta_title': 'ASUS VivoBook 15 купити в Україні',
                'meta_description': 'Ноутбук ASUS VivoBook 15 за найкращою ціною. Характеристики, відгуки, доставка.'
            }
        )
        
        if brand_asus:
            ProductAttributeValue.objects.get_or_create(product=product1, attribute_value=brand_asus)
        if color_silver:
            ProductAttributeValue.objects.get_or_create(product=product1, attribute_value=color_silver)
        if ram_16gb:
            ProductAttributeValue.objects.get_or_create(product=product1, attribute_value=ram_16gb)
        if storage_512:
            ProductAttributeValue.objects.get_or_create(product=product1, attribute_value=storage_512)
        if cpu_i5:
            ProductAttributeValue.objects.get_or_create(product=product1, attribute_value=cpu_i5)
        if warranty_24:
            ProductAttributeValue.objects.get_or_create(product=product1, attribute_value=warranty_24)
        if country_china:
            ProductAttributeValue.objects.get_or_create(product=product1, attribute_value=country_china)
        
        # Товар 2: Ноутбук Dell XPS
        product2, _ = Product.objects.get_or_create(
            slug='dell-xps-13',
            defaults={
                'name': 'Ноутбук Dell XPS 13',
                'category': laptops,
                'description': 'Преміальний ультрабук з безрамковим дисплеєм.',
                'price': 45999,
                'stock': 10,
                'is_active': True,
                'is_bestseller': True,
                'meta_title': 'Dell XPS 13 - преміальний ноутбук'
            }
        )
        
        if brand_dell:
            ProductAttributeValue.objects.get_or_create(product=product2, attribute_value=brand_dell)
        if color_silver:
            ProductAttributeValue.objects.get_or_create(product=product2, attribute_value=color_silver)
        if ram_16gb:
            ProductAttributeValue.objects.get_or_create(product=product2, attribute_value=ram_16gb)
        if storage_512:
            ProductAttributeValue.objects.get_or_create(product=product2, attribute_value=storage_512)
        if cpu_i7:
            ProductAttributeValue.objects.get_or_create(product=product2, attribute_value=cpu_i7)
        if screen_14:
            ProductAttributeValue.objects.get_or_create(product=product2, attribute_value=screen_14)
        
        # Товар 3: Ігровий ноутбук
        product3, _ = Product.objects.get_or_create(
            slug='asus-rog-strix',
            defaults={
                'name': 'Ігровий ноутбук ASUS ROG Strix',
                'category': gaming_laptops,
                'description': 'Потужний ігровий ноутбук з RGB підсвіткою.',
                'price': 52999,
                'old_price': 49999,
                'stock': 5,
                'is_active': True,
                'is_new': True,
            }
        )
        
        if brand_asus:
            ProductAttributeValue.objects.get_or_create(product=product3, attribute_value=brand_asus)
        if color_black:
            ProductAttributeValue.objects.get_or_create(product=product3, attribute_value=color_black)
        if ram_32gb:
            ProductAttributeValue.objects.get_or_create(product=product3, attribute_value=ram_32gb)
        if storage_1tb:
            ProductAttributeValue.objects.get_or_create(product=product3, attribute_value=storage_1tb)
        if cpu_i7:
            ProductAttributeValue.objects.get_or_create(product=product3, attribute_value=cpu_i7)
        
        # Товар 4: Мишка A4Tech
        product4, _ = Product.objects.get_or_create(
            slug='a4tech-bloody-v7m',
            defaults={
                'name': 'Мишка A4Tech Bloody V7M',
                'category': mice,
                'description': 'Ігрова мишка з підсвіткою та додатковими кнопками.',
                'price': 899,
                'stock': 50,
                'is_active': True,
                'is_bestseller': True,
            }
        )
        
        if brand_a4tech:
            ProductAttributeValue.objects.get_or_create(product=product4, attribute_value=brand_a4tech)
        if color_black:
            ProductAttributeValue.objects.get_or_create(product=product4, attribute_value=color_black)
        if material_plastic:
            ProductAttributeValue.objects.get_or_create(product=product4, attribute_value=material_plastic)
        if connection_usb:
            ProductAttributeValue.objects.get_or_create(product=product4, attribute_value=connection_usb)
        if warranty_12:
            ProductAttributeValue.objects.get_or_create(product=product4, attribute_value=warranty_12)
        if country_china:
            ProductAttributeValue.objects.get_or_create(product=product4, attribute_value=country_china)
        
        # Товар 5: Мишка Logitech
        product5, _ = Product.objects.get_or_create(
            slug='logitech-mx-master-3',
            defaults={
                'name': 'Мишка Logitech MX Master 3',
                'category': mice,
                'description': 'Бездротова мишка для професіоналів.',
                'price': 3999,
                'old_price': 3499,
                'stock': 30,
                'is_active': True,
                'is_new': True,
            }
        )
        
        if brand_logitech:
            ProductAttributeValue.objects.get_or_create(product=product5, attribute_value=brand_logitech)
        if color_gray:
            ProductAttributeValue.objects.get_or_create(product=product5, attribute_value=color_gray)
        if material_aluminum:
            ProductAttributeValue.objects.get_or_create(product=product5, attribute_value=material_aluminum)
        if connection_bluetooth:
            ProductAttributeValue.objects.get_or_create(product=product5, attribute_value=connection_bluetooth)
        if warranty_24:
            ProductAttributeValue.objects.get_or_create(product=product5, attribute_value=warranty_24)
        
        # Товар 6: Монітор Dell
        product6, _ = Product.objects.get_or_create(
            slug='dell-s2721h',
            defaults={
                'name': 'Монітор Dell 27" S2721H',
                'category': monitors,
                'description': '27-дюймовий IPS монітор для роботи та розваг.',
                'price': 8999,
                'stock': 15,
                'is_active': True,
            }
        )
        
        if brand_dell:
            ProductAttributeValue.objects.get_or_create(product=product6, attribute_value=brand_dell)
        if color_black:
            ProductAttributeValue.objects.get_or_create(product=product6, attribute_value=color_black)
        if screen_27:
            ProductAttributeValue.objects.get_or_create(product=product6, attribute_value=screen_27)
        
        # Товар 7: Клавіатура
        product7, _ = Product.objects.get_or_create(
            slug='logitech-k380',
            defaults={
                'name': 'Клавіатура Logitech K380',
                'category': keyboards,
                'description': 'Компактна бездротова клавіатура.',
                'price': 1299,
                'stock': 40,
                'is_active': True,
            }
        )
        
        if brand_logitech:
            ProductAttributeValue.objects.get_or_create(product=product7, attribute_value=brand_logitech)
        if color_white:
            ProductAttributeValue.objects.get_or_create(product=product7, attribute_value=color_white)
        if connection_bluetooth:
            ProductAttributeValue.objects.get_or_create(product=product7, attribute_value=connection_bluetooth)
        
        self.stdout.write(f'   ✓ Товарів: {Product.objects.count()}')
        
        # === 5. СТВОРЮЄМО СУПЕРКОРИСТУВАЧА ===
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
            self.stdout.write('   ✓ Створено суперкористувача (логін: admin, пароль: admin123)')
        else:
            self.stdout.write('   ✓ Суперкористувач вже існує')
        
        self.stdout.write(self.style.SUCCESS('✅ Базу даних успішно наповнено тестовими даними!'))