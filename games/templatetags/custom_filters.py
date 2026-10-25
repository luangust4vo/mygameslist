import markdown
from django import template
from django.utils.safestring import mark_safe

from games.generos import traduzir_genero
from games.sanitize import description_to_html

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


@register.filter
def descricao(text):
    return mark_safe(description_to_html(text))


@register.filter
def genero_pt(genero):
    return traduzir_genero(str(genero))


@register.filter
def has_group(user, name):
    return user.is_authenticated and user.groups.filter(name=name).exists()
