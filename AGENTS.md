# AGENTS.md — MyGamesList

Site no estilo MyAnimeList para jogos: lista pessoal com status, reviews e moderação. Catálogo importado da API RAWG.

## Stack

- Python 3.12, Django 5.2, Crispy Forms (`crispy_bootstrap5`), Markdown
- Banco: PostgreSQL em produção (via `DATABASE_URL`), SQLite local (`db.sqlite3`, usado quando `DATABASE_URL` está vazia)
- Deploy: Google App Engine (`app.yaml`, gunicorn); segredos no Secret Manager
- Projeto em `core/`; todo o domínio no app `games/` (`rawg.py` = cliente da API, `steam.py` = descrição em português da Steam, `sanitize.py` = HTML permitido nas descrições, `services.py` = importação)

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

Testes ficam em `games/tests.py` e usam `django.test.TestCase` com o `Client`. Não chame a API RAWG nem a Steam nos testes: use `unittest.mock.patch` em `games.views.import_game`, `games.services.get_details`/`get_stores`/`get_description_pt` ou em `games.steam.requests.get`.

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

## Skills (`.claude/skills/`)

- Do projeto: `nova-tela-django` (view + URL + template + teste), `testes-django` (como montar e o que cobrir nos testes) e `commit-padrao` (mensagem de commit).
- De terceiros, instaladas com `npx skills add mattpocock/skills` e fixadas em `skills-lock.json`: `tdd`, `diagnosing-bugs`, `grill-me`, `to-spec`, `implement-spec`, `triage`, `domain-modeling`, `improve-codebase-architecture`, `handoff`, `git-guardrails-claude-code`. Atualize com `npx skills update` e não edite os arquivos delas à mão.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/), em inglês, no imperativo e em minúsculas. Esta regra vale sobre a skill `commit-padrao` no idioma e nos escopos; dela, siga a exigência de corpo concreto em mudanças maiores:

```
feat: add review filter by status
fix: redirect duplicate review to edit page
chore: configure gcloud
```

Tipos usados: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.
