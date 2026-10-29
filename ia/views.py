from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db.models import Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, UpdateView
from django_filters.views import FilterView

from games.mixins import GroupRequiredMixin

from games.sanitize import markdown_seguro

from .assistente import TAMANHO_MAXIMO, ForaDoEscopo, responder
from .filters import RequisicaoIAFilter
from .forms import ConfiguracaoIAForm, CotaUsuarioForm, PerguntaForm
from .models import ConfiguracaoIA, CotaUsuario, MensagemAssistente, RequisicaoIA
from .servicos import (
    CotaEsgotada,
    ErroIA,
    chamar_ia,
    consumo_do_mes,
    inicio_do_mes,
    limite_mensal,
)


class ModeradorMixin(LoginRequiredMixin, GroupRequiredMixin):
    group_required = "Moderador"


class RequisicaoListView(ModeradorMixin, FilterView):
    model = RequisicaoIA
    filterset_class = RequisicaoIAFilter
    template_name = "games/ia/requisicoes.html"
    context_object_name = "requisicoes"
    paginate_by = 20

    def get_queryset(self):
        return RequisicaoIA.objects.select_related("user")


class ConfiguracaoUpdateView(ModeradorMixin, UpdateView):
    model = ConfiguracaoIA
    form_class = ConfiguracaoIAForm
    template_name = "games/ia/configuracao.html"
    success_url = reverse_lazy("ia:configuracao")

    def get_object(self, queryset=None):
        return ConfiguracaoIA.atual()

    def form_valid(self, form):
        messages.success(self.request, "Configuração da IA salva.")
        return super().form_valid(form)


class TestarConexaoView(ModeradorMixin, View):
    def post(self, request):
        try:
            resposta = chamar_ia(
                request.user,
                "teste",
                "Responda apenas com a palavra OK.",
                max_tokens=ConfiguracaoIA.atual().max_tokens,
            )
        except ErroIA as erro:
            detalhe = f" Detalhe: {erro.detalhe}" if erro.detalhe else ""
            messages.error(request, f"O teste falhou. {erro}{detalhe}")
        else:
            messages.success(
                request,
                f"Conexão funcionando. O modelo respondeu “{resposta.texto[:80]}” "
                f"usando {resposta.tokens_total} tokens.",
            )
        return redirect("ia:configuracao")


class UsuarioIAListView(ModeradorMixin, ListView):
    template_name = "games/ia/usuarios.html"
    context_object_name = "usuarios"
    paginate_by = 20

    def get_queryset(self):
        padrao = ConfiguracaoIA.atual().cota_mensal_padrao
        do_mes = Q(requisicoes_ia__criada_em__gte=inicio_do_mes())
        return (
            User.objects.annotate(
                consumo_mes=Coalesce(Sum("requisicoes_ia__tokens_total", filter=do_mes), 0),
                limite=Coalesce("cota_ia__limite_mensal", Value(padrao)),
            )
            .order_by("-consumo_mes", "username")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cota_padrao"] = ConfiguracaoIA.atual().cota_mensal_padrao
        return context


class CotaUsuarioUpdateView(ModeradorMixin, UpdateView):
    form_class = CotaUsuarioForm
    template_name = "games/ia/cota_form.html"
    success_url = reverse_lazy("ia:usuarios")

    def get_object(self, queryset=None):
        usuario = get_object_or_404(User, pk=self.kwargs["pk"])
        cota, _ = CotaUsuario.objects.get_or_create(user=usuario)
        return cota

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cota_padrao"] = ConfiguracaoIA.atual().cota_mensal_padrao
        context["consumo_mes"] = consumo_do_mes(self.object.user)
        return context

    def form_valid(self, form):
        messages.success(self.request, f"Cota de IA de {self.object.user.username} atualizada.")
        return super().form_valid(form)


class MeuConsumoView(LoginRequiredMixin, ListView):
    template_name = "games/ia/meu_consumo.html"
    context_object_name = "requisicoes"
    paginate_by = 20

    def get_queryset(self):
        return RequisicaoIA.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usado = consumo_do_mes(self.request.user)
        limite = limite_mensal(self.request.user)
        context["usado"] = usado
        context["limite"] = limite
        context["restante"] = max(limite - usado, 0)
        context["percentual"] = min(round(usado * 100 / limite), 100) if limite else 100
        return context


class AssistenteView(LoginRequiredMixin, ListView):
    template_name = "games/ia/assistente.html"
    context_object_name = "mensagens"

    def get_queryset(self):
        return MensagemAssistente.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = PerguntaForm()
        context["tamanho_maximo"] = TAMANHO_MAXIMO
        return context


class PerguntarView(LoginRequiredMixin, View):
    """Recebe a pergunta por AJAX ($.ajax com CSRF) e responde em JSON.

    Sem JavaScript, o formulário é enviado normalmente e a resposta volta pela página.
    """

    def post(self, request):
        ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
        form = PerguntaForm(request.POST)
        if not form.is_valid():
            erro = form.errors["pergunta"][0]
            return self.falha(request, ajax, erro, status=400)

        pergunta = form.cleaned_data["pergunta"]
        try:
            mensagem = responder(request.user, pergunta)
        except ForaDoEscopo as erro:
            return self.falha(request, ajax, str(erro), status=200, tipo="recusa")
        except CotaEsgotada as erro:
            return self.falha(request, ajax, str(erro), status=429)
        except ErroIA as erro:
            return self.falha(request, ajax, str(erro), status=503)

        if ajax:
            return JsonResponse(
                {"ok": True, "pergunta": pergunta, "resposta_html": markdown_seguro(mensagem.texto)}
            )
        return redirect("ia:assistente")

    def falha(self, request, ajax, erro, status, tipo="erro"):
        if ajax:
            return JsonResponse({"ok": False, "tipo": tipo, "erro": erro}, status=status)
        if tipo == "recusa":
            messages.info(request, erro)
        else:
            messages.error(request, erro)
        return redirect("ia:assistente")


class LimparConversaView(LoginRequiredMixin, View):
    def post(self, request):
        apagadas, _ = MensagemAssistente.objects.filter(user=request.user).delete()
        if apagadas:
            messages.success(request, "Conversa apagada.")
        else:
            messages.info(request, "A conversa já estava vazia.")
        return redirect("ia:assistente")
