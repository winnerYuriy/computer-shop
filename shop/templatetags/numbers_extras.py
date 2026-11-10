# shop/templatetags/numbers_extras.py

from django import template

register = template.Library()

@register.filter
def format_number(value):
    """Форматує число з пробілом як роздільник тисяч (без копійок)"""
    if value is None:
        return "0"
    try:
        return f"{int(value):,}".replace(",", " ")
    except (ValueError, TypeError):
        return str(value)

@register.filter
def format_currency(value):
    """Форматує валюту з пробілом як роздільник тисяч та знаком ₴"""
    if value is None:
        return "0 ₴"
    try:
        formatted = f"{int(value):,}".replace(",", " ")
        return f"{formatted} ₴"
    except (ValueError, TypeError):
        return f"{value} ₴"