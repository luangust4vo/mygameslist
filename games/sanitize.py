import re

import markdown
import nh3

ALLOWED_TAGS = {'h2', 'h3', 'h4', 'p', 'br', 'ul', 'ol', 'li', 'strong', 'em'}

HTML_TAG = re.compile(r'</?[a-zA-Z][^>]*>')
H1_TAG = re.compile(r'<(/?)h1\b[^>]*>', re.IGNORECASE)
EMPTY_PARAGRAPH = re.compile(r'<p>(?:\s|<br>)*</p>')


def has_html(text):
    return bool(HTML_TAG.search(text or ''))


def sanitize_html(html):
    # h1 fica reservado ao título da página; o conteúdo vira h2 em vez de texto solto
    html = H1_TAG.sub(r'<\1h2>', html or '')
    html = nh3.clean(html, tags=ALLOWED_TAGS, attributes={}, link_rel=None)
    # imagens removidas costumam deixar parágrafos vazios para trás
    return EMPTY_PARAGRAPH.sub('', html).strip()


def description_to_html(text):
    if not text:
        return ''
    if not has_html(text):
        text = markdown.markdown(text)
    return sanitize_html(text)
