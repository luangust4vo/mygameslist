from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.contrib.messages import get_messages
from django.template import Context, Template
from django.test import RequestFactory, TestCase
from django.urls import reverse

import requests

from .models import Activity, Game, Genre, Platform, Review, UserGameList
from .templatetags.custom_filters import descricao, genero_pt
from .services import import_game
from .steam import get_description_pt


class DuplicateReviewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="jogador", password="senha123")
        self.game = Game.objects.create(rawg_id=1, title="Hollow Knight")
        UserGameList.objects.create(user=self.user, game=self.game, status="completed")
        self.review = Review.objects.create(
            user=self.user, game=self.game, rating=5, title="Primeira review"
        )
        self.client.login(username="jogador", password="senha123")
        self.create_url = reverse("games:create_review", kwargs={"pk": self.game.pk})
        self.edit_url = reverse(
            "games:edit_review",
            kwargs={"pk": self.game.pk, "review_pk": self.review.pk},
        )

    def test_post_duplicate_review_redirects_to_edit(self):
        response = self.client.post(
            self.create_url, {"title": "Segunda review", "rating": 3, "body": ""}
        )

        self.assertRedirects(response, self.edit_url)
        self.assertEqual(Review.objects.filter(user=self.user, game=self.game).count(), 1)
        mensagens = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("Você já avaliou este jogo. Edite sua review.", mensagens)

    def test_get_create_page_with_existing_review_redirects_to_edit(self):
        response = self.client.get(self.create_url)

        self.assertRedirects(response, self.edit_url)


class ReviewDeleteGetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="jogador", password="senha123")
        self.game = Game.objects.create(rawg_id=1, title="Hollow Knight")
        self.review = Review.objects.create(
            user=self.user, game=self.game, rating=5, title="Minha review"
        )
        self.client.login(username="jogador", password="senha123")
        self.delete_url = reverse(
            "games:delete_review",
            kwargs={"pk": self.game.pk, "review_pk": self.review.pk},
        )

    def test_get_redirects_to_game_reviews_without_deleting(self):
        response = self.client.get(self.delete_url)

        self.assertRedirects(
            response, reverse("games:reviews_list", kwargs={"pk": self.game.pk})
        )
        self.assertTrue(Review.objects.filter(pk=self.review.pk).exists())


class ImportGameAccessTests(TestCase):
    @patch("games.views.import_game")
    def test_anonymous_is_redirected_to_login_without_calling_rawg(self, mock_import):
        url = reverse("games:import_game", kwargs={"id": 3328})

        response = self.client.post(url)

        self.assertRedirects(response, f"{reverse('games:login')}?next={url}")
        mock_import.assert_not_called()


class ReviewRequiresGameInListTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="jogador", password="senha123")
        self.game = Game.objects.create(rawg_id=1, title="Hollow Knight")
        self.client.login(username="jogador", password="senha123")
        self.create_url = reverse("games:create_review", kwargs={"pk": self.game.pk})
        self.data = {"title": "Ótimo jogo", "rating": 5, "body": ""}

    def test_game_not_in_list_redirects_to_add_to_list(self):
        response = self.client.post(self.create_url, self.data)

        self.assertRedirects(
            response, reverse("games:add_to_list", kwargs={"pk": self.game.pk})
        )
        self.assertFalse(Review.objects.filter(user=self.user, game=self.game).exists())
        mensagens = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("Adicione o jogo à sua lista antes de avaliá-lo.", mensagens)

    def test_game_in_another_users_list_is_denied(self):
        outro = User.objects.create_user(username="outro", password="senha123")
        UserGameList.objects.create(user=outro, game=self.game, status="completed")

        response = self.client.post(self.create_url, self.data)

        self.assertRedirects(
            response, reverse("games:add_to_list", kwargs={"pk": self.game.pk})
        )
        self.assertFalse(Review.objects.filter(user=self.user).exists())

    def test_game_in_list_with_any_status_allows_review(self):
        for status, _ in UserGameList.STATUS_CHOICES:
            with self.subTest(status=status):
                Review.objects.filter(user=self.user).delete()
                UserGameList.objects.update_or_create(
                    user=self.user, game=self.game, defaults={"status": status}
                )

                response = self.client.post(self.create_url, self.data)

                review = Review.objects.get(user=self.user, game=self.game)
                self.assertRedirects(
                    response,
                    reverse(
                        "games:review_details",
                        kwargs={"pk": self.game.pk, "review_pk": review.pk},
                    ),
                )


class ReviewActivityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="jogador", password="senha123")
        self.game = Game.objects.create(rawg_id=1, title="Hollow Knight")
        UserGameList.objects.create(user=self.user, game=self.game, status="completed")
        self.client.login(username="jogador", password="senha123")
        self.create_url = reverse("games:create_review", kwargs={"pk": self.game.pk})

    def test_publishing_review_creates_reviewed_activity(self):
        self.client.post(self.create_url, {"title": "Ótimo jogo", "rating": 5, "body": ""})

        activity = Activity.objects.get(action="reviewed")
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.game, self.game)
        self.assertEqual(activity.detail, "Avaliou como Obra de Arte")

    def test_invalid_review_creates_no_activity(self):
        self.client.post(self.create_url, {"title": "", "rating": 5, "body": ""})

        self.assertFalse(Activity.objects.filter(action="reviewed").exists())


class BaseTemplateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="jogador", password="senha123")
        self.client.login(username="jogador", password="senha123")

    def test_username_link_points_to_password_change(self):
        response = self.client.get(reverse("games:home"))

        self.assertContains(response, f'href="{reverse("games:password_change")}"')
        self.assertNotContains(response, 'href="admin"')

    def test_error_message_renders_as_danger_alert(self):
        game = Game.objects.create(rawg_id=1, title="Hollow Knight")

        response = self.client.get(
            reverse("games:create_review", kwargs={"pk": game.pk}), follow=True
        )

        self.assertContains(response, "alert alert-danger")


RAWG_DETAILS = {
    "id": 9767,
    "name": "Hollow Knight",
    "description_raw": "A challenging adventure.",
    "background_image": "",
    "released": "2017-02-24",
    "rating": 4.4,
    "genres": [],
    "platforms": [],
}

RAWG_STORES = {
    "results": [
        {"id": 1, "store_id": 3, "url": "https://www.playstation.com/games/hollow-knight/"},
        {"id": 2, "store_id": 1, "url": "https://store.steampowered.com/app/367520/Hollow_Knight/"},
    ]
}


@patch("games.services.get_details", return_value=RAWG_DETAILS)
class ImportDescriptionPtTests(TestCase):
    @patch("games.services.get_description_pt", return_value="Uma aventura desafiadora.")
    @patch("games.services.get_stores", return_value=RAWG_STORES)
    def test_saves_steam_description(self, mock_stores, mock_steam, mock_details):
        game = import_game(9767)

        mock_stores.assert_called_once_with(9767)
        mock_steam.assert_called_once_with("367520")
        game.refresh_from_db()
        self.assertEqual(game.description_pt, "Uma aventura desafiadora.")
        self.assertEqual(game.description_pt_source, "steam")

    @patch("games.services.get_stores", return_value={"results": []})
    def test_prefers_rawg_html_description(self, mock_stores, mock_details):
        mock_details.return_value = {
            **RAWG_DETAILS,
            "description": '<h3>Story</h3><p style="x">A challenging <a href="#">adventure</a>.</p>',
        }

        game = import_game(9767)

        self.assertEqual(game.description, "<h3>Story</h3><p>A challenging adventure.</p>")

    @patch("games.services.get_description_pt")
    @patch("games.services.get_stores", return_value={"results": [{"url": "https://www.gog.com/game/x"}]})
    def test_without_steam_link_keeps_description_empty(self, mock_stores, mock_steam, mock_details):
        game = import_game(9767)

        mock_steam.assert_not_called()
        self.assertEqual(game.description_pt, "")
        self.assertEqual(game.description_pt_source, "")

    @patch("games.services.get_stores", side_effect=requests.Timeout)
    def test_stores_failure_does_not_break_import(self, mock_stores, mock_details):
        with self.assertLogs("games.services", level="ERROR"):
            game = import_game(9767)

        self.assertIsNotNone(game)
        self.assertTrue(Game.objects.filter(rawg_id=9767).exists())
        self.assertEqual(game.description_pt, "")

    @patch("games.services.get_description_pt", return_value=None)
    @patch("games.services.get_stores", return_value=RAWG_STORES)
    def test_steam_without_description_keeps_empty(self, mock_stores, mock_steam, mock_details):
        game = import_game(9767)

        self.assertEqual(game.description_pt, "")
        self.assertEqual(game.description_pt_source, "")


class SteamDescriptionTests(TestCase):
    def steam_response(self, mock_get, data):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"367520": {"success": True, "data": data}}

    @patch("games.steam.requests.get")
    def test_returns_sanitized_html(self, mock_get):
        self.steam_response(mock_get, {
            "detailed_description": (
                '<h1>Sobre</h1><p class="bb_paragraph">Explore &amp; <a href="https://x.y">lute</a></p>'
                '<img src="https://x.y/a.png"><ul class="bb_ul"><li>Chefes</li></ul>'
                '<iframe src="https://x.y"></iframe><script>alert(1)</script>'
            ),
        })

        description = get_description_pt(367520)

        self.assertEqual(description, "<h2>Sobre</h2><p>Explore &amp; lute</p><ul><li>Chefes</li></ul>")
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["l"], "brazilian")
        self.assertEqual(kwargs["params"]["cc"], "br")
        self.assertEqual(kwargs["timeout"], 10)

    @patch("games.steam.requests.get")
    def test_uses_short_description_when_there_are_no_paragraphs(self, mock_get):
        self.steam_response(mock_get, {
            "detailed_description": "Explore o reino.<br>Lute contra chefes.",
            "short_description": "Um metroidvania &amp; muito mais.",
        })

        description = get_description_pt(367520)

        self.assertEqual(
            description,
            "<p>Um metroidvania &amp; muito mais.</p>Explore o reino.<br>Lute contra chefes.",
        )

    @patch("games.steam.requests.get")
    def test_returns_none_when_not_successful(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"367520": {"success": False}}

        self.assertIsNone(get_description_pt(367520))

    @patch("games.steam.requests.get", side_effect=requests.ConnectionError)
    def test_returns_none_on_network_error(self, mock_get):
        self.assertIsNone(get_description_pt(367520))

    @patch("games.steam.requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        mock_get.return_value.status_code = 500

        self.assertIsNone(get_description_pt(367520))


class GameDescriptionDisplayTests(TestCase):
    def test_shows_portuguese_description(self):
        game = Game.objects.create(
            rawg_id=1,
            title="Hollow Knight",
            description="A challenging adventure.",
            description_pt="Uma aventura desafiadora.",
            description_pt_source="steam",
        )

        response = self.client.get(reverse("games:game_details", kwargs={"pk": game.pk}))

        self.assertContains(response, "Uma aventura desafiadora.")
        self.assertNotContains(response, "A challenging adventure.")
        self.assertNotContains(response, "Descrição original em inglês")

    def test_description_block_is_keyboard_accessible(self):
        game = Game.objects.create(
            rawg_id=1, title="Hollow Knight", description_pt="<p>Uma aventura.</p>"
        )

        response = self.client.get(reverse("games:game_details", kwargs={"pk": game.pk}))

        self.assertContains(
            response,
            '<div class="descricao-jogo" tabindex="0" role="region" aria-label="Descrição do jogo">',
        )

    def test_original_description_block_is_marked_as_english(self):
        game = Game.objects.create(rawg_id=1, title="Hollow Knight", description="<p>An adventure.</p>")

        response = self.client.get(reverse("games:game_details", kwargs={"pk": game.pk}))

        self.assertContains(response, 'class="descricao-jogo" lang="en"')

    def test_falls_back_to_original_with_notice(self):
        game = Game.objects.create(
            rawg_id=1, title="Hollow Knight", description="A challenging adventure."
        )

        response = self.client.get(reverse("games:game_details", kwargs={"pk": game.pk}))

        self.assertContains(response, "A challenging adventure.")
        self.assertContains(response, "Descrição original em inglês")



class DescricaoFilterTests(TestCase):
    def test_keeps_allowed_structure(self):
        html = descricao("<h2>Sobre</h2><h3>Modos</h3><p><strong>Forte</strong> e <em>leve</em></p><ul><li>Item</li></ul>")

        self.assertEqual(
            html,
            "<h2>Sobre</h2><h3>Modos</h3><p><strong>Forte</strong> e <em>leve</em></p><ul><li>Item</li></ul>",
        )

    def test_removes_scripts_images_attributes_and_links(self):
        html = descricao(
            '<p class="a" style="color:red" onclick="x()">Texto <a href="https://x.y">link</a></p>'
            '<p><img src="https://x.y/a.png"></p><script>alert(1)</script>'
        )

        self.assertEqual(html, "<p>Texto link</p>")

    def test_plain_text_becomes_paragraphs(self):
        html = descricao("Primeiro parágrafo.\n\nSegundo **parágrafo**.")

        self.assertEqual(html, "<p>Primeiro parágrafo.</p>\n<p>Segundo <strong>parágrafo</strong>.</p>")

    def test_markdown_becomes_allowed_html(self):
        html = descricao("# Título\n\n- Item\n\n[link](https://x.y) e ![img](https://x.y/a.png)")

        self.assertEqual(html, "<h2>Título</h2>\n<ul>\n<li>Item</li>\n</ul>\n<p>link e </p>")


class GeneroPtFilterTests(TestCase):
    def test_translates_known_genre(self):
        self.assertEqual(genero_pt(Genre(rawg_id=4, name="Action")), "Ação")
        self.assertEqual(genero_pt("Massively Multiplayer"), "Multijogador massivo")

    def test_keeps_original_name_without_translation(self):
        self.assertEqual(genero_pt("Metroidvania"), "Metroidvania")

    def test_game_page_shows_translated_genres(self):
        game = Game.objects.create(rawg_id=1, title="Hollow Knight")
        game.genres.add(
            Genre.objects.create(rawg_id=4, name="Action"),
            Genre.objects.create(rawg_id=999, name="Metroidvania"),
        )

        response = self.client.get(reverse("games:game_details", kwargs={"pk": game.pk}))

        self.assertContains(response, '<span class="mgl-tag">Ação</span>', html=True)
        self.assertContains(response, '<span class="mgl-tag">Metroidvania</span>', html=True)
        self.assertNotContains(response, '<span class="mgl-tag">Action</span>', html=True)


class HomeFeaturedGamesTests(TestCase):
    def setUp(self):
        self.action = Genre.objects.create(rawg_id=4, name="Action")
        self.witcher = Game.objects.create(rawg_id=1, title="The Witcher 3", rawg_rating=4.6)
        self.witcher.genres.add(self.action)
        self.portal = Game.objects.create(rawg_id=2, title="Portal 2", rawg_rating=4.5)
        self.unrated = Game.objects.create(rawg_id=3, title="Sem Nota", rawg_rating=0)

    def test_visitor_sees_featured_games_ordered_by_rawg_rating(self):
        response = self.client.get(reverse("games:home"))

        self.assertContains(response, "Jogos em destaque")
        self.assertEqual(list(response.context["featured_games"]), [self.witcher, self.portal])
        self.assertContains(response, "Ação")

    def test_logged_user_sees_featured_games(self):
        User.objects.create_user(username="jogador", password="senha123")
        self.client.login(username="jogador", password="senha123")

        response = self.client.get(reverse("games:home"))

        self.assertContains(response, "Jogos em destaque")
        self.assertContains(response, "The Witcher 3")

    def test_featured_games_limited_to_six(self):
        for i in range(10, 17):
            Game.objects.create(rawg_id=i, title=f"Jogo {i}", rawg_rating=4.0)

        response = self.client.get(reverse("games:home"))

        self.assertEqual(len(response.context["featured_games"]), 6)

    def test_genres_are_prefetched(self):
        for i in range(10, 14):
            Game.objects.create(rawg_id=i, title=f"Jogo {i}", rawg_rating=4.0).genres.add(self.action)

        response = self.client.get(reverse("games:home"))

        with self.assertNumQueries(0):
            for game in response.context["featured_games"]:
                list(game.genres.all())

    def test_hides_top_rated_section_without_local_ratings(self):
        response = self.client.get(reverse("games:home"))

        self.assertNotContains(response, "Mais bem avaliados")

    def test_shows_top_rated_section_with_local_ratings(self):
        user = User.objects.create_user(username="jogador", password="senha123")
        Review.objects.create(user=user, game=self.witcher, rating=5, title="Ótimo")
        Review.objects.create(user=user, game=self.portal, rating=4, title="Bom")

        response = self.client.get(reverse("games:home"))

        self.assertContains(response, "Mais bem avaliados")

    def test_hides_featured_section_with_empty_catalog(self):
        Game.objects.all().delete()

        response = self.client.get(reverse("games:home"))

        self.assertNotContains(response, "Jogos em destaque")


class ModeradorGroupMigrationTests(TestCase):
    def test_moderador_group_exists_after_migrations(self):
        self.assertTrue(Group.objects.filter(name="Moderador").exists())


class MinhaListaFiltroTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="senha12345")
        self.bob = User.objects.create_user("bob", password="senha12345")
        self.acao = Genre.objects.create(rawg_id=4, name="Action")
        self.rpg = Genre.objects.create(rawg_id=5, name="RPG")
        self.estrategia = Genre.objects.create(rawg_id=10, name="Strategy")
        self.pc = Platform.objects.create(rawg_id=4, name="PC")
        self.ps5 = Platform.objects.create(rawg_id=187, name="PlayStation 5")

        self.witcher = Game.objects.create(rawg_id=1, title="The Witcher 3")
        self.witcher.genres.add(self.acao, self.rpg)
        self.witcher.platforms.add(self.pc)
        self.portal = Game.objects.create(rawg_id=2, title="Portal 2")
        self.portal.genres.add(self.acao)
        self.portal.platforms.add(self.ps5)
        self.celeste = Game.objects.create(rawg_id=3, title="Celeste")
        self.xcom = Game.objects.create(rawg_id=4, title="XCOM 2")
        self.xcom.genres.add(self.estrategia)

        UserGameList.objects.create(user=self.alice, game=self.witcher, status="completed")
        UserGameList.objects.create(user=self.alice, game=self.portal, status="playing")
        UserGameList.objects.create(user=self.alice, game=self.celeste, status="wishlist")
        UserGameList.objects.create(user=self.bob, game=self.xcom, status="dropped")

        self.url = reverse("games:my_list")
        self.client.force_login(self.alice)

    def titulos(self, response):
        return {item.game.title for item in response.context["items"]}

    def test_anonimo_e_redirecionado_ao_login(self):
        self.client.logout()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("games:login"), response.url)

    def test_sem_filtro_mostra_so_os_itens_do_usuario(self):
        response = self.client.get(self.url)

        self.assertEqual(self.titulos(response), {"The Witcher 3", "Portal 2", "Celeste"})

    def test_filtro_por_status_mostra_so_esse_status(self):
        response = self.client.get(self.url, {"status": "completed"})

        self.assertEqual(self.titulos(response), {"The Witcher 3"})

    def test_filtro_por_genero_mostra_jogos_do_genero(self):
        response = self.client.get(self.url, {"genero": self.acao.pk})

        self.assertEqual(self.titulos(response), {"The Witcher 3", "Portal 2"})

    def test_filtro_por_plataforma_mostra_jogos_da_plataforma(self):
        response = self.client.get(self.url, {"plataforma": self.ps5.pk})

        self.assertEqual(self.titulos(response), {"Portal 2"})

    def test_filtros_combinados_se_somam(self):
        response = self.client.get(self.url, {"genero": self.acao.pk, "status": "playing"})

        self.assertEqual(self.titulos(response), {"Portal 2"})

    def test_opcoes_de_genero_sao_so_da_lista_do_usuario(self):
        response = self.client.get(self.url)

        opcoes = set(response.context["filter"].form.fields["genero"].queryset)
        self.assertEqual(opcoes, {self.acao, self.rpg})

    def test_genero_do_outro_usuario_e_rejeitado(self):
        response = self.client.get(self.url, {"genero": self.estrategia.pk})

        self.assertEqual(self.titulos(response), set())

    def test_generos_aparecem_traduzidos_no_filtro(self):
        response = self.client.get(self.url)

        self.assertContains(response, f'<option value="{self.acao.pk}">Ação</option>', html=True)

    def test_filtro_sem_resultado_mostra_aviso(self):
        response = self.client.get(self.url, {"status": "platinum"})

        self.assertContains(response, "Nenhum jogo da sua lista combina com esses filtros.")

    def test_botao_limpar_so_aparece_com_filtro_preenchido(self):
        sem_filtro = self.client.get(self.url, {"page": 1})
        com_filtro = self.client.get(self.url, {"status": "completed"})

        self.assertNotContains(sem_filtro, ">Limpar</a>")
        self.assertContains(com_filtro, ">Limpar</a>")

    def test_lista_vazia_nao_mostra_filtros(self):
        UserGameList.objects.filter(user=self.alice).delete()

        response = self.client.get(self.url)

        self.assertContains(response, "Sua lista está vazia")
        self.assertNotContains(response, 'aria-label="Filtrar minha lista"')

    def test_paginacao_preserva_filtros(self):
        for i in range(10, 23):
            jogo = Game.objects.create(rawg_id=i, title=f"Jogo {i}")
            UserGameList.objects.create(user=self.alice, game=jogo, status="completed")

        response = self.client.get(self.url, {"status": "completed"})

        self.assertEqual(response.context["page_obj"].paginator.count, 14)
        self.assertContains(response, 'href="?status=completed&amp;page=2"')


class PainelModeracaoFiltroTests(TestCase):
    def setUp(self):
        self.moderador = User.objects.create_user("moderador", password="senha12345")
        self.moderador.groups.add(Group.objects.get(name="Moderador"))
        self.alice = User.objects.create_user("alice", password="senha12345")
        self.bob = User.objects.create_user("bob", password="senha12345")
        self.witcher = Game.objects.create(rawg_id=1, title="The Witcher 3")
        self.portal = Game.objects.create(rawg_id=2, title="Portal 2")

        Review.objects.create(user=self.alice, game=self.witcher, rating=5, title="Obra-prima")
        Review.objects.create(user=self.alice, game=self.portal, rating=1, title="Não gostei")
        Review.objects.create(user=self.bob, game=self.witcher, rating=1, title="Longo demais")

        self.url = reverse("games:moderation_panel")
        self.client.force_login(self.moderador)

    def titulos(self, response):
        return {review.title for review in response.context["reviews"]}

    def test_jogador_comum_recebe_403(self):
        self.client.force_login(self.alice)

        response = self.client.get(self.url, {"nota": 1})

        self.assertEqual(response.status_code, 403)

    def test_anonimo_e_redirecionado_ao_login(self):
        self.client.logout()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("games:login"), response.url)

    def test_filtro_por_jogo_ignora_maiusculas_e_aceita_parte_do_nome(self):
        response = self.client.get(self.url, {"jogo": "witcher"})

        self.assertEqual(self.titulos(response), {"Obra-prima", "Longo demais"})

    def test_filtro_por_autor(self):
        response = self.client.get(self.url, {"autor": "bob"})

        self.assertEqual(self.titulos(response), {"Longo demais"})

    def test_filtro_por_nota(self):
        response = self.client.get(self.url, {"nota": 1})

        self.assertEqual(self.titulos(response), {"Não gostei", "Longo demais"})

    def test_filtros_combinados_se_somam(self):
        response = self.client.get(self.url, {"nota": 1, "autor": "alice"})

        self.assertEqual(self.titulos(response), {"Não gostei"})

    def test_filtro_sem_resultado_mostra_aviso(self):
        response = self.client.get(self.url, {"autor": "ninguem"})

        self.assertContains(response, "Nenhuma review combina com esses filtros.")

    def test_paginacao_preserva_filtros(self):
        for i in range(10, 31):
            jogo = Game.objects.create(rawg_id=i, title=f"Jogo {i}")
            Review.objects.create(user=self.bob, game=jogo, rating=0, title=f"Ruim {i}")

        response = self.client.get(self.url, {"autor": "bob", "nota": 0})

        self.assertEqual(response.context["page_obj"].paginator.count, 21)
        self.assertContains(response, 'href="?autor=bob&amp;nota=0&amp;page=2"')


class UrlPaginaTagTests(TestCase):
    def renderizar(self, query_string):
        request = RequestFactory().get(f"/?{query_string}")
        template = Template("{% load custom_filters %}{% url_pagina 3 %}")
        return template.render(Context({"request": request}))

    def test_mantem_filtros_e_troca_a_pagina(self):
        self.assertEqual(self.renderizar("status=completed&page=1"), "?status=completed&amp;page=3")

    def test_sem_filtros_gera_so_a_pagina(self):
        self.assertEqual(self.renderizar(""), "?page=3")
