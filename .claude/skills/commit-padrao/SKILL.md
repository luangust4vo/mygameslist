---
name: commit-padrao
description: Use sempre que for escrever a mensagem de um commit neste projeto, ou quando o usuário pedir para commitar. Gera mensagens no padrão Conventional Commits, com resumo no imperativo e, quando a mudança for maior, um corpo que nomeia o que foi implementado. Nunca usa rótulos genéricos como "ajustes" ou "melhorias".
allowed-tools: Bash(git diff *), Bash(git status *), Bash(git log *)
---

# Mensagem de commit (Conventional Commits)

## 1. Leia as mudanças reais

Antes de escrever qualquer coisa, rode e leia a saída:

```bash
git status
git diff --cached
git log -5 --oneline
```

- Se não houver nada em stage, avise o usuário e sugira `git add <arquivos>`. Não invente mensagem.
- O `git log` serve só para ver o estilo do projeto (escopos e idioma). Não copie mensagens ruins que já existam.

## 2. Formato

```
tipo(escopo): resumo no imperativo

Corpo (quando exigido pela regra 4).
```

1. **Primeira linha:** `tipo(escopo): resumo`, até 72 caracteres, sem ponto final, em português, no imperativo ("adiciona", "corrige", "remove"; nunca "adicionado" nem "adicionei").
2. **Tipos válidos:** `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`.
3. **Escopos deste projeto:** `auth`, `lista`, `reviews`, `jogos`, `moderacao`, `recomendacao`, `preferencias`, `ia`, `assistente`, `deploy`, `config`, `docs`, `testes`. Se nenhum servir, omita o escopo.
4. **Corpo obrigatório** quando o diff toca mais de um arquivo **e** passa de umas 15 linhas. Escreva de 2 a 5 linhas (ou bullets) dizendo o que mudou em termos concretos: nomeie a função, a classe, o model, a rota, o template ou o teste.
5. **Exceção ao corpo:** se o resumo já explica tudo (typo, link, atualização de versão de dependência), o corpo pode ser omitido.
6. **Um commit, um assunto.** Se o diff mistura mudanças sem relação (por exemplo, um bug e uma tela nova), não force uma mensagem que cubra as duas. Avise o usuário e sugira separar em dois commits com `git add -p`.
7. **Nunca descreva o que não está no diff.** Cada afirmação da mensagem precisa ser verificável olhando as mudanças.

## 3. O que o corpo precisa ter

O corpo responde "o que mudou no código?", e não "qual é o tema?".

- Cite nomes que aparecem no diff.
- Prefira bullets se houver mais de uma mudança concreta.
- É proibido repetir o resumo com sinônimos ("implementa a funcionalidade", "inclui melhorias").

**Ruim** (parafraseia o título):
```
feat(reviews): permitir editar review

Adiciona a edição de reviews e as validações necessárias.
```

**Bom** (nomeia o que o diff criou):
```
fix(reviews): evita erro 500 ao avaliar um jogo duas vezes

ReviewCreateView.dispatch redireciona para ReviewUpdateView quando o
usuário já tem review do jogo e envia messages.info.
Adiciona ReviewCreateTests.test_review_duplicada_redireciona_para_edicao.
```

## 4. Resultado

Mostre a mensagem completa em um bloco de código e pergunte se o usuário quer que você faça o commit. Só rode `git commit` se ele pedir.
