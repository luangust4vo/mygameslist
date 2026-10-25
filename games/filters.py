import django_filters

from .generos import traduzir_genero
from .models import Genre, Platform, Review, UserGameList


def generos_da_lista(request):
    return Genre.objects.filter(game__usergamelist__user=request.user).distinct()


def plataformas_da_lista(request):
    return Platform.objects.filter(game__usergamelist__user=request.user).distinct()


class UserGameListFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(
        choices=UserGameList.STATUS_CHOICES, label="Status", empty_label="Todos"
    )
    genero = django_filters.ModelChoiceFilter(
        field_name="game__genres",
        queryset=generos_da_lista,
        label="Gênero",
        empty_label="Todos",
    )
    plataforma = django_filters.ModelChoiceFilter(
        field_name="game__platforms",
        queryset=plataformas_da_lista,
        label="Plataforma",
        empty_label="Todas",
    )

    class Meta:
        model = UserGameList
        fields = ["status", "genero", "plataforma"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form.fields["genero"].label_from_instance = lambda genero: traduzir_genero(genero.name)


class ReviewModerationFilter(django_filters.FilterSet):
    jogo = django_filters.CharFilter(
        field_name="game__title", lookup_expr="icontains", label="Jogo"
    )
    autor = django_filters.CharFilter(
        field_name="user__username", lookup_expr="icontains", label="Autor"
    )
    nota = django_filters.ChoiceFilter(
        field_name="rating", choices=Review.RATING_CHOICES, label="Nota", empty_label="Todas"
    )

    class Meta:
        model = Review
        fields = ["jogo", "autor", "nota"]
