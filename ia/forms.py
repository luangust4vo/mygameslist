from django import forms

from .assistente import TAMANHO_MAXIMO
from .models import ConfiguracaoIA, CotaUsuario


class ConfiguracaoIAForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoIA
        fields = ["modelo", "temperatura", "max_tokens", "cota_mensal_padrao", "ativa"]


class CotaUsuarioForm(forms.ModelForm):
    class Meta:
        model = CotaUsuario
        fields = ["limite_mensal"]


class PerguntaForm(forms.Form):
    pergunta = forms.CharField(
        label="Pergunta",
        max_length=TAMANHO_MAXIMO,
        widget=forms.Textarea(attrs={"rows": 2, "maxlength": TAMANHO_MAXIMO}),
        error_messages={
            "required": "Escreva uma pergunta.",
            "max_length": f"A pergunta pode ter no máximo {TAMANHO_MAXIMO} caracteres.",
        },
    )
