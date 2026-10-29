from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db.models import Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, UpdateView
from django_filters.views import FilterView

from games.mixins import GroupRequiredMixin

from .filters import RequisicaoIAFilter
from .forms import ConfiguracaoIAForm, CotaUsuarioForm
from .models import ConfiguracaoIA, CotaUsuario, RequisicaoIA
from .servicos import ErroIA, chamar_ia, consumo_do_mes, inicio_do_mes, limite_mensal


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
