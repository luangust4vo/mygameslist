from django import forms

from .models import ConfiguracaoIA, CotaUsuario


class ConfiguracaoIAForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoIA
        fields = ["modelo", "temperatura", "max_tokens", "cota_mensal_padrao", "ativa"]


class CotaUsuarioForm(forms.ModelForm):
    class Meta:
        model = CotaUsuario
        fields = ["limite_mensal"]
