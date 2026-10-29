"""Única porta de entrada para a IA: todo o projeto chama `chamar_ia`."""

import time
from dataclasses import dataclass

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from . import gemini
from .models import ConfiguracaoIA, CotaUsuario, RequisicaoIA


class ErroIA(Exception):
    """Erro com mensagem pronta para o usuário; `detalhe` é para o Moderador."""

    def __init__(self, mensagem, detalhe=''):
        super().__init__(mensagem)
        self.detalhe = detalhe


class IADesativada(ErroIA):
    pass


class CotaEsgotada(ErroIA):
    pass


class IAIndisponivel(ErroIA):
    pass


@dataclass
class RespostaIA:
    texto: str
    tokens_total: int
    requisicao: RequisicaoIA
    motivo: str = 'STOP'

    @property
    def cortada(self):
        """True quando o texto parou no limite de tokens e está incompleto."""
        return self.motivo == 'MAX_TOKENS'


def inicio_do_mes():
    agora = timezone.localtime()
    return agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def consumo_do_mes(user):
    total = RequisicaoIA.objects.filter(user=user, criada_em__gte=inicio_do_mes()).aggregate(
        total=Sum('tokens_total')
    )['total']
    return total or 0


def limite_mensal(user, configuracao=None):
    configuracao = configuracao or ConfiguracaoIA.atual()
    cota = CotaUsuario.objects.filter(user=user).first()
    if cota and cota.limite_mensal is not None:
        return cota.limite_mensal
    return configuracao.cota_mensal_padrao


def _normalizar(mensagens):
    if isinstance(mensagens, str):
        return [('user', mensagens)]
    return list(mensagens)


def chamar_ia(
    user, finalidade, mensagens, instrucoes='', max_tokens=None, temperatura=None, timeout=gemini.TIMEOUT
):
    """Chama o Gemini respeitando a configuração e a cota, e registra a chamada.

    `user` pode ser None em chamadas do sistema (não contam cota de ninguém).
    `mensagens` é um texto ou uma lista de (papel, texto), com papel "user" ou "model".
    Levanta IADesativada, CotaEsgotada ou IAIndisponivel.
    """
    configuracao = ConfiguracaoIA.atual()
    mensagens = _normalizar(mensagens)
    requisicao = RequisicaoIA(
        user=user,
        finalidade=finalidade,
        modelo=configuracao.modelo,
        entrada='\n\n'.join(f'[{papel}] {texto}' for papel, texto in mensagens),
    )

    def bloquear(erro):
        requisicao.status = 'bloqueada'
        requisicao.erro = erro.detalhe or str(erro)
        requisicao.save()
        raise erro

    if not configuracao.ativa:
        bloquear(IADesativada('A IA está desativada no momento.', 'IA desativada na configuração.'))

    if user is not None and consumo_do_mes(user) >= limite_mensal(user, configuracao):
        bloquear(CotaEsgotada('Sua cota de IA deste mês acabou.', 'Cota mensal esgotada.'))

    chave = getattr(settings, 'GEMINI_API_KEY', '')
    if not chave:
        bloquear(IAIndisponivel('A IA não está configurada.', 'GEMINI_API_KEY ausente.'))

    inicio = time.monotonic()
    try:
        resultado = gemini.gerar(
            chave,
            configuracao.modelo,
            mensagens,
            instrucoes=instrucoes,
            temperatura=configuracao.temperatura if temperatura is None else temperatura,
            max_tokens=max_tokens or configuracao.max_tokens,
            timeout=timeout,
        )
    except gemini.ErroGemini as erro:
        requisicao.status = 'erro'
        requisicao.erro = str(erro)[:255]
        requisicao.duracao_ms = int((time.monotonic() - inicio) * 1000)
        for campo, valor in erro.uso.items():
            setattr(requisicao, campo, valor)
        requisicao.save()
        raise IAIndisponivel(
            'A IA está indisponível no momento. Tente de novo mais tarde.', str(erro)
        )

    requisicao.status = 'sucesso'
    requisicao.saida = resultado['texto']
    requisicao.tokens_entrada = resultado['tokens_entrada']
    requisicao.tokens_saida = resultado['tokens_saida']
    requisicao.tokens_total = resultado['tokens_total']
    requisicao.duracao_ms = int((time.monotonic() - inicio) * 1000)
    requisicao.save()
    return RespostaIA(
        resultado['texto'], resultado['tokens_total'], requisicao, resultado.get('motivo', 'STOP')
    )
