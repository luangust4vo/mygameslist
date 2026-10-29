"""Assistente de jogos: classifica a pergunta, monta o contexto e guarda o histórico."""

from pathlib import Path

from django.db import transaction

from games.models import UserGameList

from .models import MensagemAssistente
from .servicos import ErroIA, chamar_ia

CONTEXTO_PROJETO = Path(__file__).resolve().parent / 'contexto_projeto.md'

# Mensagens enviadas à IA: as 4 últimas do histórico mais a pergunta nova.
JANELA = 5
LIMITE_LISTA = 30
TAMANHO_MAXIMO = 500

INSTRUCOES_CLASSIFICACAO = (
    'Você classifica mensagens enviadas ao assistente de um site sobre jogos eletrônicos. '
    'Responda apenas "permitido" se a mensagem for sobre jogos eletrônicos, sobre o uso do site '
    '(lista de jogos, reviews, conta, cota de IA) ou for um cumprimento. '
    'Responda apenas "fora" para qualquer outro assunto.'
)
RECUSA = (
    'Só consigo ajudar com perguntas sobre jogos e sobre o uso do MyGamesList. '
    'Pergunte, por exemplo, o que jogar depois de um jogo de que você gostou.'
)


class ForaDoEscopo(ErroIA):
    pass


def ler_contexto():
    return CONTEXTO_PROJETO.read_text(encoding='utf-8')


def resumo_da_lista(user):
    itens = (
        UserGameList.objects.filter(user=user)
        .select_related('game')
        .order_by('-date_updated', '-pk')[:LIMITE_LISTA]
    )
    linhas = [f'- {item.game.title} ({item.get_status_display()})' for item in itens]
    if not linhas:
        return 'O usuário ainda não tem jogos na lista.'
    return '\n'.join(linhas)


def montar_instrucoes(user):
    return (
        f'{ler_contexto()}\n\n'
        f'## Usuário\n\nNome: {user.username}\n\n'
        f'Jogos na lista (até {LIMITE_LISTA}, os mais recentes primeiro):\n{resumo_da_lista(user)}'
    )


def classificar(user, pergunta):
    """Chamada curta, só com a pergunta, que decide se o assunto é permitido."""
    resposta = chamar_ia(
        user,
        'classificacao',
        pergunta,
        instrucoes=INSTRUCOES_CLASSIFICACAO,
        max_tokens=256,
        temperatura=0,
        timeout=10,
    )
    return not resposta.texto.strip().lower().startswith('fora')


def janela_de_mensagens(user, pergunta):
    anteriores = list(
        MensagemAssistente.objects.filter(user=user).order_by('-criada_em', '-pk')[: JANELA - 1]
    )
    anteriores.reverse()
    # O Gemini espera a conversa começando pelo usuário.
    while anteriores and anteriores[0].papel != 'user':
        anteriores.pop(0)
    return [(m.papel, m.texto) for m in anteriores] + [('user', pergunta)]


def responder(user, pergunta):
    """Devolve a mensagem do assistente já salva no histórico.

    Levanta ForaDoEscopo ou outro ErroIA sem salvar nada.
    """
    if not classificar(user, pergunta):
        raise ForaDoEscopo(RECUSA, 'Pergunta classificada como fora do escopo.')

    resposta = chamar_ia(
        user,
        'assistente',
        janela_de_mensagens(user, pergunta),
        instrucoes=montar_instrucoes(user),
    )
    texto = resposta.texto
    if resposta.cortada:
        texto += '\n\n*(Resposta interrompida pelo limite de tokens.)*'
    with transaction.atomic():
        MensagemAssistente.objects.create(user=user, papel='user', texto=pergunta)
        return MensagemAssistente.objects.create(user=user, papel='model', texto=texto)
