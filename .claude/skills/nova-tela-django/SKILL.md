---
name: nova-tela-django
description: Use ao criar ou alterar uma tela do app games (view, URL e template). Segue o padrão do projeto - view baseada em classe, acesso só do dono dos dados, mensagem de feedback, template com Crispy Forms em português e teste. Use também ao criar listas com filtro ou paginação.
---

# Nova tela no MyGamesList

## 1. Antes de escrever

Leia uma tela parecida e siga o estilo dela:

- Listagem do usuário: `MyGameListView` em `games/views.py`.
- Criar, editar e excluir: `ReviewCreateView`, `ReviewUpdateView`, `AddToListView`, `EditListItemView`, `RemoveFromListView`.
- Área restrita a grupo: `ModerationPanelView` e `games/mixins.py` (`GroupRequiredMixin`).

## 2. View (`games/views.py`)

- Use **view baseada em classe** (`ListView`, `CreateView`, `UpdateView`, `DeleteView`, `DetailView`).
- Tela que mexe em dados do usuário: `LoginRequiredMixin` primeiro.
- **Só o dono acessa os próprios registros:**
  - Listagem: `get_queryset` filtra por `request.user`.
  - Detalhe, edição e exclusão: `UserPassesTestMixin` com `test_func` comparando o dono (resposta 403).
  - Exceção: o grupo `Moderador` pode excluir reviews (`GroupRequiredMixin`, `group_required = "Moderador"`).
- Em `form_valid`: preencha `form.instance.user = self.request.user`, faça os efeitos colaterais (por exemplo `Activity.objects.create(...)`) e termine com `messages.success(...)`.
- Em exclusões, envie a mensagem em `form_valid` (no `DeleteView` do Django 5 é ali que o objeto é apagado), não em `get_success_url`.
- **Unicidade:** se o model tem `unique_together` (como `(user, game)` em `Review` e `UserGameList`), verifique antes de salvar e responda com redirecionamento e mensagem. Nunca deixe estourar `IntegrityError`.
- **Consultas:** use `select_related` para chaves estrangeiras (`user`, `game`) e `prefetch_related` para muitos-para-muitos (`genres`, `platforms`) quando o template percorre essas relações. Confira o número de queries com o Debug Toolbar.
- Não chame a API do RAWG nem o Gemini direto da view. O RAWG vai por `games/rawg.py` e `games/services.py`, e a IA passa pelo app `ia`.

## 3. URL (`games/urls.py`)

- Dê um `name` a cada rota (o app usa `app_name = "games"`).
- Siga o estilo vizinho: telas do usuário em português (`minha-lista/`, `lista/<pk>/editar/`).

## 4. Template (`games/templates/games/<área>/<tela>.html`)

- Comece com `{% extends 'base.html' %}` e use `{% block title %}` e `{% block content %}`.
- Formulários: `{% load crispy_forms_tags %}`, `{% csrf_token %}` e `{{ form|crispy }}`, com os botões "Salvar" e "Cancelar".
- Textos em português do Brasil, tom simples e direto.
- **Nada de `|safe` nem `mark_safe`** sem sanitizar antes. O texto das reviews já sai escapado.
- Não coloque regra de negócio no template.
- Listas paginadas: use a templatetag de paginação do projeto (que preserva os filtros) em vez de `?page=N` solto.

## 5. Mensagens

- Use `messages.success`, `messages.error`, `messages.info` e `messages.warning`.
- O `base.html` mostra cada mensagem como `alert-{{ message.tags }}`. Para `messages.error` aparecer em vermelho, `settings.py` precisa mapear `MESSAGE_TAGS` (`messages.ERROR: "danger"`). Se ainda não existir, inclua.

## 6. Ao terminar

1. Escreva ou atualize os testes (skill `testes-django`): sucesso, anônimo, outro usuário e o caso negado.
2. Rode `python manage.py check` e `python manage.py test`.
3. Conferir na tela, no navegador, o fluxo completo.
4. Se mudou uma regra de negócio, atualize antes o `docs/prd.md`.
