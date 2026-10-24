---
name: testes-django
description: Use ao escrever, corrigir ou rodar testes do projeto Django (games/tests.py). Define como montar os dados, quais casos cobrir (sucesso, anônimo, outro usuário, regra negada), como verificar mensagens e como simular o RAWG e a IA sem chamadas reais.
allowed-tools: Bash(python manage.py test *), Bash(python manage.py check)
---

# Testes do MyGamesList

## 1. Como rodar

Com o ambiente virtual ativo:

```bash
python manage.py test                          # tudo
python manage.py test games.tests.NomeDaClasse # uma classe
python manage.py test games.tests.NomeDaClasse.test_um_caso -v 2
```

Rode também `python manage.py check` antes de entregar.

## 2. Estrutura

- Use `django.test.TestCase`, uma classe por tela ou regra (`ReviewCreateTests`, `MinhaListaTests`).
- Nome do teste em português: `test_<ação>_<condição>_<resultado>`, por exemplo `test_review_duplicada_redireciona_para_edicao`.
- Monte os dados em `setUp` (ou `setUpTestData`):
  ```python
  self.alice = User.objects.create_user("alice", password="senha12345")
  self.bob = User.objects.create_user("bob", password="senha12345")
  self.jogo = Game.objects.create(rawg_id=1, title="Jogo X")
  ```
- Entre com `self.client.force_login(self.alice)`. Não precisa passar pela tela de login.
- O grupo `Moderador` **não** é criado por migration, então o teste cria: `Group.objects.create(name="Moderador")` e adiciona o usuário.
- Use `reverse("games:nome_da_rota", kwargs={...})` em vez de escrever a URL.
- O `seed_test_data.py` é um script manual, não serve para testes automatizados.

## 3. Casos que toda tela precisa cobrir

1. **Sucesso:** o dono faz a ação e o resultado aparece (status 200 ou 302, e o registro no banco).
2. **Anônimo:** é redirecionado ao login.
   ```python
   r = self.client.get(url)
   self.assertEqual(r.status_code, 302)
   self.assertIn(reverse("games:login"), r.url)
   ```
3. **Outro usuário:** recebe 403 e nada muda no banco.
4. **Regra negada:** o caso em que a regra de negócio proíbe a ação (duplicidade, sem permissão, sem o jogo na lista).
5. **Efeito colateral:** o que a ação deveria mexer em outras tabelas (`Activity` criada, `Game.local_rating` recalculada).

## 4. Regras de negócio com teste obrigatório

- Uma review por usuário e jogo: a segunda não dá erro 500, redireciona para a edição.
- Só avalia quem tem o jogo na própria lista.
- Importar um jogo exige login.
- Só o dono edita ou exclui a própria review e os próprios itens da lista.
- O moderador pode excluir qualquer review. Um jogador comum, não.
- A nota média do jogo é recalculada ao criar, editar e excluir uma review.
- Excluir review por GET não pode dar erro 500.
- Recomendações nunca incluem jogos que o usuário já tem na lista ou já avaliou.

## 5. Mensagens

```python
from django.contrib.messages import get_messages

r = self.client.post(url, dados)
textos = [str(m) for m in get_messages(r.wsgi_request)]
self.assertIn("Review publicada com sucesso!", textos)
```

Com `follow=True`, use `r.context["messages"]`.

## 6. Serviços externos: nunca chame de verdade

Use `unittest.mock.patch` no módulo **onde o nome é usado**, não onde foi definido:

```python
from unittest.mock import patch

@patch("games.views.get")               # busca no RAWG
@patch("games.services.get_details")    # importação de um jogo
```

Para a IA, faça o `patch` da função `chamar_ia` no módulo que a chama. Nenhum teste pode usar rede, chave de API ou consumir a cota de tokens.

## 7. Corrigindo bugs

1. Escreva primeiro o teste que reproduz o bug e confirme que ele **falha**.
2. Corrija o código.
3. Confirme que o teste passa e que o resto continua passando.

Se um teste falhar, corrija o código. Não afrouxe o teste para ele passar.

## 8. Ao terminar

Mostre ao usuário o resumo da execução (quantos testes, quantos passaram) e liste os casos novos que você cobriu.
