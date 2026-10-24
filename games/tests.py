from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from .models import Activity, Game, Review, UserGameList


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
