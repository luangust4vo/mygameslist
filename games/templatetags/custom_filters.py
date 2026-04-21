import markdown
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def pretty_username(value):
    if not value:
        return ""

    normalized = str(value).replace("_", " ").replace("-", " ")
    return " ".join(normalized.split()).title()


@register.filter
def render_markdown(text):
    return mark_safe(markdown.markdown(text))
