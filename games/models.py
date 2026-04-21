from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg


class Genre(models.Model):
    rawg_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]
        verbose_name = "Gênero"
        verbose_name_plural = "Gêneros"

    def __str__(self):
        return self.name


class Platform(models.Model):
    rawg_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]
        verbose_name = "Plataforma"
        verbose_name_plural = "Plataformas"

    def __str__(self):
        return self.name


class Game(models.Model):
    rawg_id = models.IntegerField(unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    cover_url = models.URLField(blank=True, default="")
    release_date = models.DateField(null=True, blank=True)
    rawg_rating = models.FloatField(default=0)
    local_rating = models.FloatField(default=0)
    genres = models.ManyToManyField(Genre, blank=True)
    platforms = models.ManyToManyField(Platform, blank=True)

    class Meta:
        ordering = ["title"]
        verbose_name = "Jogo"
        verbose_name_plural = "Jogos"

    def __str__(self):
        return self.title

    def update_local_rating(self):
        avg = Review.objects.filter(game=self).aggregate(Avg("rating"))["rating__avg"]
        self.local_rating = round(avg, 2) if avg is not None else 0
        self.save()


class UserGameList(models.Model):
    STATUS_CHOICES = [
        ("wishlist", "Quero Jogar"),
        ("playing", "Jogando"),
        ("paused", "Pausado"),
        ("completed", "Zerado"),
        ("platinum", "Platinado"),
        ("dropped", "Dropado"),
    ]

    STATUSES_THAT_TRIGGER = ["completed", "platinum", "dropped"]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="wishlist")
    date_added = models.DateField(auto_now_add=True)
    date_updated = models.DateField(auto_now=True)

    class Meta:
        unique_together = ("user", "game")
        ordering = ["-date_added"]
        verbose_name = "Lista"
        verbose_name_plural = "Listas"

    def __str__(self):
        return f"{self.user.username} — {self.game.title} ({self.get_status_display()})"  # type: ignore


class Review(models.Model):
    RATING_CHOICES = [
        (0, "Podre"),
        (1, "Ruim"),
        (2, "Meh"),
        (3, "Bom"),
        (4, "Muito Bom"),
        (5, "Obra de Arte"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=RATING_CHOICES, verbose_name="Avaliação")
    title = models.CharField(max_length=255, verbose_name="Título")
    body = models.TextField(blank=True, default="", verbose_name="Comentário")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "game")
        ordering = ["-created_at"]
        verbose_name = "Review"
        verbose_name_plural = "Reviews"

    def __str__(self):
        return f"{self.user.username} — {self.game.title}: {self.get_rating_display()}"  # type: ignore

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.game.update_local_rating()

    def delete(self, *args, **kwargs):
        game = self.game
        super().delete(*args, **kwargs)
        game.update_local_rating()


class Activity(models.Model):
    ACTION_CHOICES = [
        ("added", "Adicionou à lista"),
        ("status", "Mudou o status"),
        ("reviewed", "Escreveu uma review"),
        ("removed", "Removeu da lista"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    detail = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Atividade"
        verbose_name_plural = "Atividades"

    def __str__(self):
        return f"{self.user.username} — {self.get_action_display()} — {self.game.title}"  # type: ignore
