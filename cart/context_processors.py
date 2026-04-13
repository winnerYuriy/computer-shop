from .cart import Cart


def cart(request):
    """Додає об'єкт кошика до всіх шаблонів"""
    return {'cart': Cart(request)}