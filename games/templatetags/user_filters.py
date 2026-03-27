from django import template

register = template.Library()

@register.filter
def pretty_username(value):
    if not value:
        return ""

    normalized = str(value).replace("_", " ").replace("-", " ")
    return " ".join(normalized.split()).title()
