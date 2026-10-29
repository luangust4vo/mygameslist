from django.urls import path

from . import views

app_name = "ia"

urlpatterns = [
    path("ia/requisicoes/", views.RequisicaoListView.as_view(), name="requisicoes"),
    path("ia/configuracao/", views.ConfiguracaoUpdateView.as_view(), name="configuracao"),
    path("ia/configuracao/testar/", views.TestarConexaoView.as_view(), name="testar_conexao"),
    path("ia/usuarios/", views.UsuarioIAListView.as_view(), name="usuarios"),
    path("ia/usuarios/<int:pk>/cota/", views.CotaUsuarioUpdateView.as_view(), name="editar_cota"),
    path("ia/meu-consumo/", views.MeuConsumoView.as_view(), name="meu_consumo"),
    path("assistente/", views.AssistenteView.as_view(), name="assistente"),
    path("assistente/perguntar/", views.PerguntarView.as_view(), name="perguntar"),
    path("assistente/limpar/", views.LimparConversaView.as_view(), name="limpar_conversa"),
]
