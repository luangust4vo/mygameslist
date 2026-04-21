from django.urls import path
from . import views

app_name = 'games'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('search/', views.SearchGameView.as_view(), name='search'),
    path('games/<int:pk>/', views.GameDetailsView.as_view(), name='game_details'),
    path('games/importar/<int:id>/', views.ImportGamesView.as_view(), name='import_game'),
]