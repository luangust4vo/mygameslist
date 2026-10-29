from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class ConfiguracaoIA(models.Model):
    """Configuração única (pk=1) editada pelo Moderador. A chave de API fica fora do banco."""

    modelo = models.CharField(
        max_length=100,
        default="gemini-flash-lite-latest",
        verbose_name="Modelo do Gemini",
        help_text="Nome do modelo na API, por exemplo gemini-flash-lite-latest.",
    )
    temperatura = models.FloatField(
        default=0.7,
        validators=[MinValueValidator(0), MaxValueValidator(2)],
        verbose_name="Temperatura",
        help_text="De 0 a 2. Valores baixos deixam as respostas mais previsíveis.",
    )
    max_tokens = models.PositiveIntegerField(
        default=2048,
        validators=[MinValueValidator(64), MaxValueValidator(65536)],
        verbose_name="Máximo de tokens por resposta",
        help_text="Inclui os tokens de raciocínio dos modelos que pensam antes de responder.",
    )
    cota_mensal_padrao = models.PositiveIntegerField(
        default=100000,
        verbose_name="Cota mensal padrão por usuário (tokens)",
    )
    ativa = models.BooleanField(
        default=True,
        verbose_name="IA ativa",
        help_text="Desmarque para bloquear todas as chamadas sem precisar de novo deploy.",
    )
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração da IA"
        verbose_name_plural = "Configuração da IA"

    def __str__(self):
        return f"Configuração da IA ({self.modelo})"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def atual(cls):
        configuracao, _ = cls.objects.get_or_create(pk=1)
        return configuracao


class CotaUsuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cota_ia")
    limite_mensal = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Limite mensal (tokens)",
        help_text="Deixe vazio para usar a cota padrão da configuração.",
    )

    class Meta:
        verbose_name = "Cota de IA do usuário"
        verbose_name_plural = "Cotas de IA dos usuários"

    def __str__(self):
        return f"{self.user.username}: {self.limite_mensal or 'cota padrão'}"


class RequisicaoIA(models.Model):
    FINALIDADE_CHOICES = [
        ("traducao", "Tradução de descrição"),
        ("classificacao", "Classificação de pergunta"),
        ("assistente", "Assistente"),
        ("teste", "Teste de conexão"),
    ]
    STATUS_CHOICES = [
        ("sucesso", "Sucesso"),
        ("erro", "Erro"),
        ("bloqueada", "Bloqueada"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="requisicoes_ia"
    )
    finalidade = models.CharField(max_length=20, choices=FINALIDADE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    modelo = models.CharField(max_length=100, blank=True, default="")
    entrada = models.TextField(blank=True, default="")
    saida = models.TextField(blank=True, default="")
    erro = models.CharField(max_length=255, blank=True, default="")
    tokens_entrada = models.PositiveIntegerField(default=0)
    tokens_saida = models.PositiveIntegerField(default=0)
    tokens_total = models.PositiveIntegerField(default=0)
    duracao_ms = models.PositiveIntegerField(default=0)
    criada_em = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-criada_em"]
        verbose_name = "Requisição à IA"
        verbose_name_plural = "Requisições à IA"

    def __str__(self):
        usuario = self.user.username if self.user else "sistema"
        return f"{usuario} — {self.get_finalidade_display()} — {self.get_status_display()}"  # type: ignore
