import logging
import re

from ia.servicos import ErroIA, chamar_ia

from .models import Game, Genre, Platform
from .rawg import get_details, get_stores
from .sanitize import sanitize_html
from .steam import get_description_pt

logger = logging.getLogger(__name__)

STEAM_APP_URL = re.compile(r'store\.steampowered\.com/app/(\d+)')
CERCA_DE_CODIGO = re.compile(r'^```[a-z]*\s*|\s*```$')

# Descrições longas precisam de mais espaço que uma resposta comum.
TRADUCAO_MAX_TOKENS = 8192
INSTRUCOES_TRADUCAO = (
    'Você traduz descrições de jogos do inglês para o português do Brasil. '
    'Mantenha exatamente as mesmas tags HTML (h2, h3, h4, p, br, ul, ol, li, strong, em) e a mesma estrutura. '
    'Não traduza nomes de jogos, personagens, lugares, empresas nem termos de mecânica consagrados em inglês. '
    'Não acrescente comentários, títulos nem explicações: responda só com o HTML traduzido.'
)


class TraducaoIncompleta(ErroIA):
    pass


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


def traduzir_descricao(game, user):
    """Traduz a descrição original com a IA e grava com fonte "ia".

    A chamada conta na cota de `user`. Levanta ErroIA (inclusive TraducaoIncompleta)
    sem alterar o jogo.
    """
    resposta = chamar_ia(
        user,
        'traducao',
        game.description,
        instrucoes=INSTRUCOES_TRADUCAO,
        max_tokens=TRADUCAO_MAX_TOKENS,
        temperatura=0.2,
    )
    if resposta.cortada:
        raise TraducaoIncompleta(
            'A tradução ficou incompleta e não foi salva.', 'Resposta cortada pelo limite de tokens.'
        )

    traducao = sanitize_html(CERCA_DE_CODIGO.sub('', resposta.texto.strip()))
    if not traducao:
        raise TraducaoIncompleta('A IA não devolveu uma tradução.', 'Texto vazio depois da sanitização.')

    game.description_pt = traducao
    game.description_pt_source = 'ia'
    game.save(update_fields=['description_pt', 'description_pt_source'])


def import_game(id, user=None):
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
    if not game.description_pt and game.description:
        try:
            traduzir_descricao(game, user)
        except ErroIA as erro:
            logger.info('Descrição de %s não traduzida pela IA: %s', game.rawg_id, erro.detalhe or erro)

    return game
