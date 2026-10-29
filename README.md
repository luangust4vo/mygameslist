# MyGamesList

Site no estilo do MyAnimeList para jogos: cada jogador monta a própria lista com status, escreve reviews e conversa com um assistente de IA sobre jogos. O catálogo é importado da API do [RAWG](https://rawg.io/apidocs), as descrições em português vêm da Steam ou são traduzidas pelo Gemini, e o grupo Moderador cuida das reviews e do uso de IA.

- Proposta, escopo e regras de negócio: [`docs/proposta.md`](docs/proposta.md)
- Instruções para agentes de IA e convenções do código: [`AGENTS.md`](AGENTS.md)

Em produção: <https://mygameslist-497823.rj.r.appspot.com>

## Requisitos da disciplina

Onde cada item do plano de atividades está no código e como vê-lo funcionando no site.

### Definição do projeto

| Requisito | Onde está | Como ver no site |
|---|---|---|
| Pelo menos seis classes no models (sem contar `User`) | `games/models.py`: `Genre`, `Platform`, `Game`, `UserGameList`, `Review`, `Activity`; `ia/models.py`: `ConfiguracaoIA`, `CotaUsuario`, `RequisicaoIA`, `MensagemAssistente` | `/admin/` |
| Telas de inserir, alterar, excluir e listar | `UserGameList`: `AddToListView`, `EditListItemView`, `RemoveFromListView`, `MyGameListView`; `Review`: `ReviewCreateView`, `ReviewUpdateView`, `ReviewDeleteView`, `ReviewListView`, `ReviewDetailView`; `MensagemAssistente`: `PerguntarView`, `AssistenteView`, `LimparConversaView`; `ConfiguracaoIA` e `CotaUsuario`: `ConfiguracaoUpdateView`, `CotaUsuarioUpdateView`. `Game`, `Genre` e `Platform` são criados pela importação do RAWG e não são editados pelo usuário, por regra de negócio | Minha Lista, página do jogo → Ver reviews, Assistente |
| Um movimento (além do CRUD) | Importação do RAWG com descrição da Steam ou tradução pela IA (`games/services.py`); nota local recalculada a cada review (`Game.update_local_rating`); feed de atividades; assistente com cota e auditoria (`ia/servicos.py`, `ia/assistente.py`) | Buscar → importar um jogo; Início → Atividade recente |
| Layout com framework front-end | Bootstrap 5 com tema próprio em `static/css/global.css` e `games/templates/games/base.html` | Todas as telas |
| Controle de acesso com autenticação | `LoginRequiredMixin` nas telas do usuário; login, logout, cadastro e troca de senha em `games/urls.py` | Minha Lista sem login redireciona para Entrar |
| Controle de acesso por grupo em mais de uma view | Grupo Moderador (`GroupRequiredMixin` em `games/mixins.py`): `ModerationPanelView`, `RetraduzirDescricaoView`, exclusão de qualquer review e as telas de IA (`ia/views.py`, `ModeradorMixin`) | Menu Moderação (só para o grupo) |
| Plugins front-end (jQuery) | Select2 e Bootbox em `static/js/mgl.js`; `$.ajax` em `static/js/assistente.js` | Filtros da Minha Lista; botão Remover; Assistente |
| Controle de versões com Git | Repositório no GitHub, Conventional Commits, branches com pull request | — |

### 3º trimestre — 1ª parte

| Requisito | Onde está | Como ver no site |
|---|---|---|
| 1. Debug Toolbar e consultas otimizadas | `debug_toolbar` em `core/settings.py` com `DEBUG=True`; `select_related` em `MyGameListView`, `ModerationPanelView`, `ReviewListView`, `RequisicaoListView` e no feed; `prefetch_related("genres")` em "Jogos em destaque" (`HomeView`) | Rodando localmente, painel SQL em qualquer tela |
| 2. Django Filter em duas ListViews, com paginação por templatetag própria que preserva a busca | `games/filters.py` (Minha Lista e painel de moderação) e `ia/filters.py` (requisições de IA); templatetag `url_pagina` em `games/templatetags/custom_filters.py`, usada por `comum/_paginacao.html` | Minha Lista → filtrar → página 2 |
| 3. Registros do próprio usuário em duas classes | `UserGameList` (listar, alterar e excluir só os seus) e `MensagemAssistente` (listar, criar e apagar só os seus); `Review` só pode ser alterada ou excluída pelo autor | Minha Lista; Assistente |
| 4. Mensagens em cadastro, alteração e exclusão | `messages.success`/`error`/`info` em todas as views de criar, alterar e excluir | Alertas no topo da página |
| 5. Dois plugins jQuery | Select2 (busca nos campos de gênero e plataforma) e Bootbox (confirmação de remover da lista, excluir review, nova tradução e limpar conversa) | Minha Lista |
| 6. Deploy no Google App Engine | `app.yaml`, `.gcloudignore`, segredos no Secret Manager (veja [Deploy](#deploy-no-google-app-engine)) | <https://mygameslist-497823.rj.r.appspot.com> |

### 3º trimestre — 2ª parte

| Requisito | Onde está | Como ver no site |
|---|---|---|
| 1. `AGENTS.md` e pelo menos três skills, uma para commits | `AGENTS.md`; `.claude/skills/commit-padrao`, `nova-tela-django` e `testes-django` | — |
| 2. App `ia` como única porta de entrada, com configuração, auditoria, cota mensal e as quatro telas | `ia/servicos.py` (`chamar_ia`); `ia/models.py`; telas de requisições, configuração com "Testar conexão", IA por usuário e meu consumo em `ia/views.py` | Moderação → Requisições de IA, Configuração da IA, IA por usuário; Meu consumo de IA |
| 3. Assistente com `chamar_ia`, `contexto_projeto.md`, limites, histórico por usuário, janela de 5 mensagens, AJAX com CSRF e Markdown sanitizado | `ia/assistente.py`, `ia/contexto_projeto.md`, `PerguntarView`, `static/js/assistente.js`, `markdown_seguro` em `games/sanitize.py` | Assistente |
| 4. Auditoria do código no TestAI | Texto do repositório gerado pelo gitingest a partir da `main` | — |
| 5. Sistema funcional, com interface amigável e navegação coerente | 137 testes automatizados (`games/tests.py`, `ia/tests.py`) e o site publicado | Todas as telas |

## Tecnologias

- Python 3.12, Django 5.2, django-filter, Crispy Forms (Bootstrap 5), nh3 e Markdown
- jQuery com os plugins Select2 e Bootbox
- PostgreSQL no [Neon](https://neon.tech) em produção e SQLite no desenvolvimento
- Google App Engine (gunicorn) e Secret Manager para as chaves
- Gemini (API REST) para tradução e assistente, sempre pelo app `ia`

## Rodar na sua máquina

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env-example .env
```

No `.env`, preencha `API_KEY` (RAWG) e, se quiser usar a IA, `GEMINI_API_KEY`. Deixe `DATABASE_URL` vazia para usar o SQLite local e acrescente `DEBUG=True`. Depois:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

> Com `DATABASE_URL` preenchida, o site usa o banco de produção do Neon. Só preencha quando for mexer nele de propósito (veja o deploy abaixo).

## Testes

```bash
python manage.py check
python manage.py test games ia
```

Os testes não chamam o RAWG, a Steam nem o Gemini: tudo é simulado com `unittest.mock.patch`.

## Deploy no Google App Engine

O site roda no projeto `mygameslist-497823`, região `southamerica-east1`, em <https://mygameslist-497823.rj.r.appspot.com>. O projeto pertence à conta institucional do IFPR.

### 1. Preparar o `gcloud` (uma vez por computador)

Instale o [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) e entre com a conta dona do projeto:

```bash
gcloud auth login
gcloud config set project mygameslist-497823
```

### 2. Criar os segredos (uma vez por projeto)

O `core/settings.py` lê as chaves com `get_config_value`: primeiro da variável de ambiente e, no App Engine, do Secret Manager. Em produção, `SECRET_KEY`, `API_KEY` e `DATABASE_URL` são obrigatórias; sem `GEMINI_API_KEY` o site funciona, mas a IA fica indisponível.

```bash
gcloud services enable secretmanager.googleapis.com

# Cada comando lê o valor da entrada padrão, sem deixar a chave no histórico do terminal.
printf '%s' 'valor-da-chave' | gcloud secrets create API_KEY --data-file=-
# Repita para DATABASE_URL e GEMINI_API_KEY. A SECRET_KEY deve ser nova e só de produção:
python -c "import secrets; print(secrets.token_urlsafe(50), end='')" | gcloud secrets create SECRET_KEY --data-file=-

# O site roda com a conta de serviço do App Engine, que precisa ler os segredos.
gcloud projects add-iam-policy-binding mygameslist-497823 \
  --member="serviceAccount:mygameslist-497823@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

Para trocar uma chave depois: `printf '%s' 'novo-valor' | gcloud secrets versions add NOME --data-file=-`. O site sempre lê a versão mais recente.

### 3. Atualizar o banco do Neon

Com a `DATABASE_URL` do Neon no `.env`:

```bash
python manage.py migrate
python manage.py createsuperuser   # só na primeira vez
```

A migration `games.0004` cria o grupo Moderador e a `ia.0002` cria a configuração padrão da IA. Para tornar alguém Moderador, use o admin (`/admin/`).

### 4. Publicar

```bash
DATABASE_URL= DEBUG=False python manage.py collectstatic --noinput --clear
gcloud app deploy
```

- O `collectstatic` gera em `static_gcloud/` os arquivos com hash no nome (por exemplo `global.c9ee25c4417e.css`), que o `app.yaml` serve em `/static`. Assim o navegador baixa a versão nova a cada deploy.
- O `.gcloudignore` deixa de fora o `.env`, o `venv/`, o `db.sqlite3` e o que não é usado em produção.
- O `app.yaml` roda o gunicorn com `--timeout 60`, porque o assistente faz duas chamadas ao Gemini na mesma requisição.

### 5. Conferir

```bash
gcloud app browse                 # abre o site
gcloud app logs tail -s default   # acompanha os logs em tempo real
gcloud app versions list          # versões publicadas e quanto tráfego cada uma recebe
```
