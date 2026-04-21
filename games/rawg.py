import requests
from django.conf import settings

BASE_URL = 'https://api.rawg.io/api'

def get_params(extra=None):
    params = {'key': settings.API_KEY}
    if extra:
        params.update(extra)
    return params

def get(query, page=1):
    response = requests.get(
        f'{BASE_URL}/games',
        params=get_params({
            'search': query,
            'page': page,
            'page_size': 12,
        })
    )
    if response.status_code == 200:
        return response.json()
    return None


def get_details(id):
    response = requests.get(
        f'{BASE_URL}/games/{id}',
        params=get_params()
    )
    if response.status_code == 200:
        return response.json()
    return None