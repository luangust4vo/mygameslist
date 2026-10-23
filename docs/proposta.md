# Proposta — MyGamesList

> Rascunho. O que já existe no código está marcado com **(existe)**; o que falta está marcado com **(novo)**.

## 1. O problema

Quem joga em várias plataformas perde o controle do que já jogou, do que zerou e do que achou de cada jogo. Além disso, escolher o próximo jogo é difícil: as lojas mostram o que é popular, não o que combina com o gosto da pessoa, e as descrições dos jogos vêm quase sempre em inglês.

Caso concreto (reescrever com um caso seu): um jogador com dezenas de jogos em PC e console não lembra quais terminou nem o que achou deles, e na hora de escolher o próximo passa muito tempo lendo páginas em inglês sem saber se combina com o que ele costuma gostar.

O MyGamesList é um site, no estilo do MyAnimeList, em que o jogador monta a sua lista de jogos com status, escreve reviews e recebe recomendações de novos jogos a partir dos gêneros e plataformas de que gosta e das notas que dá.

## 2. Quem vai usar

- **Visitante:** vê a página inicial, busca jogos e lê as páginas dos jogos e as reviews. Não altera nada.
- **Jogador (logado):** mantém a própria lista, escreve reviews, define as próprias preferências, recebe recomendações e usa o assistente de IA. Só vê e altera os próprios dados.
- **Moderador:** exclui reviews impróprias, pede nova tradução de uma descrição, consulta o consumo de IA e edita a configuração da IA.

## 3. O que o sistema faz

1. Cadastro, login, logout e troca de senha **(existe)**.
2. Busca de jogos na API do RAWG e importação para o catálogo local **(existe)**; a importação passa a exigir login **(novo)**.
3. Página do jogo com a descrição traduzida para português por IA, guardada no banco; a original em inglês é mantida **(novo)**.
4. Minha lista com status (Quero Jogar, Jogando, Pausado, Zerado, Platinado, Dropado) **(existe)**, com filtros por status, gênero e plataforma e paginação que preserva os filtros **(novo)**.
5. Reviews com nota de 0 a 5, título e comentário: criar, editar e excluir **(existe)**; tela "minhas reviews" **(novo)**.
6. Feed de atividades na página inicial **(existe)**; registrar também a atividade de review **(novo)**.
7. Preferências do jogador: logo após o cadastro, o sistema pede (sem obrigar) que o jogador escolha gêneros e plataformas de que gosta; o jogador pode pular e editar depois **(novo)**.
8. Recomendações de jogos com base nas preferências e no que o jogador avaliou e listou, cada uma com o motivo ("porque você gosta de RPG e deu nota 5 a ...") **(novo)**.
9. Painel de moderação **(existe)**.
10. Assistente de IA que responde sobre jogos e sobre o uso do site, com histórico por usuário **(novo)**.
11. App `ia`: configuração editável, auditoria de cada chamada, cota mensal de tokens, e as telas de requisições, configuração (com "Testar conexão"), IA por usuário e meu consumo **(novo)**.
12. Comando para popular o catálogo com jogos populares por gênero e carregar as listas de gêneros e plataformas do RAWG **(novo)**.

## 4. O que o sistema NÃO faz

- Não recomenda por semelhança entre usuários (filtragem colaborativa) nem usa aprendizado de máquina; a recomendação é por conteúdo (gêneros, plataformas e notas do próprio jogador).
- Não tem rede social: sem seguir pessoas, sem comentar nas reviews dos outros, sem mensagens entre usuários.
- Não vende, não compra nem rastreia preço de jogos.
- Não importa listas de outras plataformas (Steam, PlayStation etc.).
- Não traduz comentários e reviews dos usuários; só as descrições vindas do RAWG.
- Não tem upload de imagens; as capas vêm do RAWG.
- Não tem login por redes sociais nem aplicativo para celular.
- Não tem bot do Telegram nesta versão.

## 5. Regras de negócio

- Cada jogador só vê e altera os próprios itens de lista, reviews e preferências; o Moderador pode excluir qualquer review (é a exceção).
- Um jogo aparece no máximo uma vez na lista de cada jogador, e cada jogador escreve no máximo uma review por jogo; ao tentar de novo, o sistema leva para a edição da review existente.
- Só pode avaliar um jogo quem o tem na própria lista.
- A nota média local de um jogo é a média das reviews e é recalculada ao criar, editar ou excluir uma review.
- Importar um jogo para o catálogo exige login.
- As preferências são opcionais: o jogador pode pular e editá-las depois.
- A pontuação de gêneros do jogador soma: um peso fixo para cada gênero marcado nas preferências; para cada jogo avaliado, (nota − 2,5) em cada gênero do jogo; um pequeno acréscimo para jogos Zerados ou Platinados e uma redução para Dropados. Os valores exatos ficam para o PRD.
- A recomendação nunca inclui jogos que já estão na lista ou que o jogador já avaliou.
- Se o jogador não tem preferências nem avaliações, recebe os jogos mais bem avaliados do catálogo.
- Toda recomendação mostra o motivo.
- A descrição é traduzida uma única vez e guardada; só o Moderador pode pedir nova tradução.
- Toda chamada à IA passa pelo app `ia` (única porta de entrada), é registrada na auditoria e conta na cota mensal de tokens; com a cota esgotada a chamada é bloqueada com mensagem clara.
- O assistente responde só sobre jogos e sobre o uso do site e recusa outros assuntos; mantém histórico por usuário e usa as 5 últimas mensagens como contexto.
- Chaves (RAWG, Gemini) ficam só em variáveis de ambiente ou no Secret Manager, nunca no banco nem no repositório.

## 6. IA e Telegram

- **IA (Gemini), obrigatória:** tradução das descrições, assistente de jogos e, como item Desejável, explicação em linguagem natural do motivo de cada recomendação. Tudo passa por `chamar_ia`.
- **Telegram:** fora do escopo desta versão.

## 7. Dúvidas

- Quais status contam para poder avaliar: qualquer um, ou "Quero Jogar" não conta?
- Os pesos da recomendação (preferência declarada, nota, status) precisam de teste com dados reais para ficarem bons.
- Quantos jogos o comando de popular o catálogo deve importar por gênero, e se ele roda também contra o banco de produção.
- O que o assistente faz se o RAWG ou a IA estiver fora do ar.
- O que o TestAI exige (formato de entrega do código).
- Quem é o Moderador em produção e como o grupo é criado (migration ou manualmente).