"""Cliente HTTP da API REST do Gemini. Só deve ser usado por ia.servicos.chamar_ia."""

import requests

BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/models'

# O gunicorn do App Engine derruba o worker em 30 s; desistimos antes disso.
TIMEOUT = 25


class ErroGemini(Exception):
    def __init__(self, mensagem, uso=None):
        super().__init__(mensagem)
        self.uso = uso or {}


def _uso(dados):
    meta = dados.get('usageMetadata') or {}
    saida = meta.get('candidatesTokenCount', 0) + meta.get('thoughtsTokenCount', 0)
    return {
        'tokens_entrada': meta.get('promptTokenCount', 0),
        'tokens_saida': saida,
        'tokens_total': meta.get('totalTokenCount', 0),
    }


def gerar(chave, modelo, mensagens, instrucoes='', temperatura=0.7, max_tokens=2048):
    """`mensagens` é uma lista de (papel, texto), com papel "user" ou "model"."""
    corpo = {
        'contents': [{'role': papel, 'parts': [{'text': texto}]} for papel, texto in mensagens],
        'generationConfig': {'temperature': temperatura, 'maxOutputTokens': max_tokens},
    }
    if instrucoes:
        corpo['systemInstruction'] = {'parts': [{'text': instrucoes}]}

    try:
        response = requests.post(
            f'{BASE_URL}/{modelo}:generateContent',
            headers={'x-goog-api-key': chave},
            json=corpo,
            timeout=TIMEOUT,
        )
    except requests.Timeout:
        raise ErroGemini(f'Tempo esgotado ({TIMEOUT} s) esperando o Gemini.')
    except requests.RequestException as erro:
        raise ErroGemini(f'Falha de conexão com o Gemini: {type(erro).__name__}.')

    try:
        dados = response.json()
    except ValueError:
        raise ErroGemini(f'Resposta inválida do Gemini (HTTP {response.status_code}).')

    if response.status_code != 200:
        mensagem = (dados.get('error') or {}).get('message', '')
        raise ErroGemini(f'HTTP {response.status_code}: {mensagem}'[:255])

    uso = _uso(dados)
    bloqueio = (dados.get('promptFeedback') or {}).get('blockReason')
    if bloqueio:
        raise ErroGemini(f'Pergunta bloqueada pelo Gemini ({bloqueio}).', uso)

    candidatos = dados.get('candidates') or [{}]
    partes = (candidatos[0].get('content') or {}).get('parts') or []
    texto = ''.join(parte.get('text', '') for parte in partes if not parte.get('thought')).strip()
    motivo = candidatos[0].get('finishReason', 'desconhecido')
    if not texto:
        raise ErroGemini(f'O Gemini não devolveu texto (motivo: {motivo}).', uso)

    # motivo "MAX_TOKENS" indica que o texto foi cortado pelo limite de tokens
    return {'texto': texto, 'motivo': motivo, **uso}
