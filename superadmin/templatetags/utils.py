
from django import template

register = template.Library()

@register.filter
def zip_lists(a, b):
    return zip(a, b)  # Now refers to built-in zip

@register.filter
def index(sequence, position):
    return sequence[position]