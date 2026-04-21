from django.views.generic import TemplateView, CreateView, View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import login
from django.urls import reverse_lazy
from django.contrib import messages
from .rawg import get
from .services import import_game
from .models import Game, Review
from .forms import ReviewForm


class HomeView(TemplateView):
    template_name = "games/home/home.html"


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
        return render(request, "games/game/details.html", {"game": game})


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
        return reverse_lazy("games:review_details", kwargs={"pk": self.object.pk})  # type: ignore

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["game"] = get_object_or_404(Game, pk=self.kwargs["pk"])
        context["title"] = "Nova Review"
        return context
