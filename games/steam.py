import html

import requests

from .sanitize import sanitize_html

APPDETAILS_URL = 'https://store.steampowered.com/api/appdetails'


def get_description_pt(appid):
    try:
        response = requests.get(
            APPDETAILS_URL,
            params={'appids': appid, 'l': 'brazilian', 'cc': 'br'},
            timeout=10,
        )
        if response.status_code != 200:
            return None
        entry = response.json()[str(appid)]
        if not entry.get('success'):
            return None
        data = entry['data']
        raw = data.get('detailed_description') or data.get('about_the_game') or ''
        description = sanitize_html(raw)

        short = html.unescape(data.get('short_description') or '').strip()
        if short and '<p>' not in description:
            description = f'<p>{html.escape(short)}</p>{description}'

        return description or None
    except Exception:
        return None
