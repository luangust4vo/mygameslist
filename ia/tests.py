from datetime import timedelta
from unittest.mock import patch

import requests
from django.contrib.auth.models import Group, User
from django.contrib.messages import get_messages
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from games.models import Game, UserGameList

from . import gemini
from .assistente import RECUSA, janela_de_mensagens, montar_instrucoes
from .models import ConfiguracaoIA, CotaUsuario, MensagemAssistente, RequisicaoIA
from .servicos import (
    CotaEsgotada,
    IADesativada,
    IAIndisponivel,
    RespostaIA,
    chamar_ia,
    consumo_do_mes,
    inicio_do_mes,
)

RESPOSTA_GEMINI = {
    "candidates": [
        {
            "content": {
                "parts": [
                    {"text": "pensando...", "thought": True},
                    {"text": "OK"},
                ]
            },
            "finishReason": "STOP",
        }
    ],
    "usageMetadata": {
        "promptTokenCount": 10,
        "candidatesTokenCount": 2,
        "thoughtsTokenCount": 30,
        "totalTokenCount": 42,
    },
}

RESULTADO_GERAR = {"texto": "OK", "motivo": "STOP", "tokens_entrada": 10, "tokens_saida": 32, "tokens_total": 42}


def mensagens(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


def requisicao(user, tokens, finalidade="assistente", status="sucesso"):
    return RequisicaoIA.objects.create(
        user=user, finalidade=finalidade, status=status, tokens_total=tokens
    )


@patch("ia.gemini.requests.post")
class ClienteGeminiTests(TestCase):
    def test_devolve_texto_sem_o_raciocinio_e_soma_tokens_de_raciocinio(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = RESPOSTA_GEMINI

        resultado = gemini.gerar("chave", "gemini-teste", [("user", "Oi")], instrucoes="Seja breve")

        self.assertEqual(resultado, RESULTADO_GERAR)
        args, kwargs = mock_post.call_args
        self.assertIn("/gemini-teste:generateContent", args[0])
        self.assertEqual(kwargs["headers"], {"x-goog-api-key": "chave"})
        self.assertEqual(kwargs["timeout"], 25)
        self.assertEqual(kwargs["json"]["systemInstruction"], {"parts": [{"text": "Seja breve"}]})
        self.assertEqual(kwargs["json"]["contents"], [{"role": "user", "parts": [{"text": "Oi"}]}])

    def test_erro_http_vira_erro_gemini_com_a_mensagem_da_api(self, mock_post):
        mock_post.return_value.status_code = 503
        mock_post.return_value.json.return_value = {"error": {"message": "high demand"}}

        with self.assertRaisesMessage(gemini.ErroGemini, "HTTP 503: high demand"):
            gemini.gerar("chave", "gemini-teste", [("user", "Oi")])

    def test_tempo_esgotado_vira_erro_gemini(self, mock_post):
        mock_post.side_effect = requests.Timeout

        with self.assertRaisesMessage(gemini.ErroGemini, "Tempo esgotado"):
            gemini.gerar("chave", "gemini-teste", [("user", "Oi")])

    def test_resposta_sem_texto_guarda_os_tokens_gastos(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "...", "thought": True}]}, "finishReason": "MAX_TOKENS"}],
            "usageMetadata": {"promptTokenCount": 5, "thoughtsTokenCount": 64, "totalTokenCount": 69},
        }

        with self.assertRaises(gemini.ErroGemini) as contexto:
            gemini.gerar("chave", "gemini-teste", [("user", "Oi")])

        self.assertIn("MAX_TOKENS", str(contexto.exception))
        self.assertEqual(contexto.exception.uso["tokens_total"], 69)


@override_settings(GEMINI_API_KEY="chave-teste")
@patch("ia.servicos.gemini.gerar", return_value=RESULTADO_GERAR)
class ChamarIATests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="senha12345")
        self.configuracao = ConfiguracaoIA.atual()
        self.configuracao.cota_mensal_padrao = 1000
        self.configuracao.save()

    def test_sucesso_registra_a_requisicao_com_os_tokens(self, mock_gerar):
        resposta = chamar_ia(self.alice, "assistente", "Qual o melhor RPG?")

        self.assertEqual(resposta.texto, "OK")
        self.assertFalse(resposta.cortada)
        registro = RequisicaoIA.objects.get()
        self.assertEqual(registro.status, "sucesso")
        self.assertEqual(registro.user, self.alice)
        self.assertEqual(registro.tokens_total, 42)
        self.assertEqual(registro.saida, "OK")
        self.assertIn("Qual o melhor RPG?", registro.entrada)

    def test_usa_modelo_temperatura_e_maximo_da_configuracao(self, mock_gerar):
        self.configuracao.modelo = "gemini-x"
        self.configuracao.temperatura = 0.3
        self.configuracao.max_tokens = 512
        self.configuracao.save()

        chamar_ia(self.alice, "assistente", [("user", "Oi"), ("model", "Olá"), ("user", "Tudo bem?")], instrucoes="Regras")

        args, kwargs = mock_gerar.call_args
        self.assertEqual(args[0], "chave-teste")
        self.assertEqual(args[1], "gemini-x")
        self.assertEqual(len(args[2]), 3)
        self.assertEqual(kwargs, {"instrucoes": "Regras", "temperatura": 0.3, "max_tokens": 512, "timeout": 25})

    def test_ia_desativada_bloqueia_sem_chamar_o_gemini(self, mock_gerar):
        self.configuracao.ativa = False
        self.configuracao.save()

        with self.assertRaisesMessage(IADesativada, "A IA está desativada no momento."):
            chamar_ia(self.alice, "assistente", "Oi")

        mock_gerar.assert_not_called()
        self.assertEqual(RequisicaoIA.objects.get().status, "bloqueada")

    def test_cota_esgotada_bloqueia_sem_chamar_o_gemini(self, mock_gerar):
        requisicao(self.alice, 1000)

        with self.assertRaisesMessage(CotaEsgotada, "Sua cota de IA deste mês acabou."):
            chamar_ia(self.alice, "assistente", "Oi")

        mock_gerar.assert_not_called()
        self.assertTrue(RequisicaoIA.objects.filter(status="bloqueada").exists())

    def test_limite_personalizado_vale_sobre_a_cota_padrao(self, mock_gerar):
        requisicao(self.alice, 1000)
        CotaUsuario.objects.create(user=self.alice, limite_mensal=5000)

        resposta = chamar_ia(self.alice, "assistente", "Oi")

        self.assertEqual(resposta.texto, "OK")

    def test_consumo_de_meses_anteriores_nao_conta(self, mock_gerar):
        antiga = requisicao(self.alice, 1000)
        RequisicaoIA.objects.filter(pk=antiga.pk).update(criada_em=inicio_do_mes() - timedelta(days=1))

        chamar_ia(self.alice, "assistente", "Oi")

        self.assertEqual(consumo_do_mes(self.alice), 42)

    def test_erro_do_gemini_vira_ia_indisponivel_e_fica_na_auditoria(self, mock_gerar):
        mock_gerar.side_effect = gemini.ErroGemini("HTTP 503: high demand", {"tokens_total": 7})

        with self.assertRaises(IAIndisponivel) as contexto:
            chamar_ia(self.alice, "assistente", "Oi")

        self.assertEqual(str(contexto.exception), "A IA está indisponível no momento. Tente de novo mais tarde.")
        self.assertEqual(contexto.exception.detalhe, "HTTP 503: high demand")
        registro = RequisicaoIA.objects.get()
        self.assertEqual((registro.status, registro.erro, registro.tokens_total), ("erro", "HTTP 503: high demand", 7))

    @override_settings(GEMINI_API_KEY="")
    def test_sem_chave_bloqueia_sem_chamar_o_gemini(self, mock_gerar):
        with self.assertRaisesMessage(IAIndisponivel, "A IA não está configurada."):
            chamar_ia(self.alice, "assistente", "Oi")

        mock_gerar.assert_not_called()

    def test_resposta_cortada_pelo_limite_de_tokens_e_sinalizada(self, mock_gerar):
        mock_gerar.return_value = {**RESULTADO_GERAR, "motivo": "MAX_TOKENS"}

        resposta = chamar_ia(self.alice, "traducao", "Translate")

        self.assertTrue(resposta.cortada)

    def test_chamada_do_sistema_nao_verifica_cota(self, mock_gerar):
        self.configuracao.cota_mensal_padrao = 0
        self.configuracao.save()

        resposta = chamar_ia(None, "traducao", "Translate")

        self.assertEqual(resposta.texto, "OK")
        self.assertIsNone(RequisicaoIA.objects.get().user)


class TelasIABase(TestCase):
    def setUp(self):
        self.moderador = User.objects.create_user("moderador", password="senha12345")
        self.moderador.groups.add(Group.objects.get(name="Moderador"))
        self.alice = User.objects.create_user("alice", password="senha12345")
        self.configuracao = ConfiguracaoIA.atual()


class AcessoTelasIATests(TelasIABase):
    def urls_do_moderador(self):
        return [
            reverse("ia:requisicoes"),
            reverse("ia:configuracao"),
            reverse("ia:usuarios"),
            reverse("ia:editar_cota", args=[self.alice.pk]),
        ]

    def test_anonimo_e_redirecionado_ao_login(self):
        for url in self.urls_do_moderador() + [reverse("ia:meu_consumo")]:
            response = self.client.get(url)

            self.assertEqual(response.status_code, 302, url)
            self.assertIn(reverse("games:login"), response.url)

    def test_jogador_comum_recebe_403_nas_telas_do_moderador(self):
        self.client.force_login(self.alice)

        for url in self.urls_do_moderador():
            self.assertEqual(self.client.get(url).status_code, 403, url)
        self.assertEqual(self.client.post(reverse("ia:testar_conexao")).status_code, 403)

    def test_moderador_abre_todas_as_telas(self):
        self.client.force_login(self.moderador)

        for url in self.urls_do_moderador():
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_menu_mostra_as_telas_de_ia_so_para_o_moderador(self):
        self.client.force_login(self.alice)
        jogador = self.client.get(reverse("games:home"))
        self.client.force_login(self.moderador)
        moderador = self.client.get(reverse("games:home"))

        self.assertContains(jogador, reverse("ia:meu_consumo"))
        self.assertNotContains(jogador, reverse("ia:configuracao"))
        self.assertContains(moderador, reverse("ia:configuracao"))
        self.assertContains(moderador, reverse("ia:requisicoes"))


class ConfiguracaoIATelaTests(TelasIABase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.moderador)
        self.url = reverse("ia:configuracao")

    def test_migration_cria_a_configuracao_padrao(self):
        self.assertTrue(ConfiguracaoIA.objects.filter(pk=1, modelo="gemini-flash-lite-latest").exists())

    def test_salvar_altera_a_configuracao(self):
        dados = {"modelo": "gemini-x", "temperatura": 0.2, "max_tokens": 1024, "cota_mensal_padrao": 5000}

        response = self.client.post(self.url, dados)

        self.assertRedirects(response, self.url)
        self.configuracao.refresh_from_db()
        self.assertEqual(self.configuracao.modelo, "gemini-x")
        self.assertFalse(self.configuracao.ativa)
        self.assertIn("Configuração da IA salva.", mensagens(response))
        self.assertEqual(ConfiguracaoIA.objects.count(), 1)

    def test_temperatura_fora_do_limite_nao_salva(self):
        dados = {"modelo": "gemini-x", "temperatura": 3, "max_tokens": 1024, "cota_mensal_padrao": 5000, "ativa": "on"}

        response = self.client.post(self.url, dados)

        self.assertEqual(response.status_code, 200)
        self.configuracao.refresh_from_db()
        self.assertEqual(self.configuracao.modelo, "gemini-flash-lite-latest")

    @patch("ia.views.chamar_ia")
    def test_testar_conexao_com_sucesso(self, mock_chamar):
        mock_chamar.return_value.texto = "OK"
        mock_chamar.return_value.tokens_total = 42

        response = self.client.post(reverse("ia:testar_conexao"))

        self.assertRedirects(response, self.url)
        self.assertEqual(mock_chamar.call_args.args[:2], (self.moderador, "teste"))
        self.assertIn("Conexão funcionando. O modelo respondeu “OK” usando 42 tokens.", mensagens(response))

    @patch("ia.views.chamar_ia", side_effect=IAIndisponivel("A IA está indisponível.", "HTTP 404: modelo inexistente"))
    def test_testar_conexao_com_falha_mostra_o_detalhe(self, mock_chamar):
        response = self.client.post(reverse("ia:testar_conexao"))

        self.assertIn(
            "O teste falhou. A IA está indisponível. Detalhe: HTTP 404: modelo inexistente",
            mensagens(response),
        )

    def test_testar_conexao_nao_aceita_get(self):
        self.assertEqual(self.client.get(reverse("ia:testar_conexao")).status_code, 405)


class RequisicoesTelaTests(TelasIABase):
    def test_filtra_por_finalidade_e_status(self):
        requisicao(self.alice, 10, finalidade="assistente")
        requisicao(self.alice, 20, finalidade="traducao")
        requisicao(self.alice, 0, finalidade="traducao", status="erro")
        self.client.force_login(self.moderador)

        response = self.client.get(reverse("ia:requisicoes"), {"finalidade": "traducao", "status": "erro"})

        self.assertEqual([r.tokens_total for r in response.context["requisicoes"]], [0])


class UsuariosIATelaTests(TelasIABase):
    def setUp(self):
        super().setUp()
        self.configuracao.cota_mensal_padrao = 1000
        self.configuracao.save()
        self.client.force_login(self.moderador)

    def test_mostra_consumo_do_mes_e_limite_de_cada_usuario(self):
        requisicao(self.alice, 300)
        antiga = requisicao(self.alice, 999)
        RequisicaoIA.objects.filter(pk=antiga.pk).update(criada_em=inicio_do_mes() - timedelta(days=2))
        CotaUsuario.objects.create(user=self.moderador, limite_mensal=5000)

        response = self.client.get(reverse("ia:usuarios"))

        usuarios = {u.username: (u.consumo_mes, u.limite) for u in response.context["usuarios"]}
        self.assertEqual(usuarios["alice"], (300, 1000))
        self.assertEqual(usuarios["moderador"], (0, 5000))

    def test_editar_cota_define_limite_personalizado(self):
        url = reverse("ia:editar_cota", args=[self.alice.pk])

        response = self.client.post(url, {"limite_mensal": 2500})

        self.assertRedirects(response, reverse("ia:usuarios"))
        self.assertEqual(self.alice.cota_ia.limite_mensal, 2500)
        self.assertIn("Cota de IA de alice atualizada.", mensagens(response))

    def test_limite_vazio_volta_para_a_cota_padrao(self):
        CotaUsuario.objects.create(user=self.alice, limite_mensal=2500)

        self.client.post(reverse("ia:editar_cota", args=[self.alice.pk]), {"limite_mensal": ""})

        self.alice.cota_ia.refresh_from_db()
        self.assertIsNone(self.alice.cota_ia.limite_mensal)

    def test_usuario_inexistente_da_404(self):
        self.assertEqual(self.client.get(reverse("ia:editar_cota", args=[9999])).status_code, 404)


class MeuConsumoTelaTests(TelasIABase):
    def test_mostra_so_o_consumo_e_as_requisicoes_do_proprio_usuario(self):
        self.configuracao.cota_mensal_padrao = 1000
        self.configuracao.save()
        requisicao(self.alice, 250)
        requisicao(self.moderador, 700)
        self.client.force_login(self.alice)

        response = self.client.get(reverse("ia:meu_consumo"))

        self.assertEqual([r.user for r in response.context["requisicoes"]], [self.alice])
        self.assertEqual(
            (response.context["usado"], response.context["limite"], response.context["restante"], response.context["percentual"]),
            (250, 1000, 750, 25),
        )

    def test_sem_requisicoes_mostra_aviso(self):
        self.client.force_login(self.alice)

        response = self.client.get(reverse("ia:meu_consumo"))

        self.assertContains(response, "Você ainda não usou a IA.")


AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


class IAFalsa:
    """Substitui chamar_ia no assistente: responde conforme a finalidade."""

    def __init__(self, classificacao="permitido", resposta="Experimente **Celeste**.", erro=None, erro_em=None):
        self.classificacao = classificacao
        self.resposta = resposta
        self.erro = erro
        self.erro_em = erro_em
        self.chamadas = []

    def __call__(self, user, finalidade, mensagens, **kwargs):
        self.chamadas.append({"user": user, "finalidade": finalidade, "mensagens": mensagens, **kwargs})
        if self.erro and self.erro_em == finalidade:
            raise self.erro
        texto = self.classificacao if finalidade == "classificacao" else self.resposta
        return RespostaIA(texto=texto, tokens_total=5, requisicao=None)

    def finalidades(self):
        return [chamada["finalidade"] for chamada in self.chamadas]


class AssistenteTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="senha12345")
        self.bob = User.objects.create_user("bob", password="senha12345")
        self.url = reverse("ia:perguntar")
        self.client.force_login(self.alice)

    def perguntar(self, ia, pergunta="O que jogo depois de Hollow Knight?", **extra):
        with patch("ia.assistente.chamar_ia", ia):
            return self.client.post(self.url, {"pergunta": pergunta}, **extra)

    def test_pergunta_por_ajax_classifica_responde_e_guarda_o_par(self):
        ia = IAFalsa()

        response = self.perguntar(ia, **AJAX)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["resposta_html"], "<p>Experimente <strong>Celeste</strong>.</p>")
        self.assertEqual(ia.finalidades(), ["classificacao", "assistente"])
        self.assertEqual(
            list(MensagemAssistente.objects.values_list("papel", "texto")),
            [("user", "O que jogo depois de Hollow Knight?"), ("model", "Experimente **Celeste**.")],
        )

    def test_classificacao_recebe_so_a_pergunta_e_tem_limite_curto(self):
        MensagemAssistente.objects.create(user=self.alice, papel="user", texto="Pergunta antiga")
        ia = IAFalsa()

        self.perguntar(ia, **AJAX)

        classificacao = ia.chamadas[0]
        self.assertEqual(classificacao["mensagens"], "O que jogo depois de Hollow Knight?")
        self.assertEqual((classificacao["timeout"], classificacao["temperatura"]), (10, 0))

    def test_pergunta_fora_do_escopo_e_recusada_sem_resposta_nem_historico(self):
        ia = IAFalsa(classificacao="fora")

        response = self.perguntar(ia, "Qual a capital da França?", **AJAX)

        self.assertEqual(response.json(), {"ok": False, "tipo": "recusa", "erro": RECUSA})
        self.assertEqual(ia.finalidades(), ["classificacao"])
        self.assertFalse(MensagemAssistente.objects.exists())

    def test_cota_esgotada_responde_429_e_nao_guarda(self):
        ia = IAFalsa(erro=CotaEsgotada("Sua cota de IA deste mês acabou."), erro_em="classificacao")

        response = self.perguntar(ia, **AJAX)

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["erro"], "Sua cota de IA deste mês acabou.")
        self.assertFalse(MensagemAssistente.objects.exists())

    def test_ia_fora_do_ar_na_resposta_responde_503_e_nao_guarda(self):
        ia = IAFalsa(erro=IAIndisponivel("A IA está indisponível no momento."), erro_em="assistente")

        response = self.perguntar(ia, **AJAX)

        self.assertEqual(response.status_code, 503)
        self.assertFalse(MensagemAssistente.objects.exists())

    def test_pergunta_vazia_ou_longa_demais_e_rejeitada_sem_chamar_a_ia(self):
        ia = IAFalsa()

        vazia = self.perguntar(ia, "   ", **AJAX)
        longa = self.perguntar(ia, "a" * 501, **AJAX)

        self.assertEqual((vazia.status_code, longa.status_code), (400, 400))
        self.assertEqual(vazia.json()["erro"], "Escreva uma pergunta.")
        self.assertEqual(longa.json()["erro"], "A pergunta pode ter no máximo 500 caracteres.")
        self.assertEqual(ia.chamadas, [])

    def test_janela_envia_so_as_ultimas_cinco_mensagens_comecando_pelo_usuario(self):
        for i in range(3):
            MensagemAssistente.objects.create(user=self.alice, papel="user", texto=f"pergunta {i}")
            MensagemAssistente.objects.create(user=self.alice, papel="model", texto=f"resposta {i}")
        MensagemAssistente.objects.create(user=self.bob, papel="user", texto="do bob")

        janela = janela_de_mensagens(self.alice, "nova")

        self.assertEqual(
            janela,
            [("user", "pergunta 1"), ("model", "resposta 1"), ("user", "pergunta 2"), ("model", "resposta 2"), ("user", "nova")],
        )

    def test_janela_nao_comeca_por_resposta_do_assistente(self):
        MensagemAssistente.objects.create(user=self.alice, papel="model", texto="sobrou")
        MensagemAssistente.objects.create(user=self.alice, papel="user", texto="pergunta")
        MensagemAssistente.objects.create(user=self.alice, papel="model", texto="resposta")

        self.assertEqual(janela_de_mensagens(self.alice, "nova")[0], ("user", "pergunta"))

    def test_instrucoes_tem_o_contexto_e_a_lista_do_proprio_usuario(self):
        celeste = Game.objects.create(rawg_id=1, title="Celeste")
        hades = Game.objects.create(rawg_id=2, title="Hades")
        UserGameList.objects.create(user=self.alice, game=celeste, status="completed")
        UserGameList.objects.create(user=self.bob, game=hades, status="playing")

        instrucoes = montar_instrucoes(self.alice)

        self.assertIn("Você é o assistente do MyGamesList", instrucoes)
        self.assertIn("- Celeste (Zerado)", instrucoes)
        self.assertNotIn("Hades", instrucoes)

    def test_lista_no_contexto_e_limitada_a_trinta_jogos(self):
        for i in range(35):
            UserGameList.objects.create(user=self.alice, game=Game.objects.create(rawg_id=i, title=f"Jogo {i}"))

        self.assertEqual(montar_instrucoes(self.alice).count("(Quero Jogar)"), 30)

    def test_resposta_e_sanitizada(self):
        ia = IAFalsa(resposta="Veja [lista](/minha-lista/) [x](javascript:alert(1)) <script>alert(1)</script>")

        html = self.perguntar(ia, **AJAX).json()["resposta_html"]

        self.assertIn('<a href="/minha-lista/" rel="nofollow noopener noreferrer">lista</a>', html)
        self.assertNotIn("javascript", html)
        self.assertNotIn("<script", html)

    def test_sem_javascript_o_formulario_volta_para_a_tela(self):
        ia = IAFalsa(classificacao="fora")

        response = self.perguntar(ia)

        self.assertRedirects(response, reverse("ia:assistente"))
        self.assertIn(RECUSA, mensagens(response))

    def test_post_sem_token_csrf_e_rejeitado(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.alice)

        with patch("ia.assistente.chamar_ia", IAFalsa()) as ia:
            response = cliente.post(self.url, {"pergunta": "Oi"}, **AJAX)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(ia.chamadas, [])

    def test_anonimo_e_redirecionado_ao_login(self):
        self.client.logout()

        for url in [reverse("ia:assistente"), self.url]:
            response = self.client.post(url, {"pergunta": "Oi"}) if url == self.url else self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("games:login"), response.url)


class TelaAssistenteTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="senha12345")
        self.bob = User.objects.create_user("bob", password="senha12345")
        self.client.force_login(self.alice)

    def test_mostra_so_o_historico_do_proprio_usuario_com_markdown_seguro(self):
        MensagemAssistente.objects.create(user=self.alice, papel="user", texto="<b>Oi</b>")
        MensagemAssistente.objects.create(user=self.alice, papel="model", texto="Olá, **Alice**! <script>x</script>")
        MensagemAssistente.objects.create(user=self.bob, papel="user", texto="Segredo do Bob")

        response = self.client.get(reverse("ia:assistente"))

        self.assertContains(response, "&lt;b&gt;Oi&lt;/b&gt;")
        self.assertContains(response, "Olá, <strong>Alice</strong>!")
        self.assertNotContains(response, "<script>x</script>")
        self.assertNotContains(response, "Segredo do Bob")

    def test_pagina_carrega_o_script_e_o_contador(self):
        response = self.client.get(reverse("ia:assistente"))

        self.assertContains(response, "js/assistente.js")
        self.assertContains(response, 'maxlength="500"')
        self.assertContains(response, "0/500")

    def test_limpar_conversa_apaga_so_as_mensagens_do_usuario(self):
        MensagemAssistente.objects.create(user=self.alice, papel="user", texto="Oi")
        MensagemAssistente.objects.create(user=self.bob, papel="user", texto="Oi")
        requisicao(self.alice, 10)

        response = self.client.post(reverse("ia:limpar_conversa"))

        self.assertRedirects(response, reverse("ia:assistente"))
        self.assertIn("Conversa apagada.", mensagens(response))
        self.assertEqual(list(MensagemAssistente.objects.values_list("user__username", flat=True)), ["bob"])
        self.assertEqual(RequisicaoIA.objects.count(), 1)

    def test_limpar_conversa_pede_confirmacao_e_nao_aceita_get(self):
        MensagemAssistente.objects.create(user=self.alice, papel="user", texto="Oi")

        pagina = self.client.get(reverse("ia:assistente"))

        self.assertContains(pagina, 'data-confirmar-titulo="Limpar conversa?"')
        self.assertEqual(self.client.get(reverse("ia:limpar_conversa")).status_code, 405)

    def test_menu_mostra_o_assistente_so_para_quem_esta_logado(self):
        logado = self.client.get(reverse("games:home"))
        self.client.logout()
        visitante = self.client.get(reverse("games:home"))

        self.assertContains(logado, f'href="{reverse("ia:assistente")}"')
        self.assertNotContains(visitante, f'href="{reverse("ia:assistente")}"')
