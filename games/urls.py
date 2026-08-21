from django.urls import path
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from . import views

app_name = "games"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("auth/login/", views.CustomLoginView.as_view(), name="login"),
    path("auth/logout/", views.CustomLogoutView.as_view(), name="logout"),
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("game/search/", views.SearchGameView.as_view(), name="search"),
    path("game/<int:pk>/", views.GameDetailsView.as_view(), name="game_details"),
    path("game/import/<int:id>/", views.ImportGamesView.as_view(), name="import_game"),
    path("game/<int:pk>/reviews/", views.ReviewListView.as_view(), name="reviews_list"),
    path(
        "game/<int:pk>/reviews/<int:review_pk>/",
        views.ReviewDetailView.as_view(),
        name="review_details",
    ),
    path(
        "game/<int:pk>/reviews/new/",
        views.ReviewCreateView.as_view(),
        name="create_review",
    ),
    path(
        "game/<int:pk>/reviews/<int:review_pk>/edit/",
        views.ReviewUpdateView.as_view(),
        name="edit_review",
    ),
    path(
        "game/<int:pk>/reviews/<int:review_pk>/delete/",
        views.ReviewDeleteView.as_view(),
        name="delete_review",
    ),
    path(
        "auth/senha/alterar/",
        auth_views.PasswordChangeView.as_view(
            template_name="games/auth/password_change.html",
            success_url=reverse_lazy("games:password_change_done"),
        ),
        name="password_change",
    ),
    path(
        "auth/senha/alterada/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="games/auth/password_change_done.html"
        ),
        name="password_change_done",
    ),
]
