from django.contrib.auth.models import User
from games.models import Game, Review

u1, _ = User.objects.get_or_create(username="alice")
u1.set_password("teste1234")
u1.save()

u2, _ = User.objects.get_or_create(username="bob")
u2.set_password("teste1234")
u2.save()

game, _ = Game.objects.get_or_create(
    rawg_id=999999, defaults={"title": "Jogo de Teste"}
)

for i in range(15):
    user = u1 if i % 2 == 0 else u2
    g, _ = Game.objects.get_or_create(
        rawg_id=1000000 + i, defaults={"title": f"Jogo de Teste {i}"}
    )
    Review.objects.get_or_create(
        user=user,
        game=g,
        defaults={"rating": i % 6, "title": f"Review {i}", "body": "Texto de teste"},
    )

print(
    f"Criado: {Review.objects.count()} reviews, {Game.objects.count()} jogos, {User.objects.count()} usuários"
)
