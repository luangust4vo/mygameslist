# AGENTS.md — MyGamesList

Site no estilo MyAnimeList para jogos: lista pessoal com status, reviews e moderação. Catálogo importado da API RAWG.

## Stack

- Python 3.12, Django 5.2, Crispy Forms (`crispy_bootstrap5`), Markdown
- Banco: PostgreSQL em produção (via `DATABASE_URL`), SQLite local (`db.sqlite3`, usado quando `DATABASE_URL` está vazia)
- Deploy: Google App Engine (`app.yaml`, gunicorn); segredos no Secret Manager
- Projeto em `core/`; todo o domínio no app `games/` (`rawg.py` = cliente da API, `services.py` = importação)

## Rodar

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env-example .env        # preencha API_KEY (RAWG); deixe DATABASE_URL vazia para SQLite
echo "DEBUG=True" >> .env
python manage.py migrate
python manage.py runserver
python manage.py shell < seed_test_data.py   # dados de teste (opcional)
```

Com `DEBUG=True` o projeto carrega o `django-debug-toolbar` (em `/__debug__/`).

## Testar

```bash
python manage.py check
python manage.py test games
```

Testes ficam em `games/tests.py` e usam `django.test.TestCase` com o `Client`. Não chame a API RAWG nos testes: use `unittest.mock.patch` em `games.views.import_game` ou em `games.rawg`.

## Convenções

- Views baseadas em classe (`CreateView`, `UpdateView`, `ListView`…); nada de views em função.
- Textos visíveis ao usuário, `verbose_name` e mensagens em português. URLs novas também em português (ex.: `minha-lista/`).
- Cada usuário só acessa os próprios registros: `LoginRequiredMixin` + `UserPassesTestMixin` (`test_func` compara com `request.user`) ou queryset filtrado por `user=self.request.user`. Exceção: o grupo `Moderador` pode excluir qualquer review (use `GroupRequiredMixin` de `games/mixins.py`).
- Toda ação de criar, alterar ou excluir chama `messages.success` (ou `messages.error`/`messages.info` quando bloqueada).
- Chaves e credenciais (RAWG, Gemini, banco, `SECRET_KEY`) só em variáveis de ambiente (`.env`, nunca versionado) ou no Secret Manager. Leia com `get_config_value` em `core/settings.py`. Nunca no banco nem no repositório.
- Templates em `games/templates/games/<área>/`, herdando de `base.html`.

## Documentos (`docs/`)

- `docs/proposta.md`: proposta do sistema, com problema, usuários, escopo e regras de negócio. O que está marcado **(novo)** ainda não foi implementado.
- `docs/2026 - Plano de Atividades e Avaliações-1.pdf`: plano de atividades e avaliações da disciplina.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/), em inglês, no imperativo e em minúsculas:

```
feat: add review filter by status
fix: redirect duplicate review to edit page
chore: configure gcloud
```

Tipos usados: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.
