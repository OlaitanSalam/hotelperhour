# superadmin/templatetags/sum_attr.py
from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def sum_attr(queryset, attr):
    """Safely sum an attribute/property from a queryset"""
    total = Decimal('0.00')
    for item in queryset:
        value = getattr(item, attr, None)
        if value is not None:
            try:
                total += Decimal(str(value))
            except (ValueError, TypeError):
                continue
    return total