from django.contrib import admin

from .models import ConfiguracaoIA, CotaUsuario, RequisicaoIA


@admin.register(ConfiguracaoIA)
class ConfiguracaoIAAdmin(admin.ModelAdmin):
    list_display = ("modelo", "temperatura", "max_tokens", "cota_mensal_padrao", "ativa")


@admin.register(CotaUsuario)
class CotaUsuarioAdmin(admin.ModelAdmin):
    list_display = ("user", "limite_mensal")


@admin.register(RequisicaoIA)
class RequisicaoIAAdmin(admin.ModelAdmin):
    list_display = ("criada_em", "user", "finalidade", "status", "modelo", "tokens_total", "duracao_ms")
    list_filter = ("finalidade", "status")
    search_fields = ("user__username", "erro")
