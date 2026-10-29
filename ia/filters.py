import django_filters

from .models import RequisicaoIA


class RequisicaoIAFilter(django_filters.FilterSet):
    usuario = django_filters.CharFilter(
        field_name="user__username", lookup_expr="icontains", label="Usuário"
    )
    finalidade = django_filters.ChoiceFilter(
        choices=RequisicaoIA.FINALIDADE_CHOICES, label="Finalidade", empty_label="Todas"
    )
    status = django_filters.ChoiceFilter(
        choices=RequisicaoIA.STATUS_CHOICES, label="Status", empty_label="Todos"
    )

    class Meta:
        model = RequisicaoIA
        fields = ["usuario", "finalidade", "status"]
