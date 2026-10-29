# MyGamesList

Site no estilo do MyAnimeList para jogos: cada jogador monta a própria lista com status, escreve reviews e conversa com um assistente de IA sobre jogos. O catálogo é importado da API do [RAWG](https://rawg.io/apidocs), as descrições em português vêm da Steam ou são traduzidas pelo Gemini, e o grupo Moderador cuida das reviews e do uso de IA.

- Proposta, escopo e regras de negócio: [`docs/proposta.md`](docs/proposta.md)
- Instruções para agentes de IA e convenções do código: [`AGENTS.md`](AGENTS.md)

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
