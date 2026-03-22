from django.urls import path
from . import views

app_name = 'games'

urlpatterns = [
    # home
    path('', views.HomeView.as_view(), name='home'),
]