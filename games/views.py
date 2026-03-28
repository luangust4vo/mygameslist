from django.views.generic import TemplateView, CreateView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.urls import reverse_lazy
from django.contrib import messages

class HomeView(TemplateView):
    template_name = 'games/home/home.html'

class CustomLoginView(LoginView):
    template_name = 'games/auth/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        messages.success(self.request, f'Bem-vindo, {self.request.user.username}!')
        return reverse_lazy('games:home')

    def form_invalid(self, form):
        messages.error(self.request, 'Usuário ou senha incorretos.')
        return super().form_invalid(form)
    
class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('games:home')
    
class RegisterView(CreateView):
    template_name = 'games/auth/register.html'
    form_class = UserCreationForm
    success_url = reverse_lazy('games:home')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.save()
        login(self.request, user)
        messages.success(self.request, 'Cadastro realizado com sucesso!')
        return response