from datetime import datetime

from django import template

register = template.Library()


@register.filter
def get_item(d, key):
    if d is None:
        return ""
    return d.get(key, "")


@register.filter
def format_value(value):
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M:%S")
    if value is None:
        return ""
    return value
