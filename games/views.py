from .mixins import GroupRequiredMixin
from django.views.generic import (
    TemplateView,
    CreateView,
    ListView,
    UpdateView,
    DetailView,
    DeleteView,
    View,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import login
from django.urls import reverse_lazy
from django.contrib import messages
from .rawg import get
from .services import import_game
from .models import Game, Review, UserGameList, Activity
from .forms import ReviewForm, UserGameListForm


class HomeView(TemplateView):
    template_name = "games/home/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["recent_activities"] = Activity.objects.select_related(
            "user", "game"
        ).order_by("-created_at")[:8]
        context["top_rated_games"] = Game.objects.filter(local_rating__gt=0).order_by(
            "-local_rating"
        )[:6]
        context["recent_games"] = Game.objects.order_by("-id")[:6]
        return context


class CustomLoginView(LoginView):
    template_name = "games/auth/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        messages.success(self.request, f"Bem-vindo, {self.request.user.username}!")
        return reverse_lazy("games:home")

    def form_invalid(self, form):
        messages.error(self.request, "Usuário ou senha incorretos.")
        return super().form_invalid(form)


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy("games:home")


class RegisterView(CreateView):
    template_name = "games/auth/register.html"
    form_class = UserCreationForm
    success_url = reverse_lazy("games:home")

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.save()
        login(self.request, user)
        messages.success(self.request, "Cadastro realizado com sucesso!")
        return response


class SearchGameView(View):
    def get(self, request):
        query = request.GET.get("q", "").strip()
        results = None

        if query:
            data = get(query)
            results = data.get("results", []) if data else []

        return render(
            request,
            "games/game/search.html",
            {
                "results": results,
                "query": query,
            },
        )


class ImportGamesView(View):
    def post(self, request, id):
        game = import_game(id)
        if game:
            return redirect("games:game_details", pk=game.pk)
        messages.error(request, "Não foi possível importar o game.")
        return redirect("games:search")


class GameDetailsView(View):
    def get(self, request, pk):
        game = get_object_or_404(Game, pk=pk)
        context = {"game": game}
        if request.user.is_authenticated:
            context["user_list_item"] = UserGameList.objects.filter(
                user=request.user, game=game
            ).first()
        return render(request, "games/game/details.html", context)


class ReviewListView(ListView):
    model = Review
    template_name = "review/list.html"
    context_object_name = "reviews"
    paginate_by = 10

    def get_queryset(self):
        self.jogo = get_object_or_404(Game, pk=self.kwargs["pk"])
        return Review.objects.filter(game=self.jogo).select_related("user", "game")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = self.jogo
        return context


class ReviewDetailView(DetailView):
    model = Review
    template_name = "review/details.html"
    context_object_name = "review"
    pk_url_kwarg = "review_pk"

    def get_queryset(self):
        return Review.objects.filter(game_id=self.kwargs["pk"])


class ReviewCreateView(LoginRequiredMixin, CreateView):
    model = Review
    form_class = ReviewForm
    template_name = "games/review/form.html"

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.game = get_object_or_404(Game, pk=self.kwargs["pk"])
        messages.success(self.request, "Review publicada com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("games:review_details", kwargs={"pk": self.object.game.pk, "review_pk": self.object.pk})  # type: ignore

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = get_object_or_404(Game, pk=self.kwargs["pk"])
        context["title"] = "Nova Review"
        return context


class ReviewUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Review
    form_class = ReviewForm
    template_name = "games/review/form.html"
    pk_url_kwarg = "review_pk"

    def test_func(self):
        review = self.get_object()
        return self.request.user == review.user  # type: ignore

    def form_valid(self, form):
        messages.success(self.request, "Review atualizada com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("games:review_details", kwargs={"pk": self.object.game.pk, "review_pk": self.object.pk})  # type: ignore

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = self.object.game  # type: ignore
        context["title"] = "Editar Review"
        return context


class ReviewDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Review
    context_object_name = "review"
    pk_url_kwarg = "review_pk"

    def get(self):
        return redirect("games:reviews_list")

    def test_func(self):
        review = self.get_object()
        user = self.request.user
        return user == review.user or user.groups.filter(name="Moderador").exists()

    def get_success_url(self):
        messages.success(self.request, "Review excluída.")
        return reverse_lazy("games:reviews_list", kwargs={"pk": self.object.game.pk})  # type: ignore


class MyGameListView(LoginRequiredMixin, ListView):
    model = UserGameList
    template_name = "games/list/user_games_list.html"
    context_object_name = "items"
    paginate_by = 12

    def get_queryset(self):
        return UserGameList.objects.filter(user=self.request.user).select_related(
            "game"
        )


class AddToListView(LoginRequiredMixin, CreateView):
    model = UserGameList
    form_class = UserGameListForm
    template_name = "games/list/manage_item_list.html"

    def dispatch(self, request, *args, **kwargs):
        self.game = get_object_or_404(Game, pk=self.kwargs["pk"])
        existing = UserGameList.objects.filter(
            user=request.user, game=self.game
        ).first()
        if existing:
            return redirect("games:edit_list_item", pk=existing.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.game = self.game
        response = super().form_valid(form)
        Activity.objects.create(
            user=self.request.user,
            game=self.game,
            action="added",
            detail=f"Adicionou à lista como {self.object.get_status_display()}",  # type: ignore
        )
        messages.success(self.request, "Jogo adicionado à sua lista!")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = self.game
        context["title"] = "Adicionar à minha lista"
        return context

    def get_success_url(self):
        return reverse_lazy("games:my_list")


class EditListItemView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = UserGameList
    form_class = UserGameListForm
    template_name = "games/list/manage_item_list.html"

    def test_func(self):
        return self.request.user == self.get_object().user

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.object.status in UserGameList.STATUSES_THAT_TRIGGER:  # type: ignore
            Activity.objects.create(
                user=self.request.user,
                game=self.object.game,  # type: ignore
                action="status",
                detail=f"Mudou o status para {self.object.get_status_display()}",  # type: ignore
            )
        messages.success(self.request, "Status atualizado!")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = self.object.game  # type: ignore
        context["title"] = "Atualizar status"
        return context

    def get_success_url(self):
        return reverse_lazy("games:my_list")


class RemoveFromListView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = UserGameList
    context_object_name = "item"
    template_name = "games/list/confirm_delete_item_list.html"

    def test_func(self):
        return self.request.user == self.get_object().user

    def get_success_url(self):
        Activity.objects.create(
            user=self.request.user,
            game=self.object.game,  # type: ignore
            action="removed",
            detail="Removeu da lista",
        )
        messages.success(self.request, "Jogo removido da sua lista.")
        return reverse_lazy("games:my_list")


class ModerationPanelView(LoginRequiredMixin, GroupRequiredMixin, ListView):
    model = Review
    template_name = "games/moderation/panel.html"
    context_object_name = "reviews"
    group_required = "Moderador"
    paginate_by = 20

    def get_queryset(self):
        return Review.objects.select_related("user", "game").order_by("-created_at")
