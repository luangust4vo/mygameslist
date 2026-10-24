from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from .models import Game, Review, UserGameList


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
