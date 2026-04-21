from django.urls import path
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
    path(
        "game/<int:pk>/review/new/",
        views.ReviewCreateView.as_view(),
        name="create_review",
    ),
]
