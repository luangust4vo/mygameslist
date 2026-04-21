from .models import Game, Genre, Platform
from .rawg import get_details

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
        description=data.get('description_raw', ''),
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

    return game