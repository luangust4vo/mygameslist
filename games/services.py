import logging
import re

from .models import Game, Genre, Platform
from .rawg import get_details, get_stores
from .sanitize import sanitize_html
from .steam import get_description_pt

logger = logging.getLogger(__name__)

STEAM_APP_URL = re.compile(r'store\.steampowered\.com/app/(\d+)')


def find_steam_appid(rawg_id):
    stores = get_stores(rawg_id) or {}
    for store in stores.get('results', []):
        match = STEAM_APP_URL.search(store.get('url') or '')
        if match:
            return match.group(1)
    return None


def import_description_pt(game):
    try:
        appid = find_steam_appid(game.rawg_id)
        if not appid:
            return
        description = get_description_pt(appid)
        if description:
            game.description_pt = description
            game.description_pt_source = 'steam'
            game.save(update_fields=['description_pt', 'description_pt_source'])
    except Exception:
        logger.exception('Falha ao buscar descrição em português do jogo %s', game.rawg_id)


def import_game(id):
    game = Game.objects.filter(rawg_id=id).first()
    if game:
        return game

    data = get_details(id)
    if not data:
        return None

    game = Game.objects.create(
        rawg_id=data['id'],
        title=data['name'],
        description=sanitize_html(data.get('description') or data.get('description_raw') or ''),
        cover_url=data.get('background_image', ''),
        release_date=data.get('released'),
        rawg_rating=data.get('rating', 0),
    )

    for g in data.get('genres', []):
        genre, _ = Genre.objects.get_or_create(
            rawg_id=g['id'],
            defaults={'name': g['name']}
        )
        game.genres.add(genre)

    for p in data.get('platforms', []):
        platform, _ = Platform.objects.get_or_create(
            rawg_id=p['platform']['id'],
            defaults={'name': p['platform']['name']}
        )
        game.platforms.add(platform)

    import_description_pt(game)

    return game
