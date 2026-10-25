# Proposta — MyGamesList

> Rascunho. O que já existe no código está marcado com **(existe)**; o que falta está marcado com **(novo)**. Itens com **(depois de 13/11)** ficam fora da entrega do 3º trimestre.

## 1. O problema

Quem joga em várias plataformas perde o controle do que já jogou, do que zerou e do que achou de cada jogo. Além disso, escolher o próximo jogo é difícil: as lojas mostram o que é popular, não o que combina com o gosto da pessoa, e as descrições dos jogos vêm quase sempre em inglês.

Caso concreto (reescrever com um caso seu): um jogador com dezenas de jogos em PC e console não lembra quais terminou nem o que achou deles, e na hora de escolher o próximo passa muito tempo lendo páginas em inglês sem saber se combina com o que ele costuma gostar.

O MyGamesList é um site, no estilo do MyAnimeList, em que o jogador monta a sua lista de jogos com status, escreve reviews e recebe recomendações de novos jogos a partir dos gêneros e plataformas de que gosta e das notas que dá.

## 2. Quem vai usar

- **Visitante:** vê a página inicial, busca jogos e lê as páginas dos jogos e as reviews. Não altera nada.
- **Jogador (logado):** importa jogos para o catálogo, mantém a própria lista, escreve reviews, usa o assistente de IA e vê o próprio consumo de IA. Só vê e altera os próprios dados.
- **Moderador:** exclui reviews impróprias, filtra reviews no painel de moderação, pede nova tradução de uma descrição, consulta as requisições e o consumo de IA por usuário e edita a configuração da IA.

## 3. O que o sistema faz

1. Cadastro, login, logout e troca de senha **(existe)**.
2. Busca de jogos na API do RAWG e importação para o catálogo local, exigindo login **(existe)**.
3. Página do jogo:
   - descrição em português buscada na Steam (texto oficial), guardada no banco como HTML sanitizado; sem ela, mostra a original em inglês do RAWG com aviso **(existe)**;
   - capa e ações fixas enquanto as informações rolam **(existe)**;
   - gêneros traduzidos para português na exibição **(existe)**;
   - tradução por IA quando a Steam não tem descrição em português **(novo)**;
   - botão do Moderador para pedir nova tradução por IA **(novo)**.
4. Minha lista com status (Quero Jogar, Jogando, Pausado, Zerado, Platinado, Dropado) **(existe)**, com filtros por status, gênero e plataforma (django-filter, campos com Select2) e paginação que preserva os filtros por uma templatetag própria **(novo)**.
5. Reviews com nota de 0 a 5, título e comentário: criar, editar e excluir **(existe)**; tela "minhas reviews" **(novo, depois de 13/11)**.
6. Página inicial com "Jogos em destaque" (maior nota RAWG), "Mais bem avaliados" (nota local), "Chegaram agora" e feed de atividades, incluindo a de review **(existe)**.
7. Preferências do jogador: logo após o cadastro, o sistema pede (sem obrigar) que o jogador escolha gêneros e plataformas de que gosta; o jogador pode pular e editar depois **(novo, depois de 13/11)**.
8. Recomendações de jogos com base nas preferências e no que o jogador avaliou e listou, cada uma com o motivo ("porque você gosta de RPG e deu nota 5 a ...") **(novo, depois de 13/11)**.
9. Painel de moderação **(existe)**, com filtros por jogo, autor e nota (django-filter) e paginação que preserva os filtros **(novo)**.
10. Confirmação de remoção da lista, exclusão de review e "Limpar conversa" em modal com Bootbox; a página de confirmação continua funcionando sem JavaScript **(novo)**.
11. Assistente de IA que responde sobre jogos e sobre o uso do site, com histórico por usuário, em `assistente/` **(novo)**.
12. App `ia`: configuração editável, auditoria de cada chamada, cota mensal de tokens por usuário, e as telas de requisições, configuração (com "Testar conexão"), IA por usuário e meu consumo **(novo)**.
13. Comando para popular o catálogo com jogos populares por gênero e carregar as listas de gêneros e plataformas do RAWG **(novo, depois de 13/11)**.

## 4. O que o sistema NÃO faz

- Não recomenda por semelhança entre usuários (filtragem colaborativa) nem usa aprendizado de máquina; a recomendação é por conteúdo (gêneros, plataformas e notas do próprio jogador).
- Não tem rede social: sem seguir pessoas, sem comentar nas reviews dos outros, sem mensagens entre usuários.
- Não vende, não compra nem rastreia preço de jogos.
- Não importa listas de outras plataformas (Steam, PlayStation etc.); da Steam usa só a descrição pública do jogo.
- Não traduz comentários e reviews dos usuários; só as descrições dos jogos.
- Não tem upload de imagens; as capas vêm do RAWG.
- Não tem login por redes sociais nem aplicativo para celular.
- Não tem bot do Telegram nesta versão.

## 5. Regras de negócio

### Lista e reviews
- Cada jogador só vê e altera os próprios itens de lista, reviews, histórico do assistente e preferências; o Moderador pode excluir qualquer review (é a exceção).
- Um jogo aparece no máximo uma vez na lista de cada jogador, e cada jogador escreve no máximo uma review por jogo; ao tentar de novo, o sistema leva para a edição da review existente.
- Só pode avaliar um jogo quem o tem na própria lista, com qualquer status.
- A nota média local de um jogo é a média das reviews e é recalculada ao criar, editar ou excluir uma review.
- Importar um jogo para o catálogo exige login.
- O grupo Moderador é criado por migration; quem faz parte dele é definido no admin.

### Descrições
- Na importação, a descrição em português vem da Steam quando o RAWG aponta uma página da loja; falhas na Steam não impedem a importação.
- Sem descrição da Steam, a IA traduz a original uma única vez e guarda com fonte "ia"; a chamada conta na cota de quem importou.
- Só o Moderador pede nova tradução, e só em jogos sem descrição em português ou com fonte "ia". O texto da Steam, que é oficial, não é substituído.
- Toda descrição é guardada e exibida como HTML sanitizado (nh3): só h2, h3, h4, p, br, ul, ol, li, strong e em, sem atributos.

### IA
- Toda chamada à IA passa por `chamar_ia` no app `ia` (única porta de entrada), é registrada na auditoria (inclusive as que falham) e conta na cota mensal de tokens do usuário.
- A cota é por usuário: vale o limite padrão da configuração, que o Moderador pode ajustar por usuário. Com a cota esgotada, a chamada é bloqueada com mensagem clara.
- A configuração fica em uma única linha no banco: modelo do Gemini, temperatura, máximo de tokens por resposta, cota mensal padrão e a chave "IA ativa". A chave de API não fica no banco.
- O Gemini é chamado pela API REST com `requests`.

### Assistente
- Antes de responder, uma chamada curta de classificação (só a pergunta, sem histórico) decide se a pergunta é sobre jogos ou sobre o uso do site; se não for, a pergunta principal nem é feita. As instruções do `contexto_projeto.md` são a segunda barreira.
- A resposta usa o `contexto_projeto.md`, as 5 últimas mensagens e um resumo da lista do usuário (até cerca de 30 jogos com status).
- O histórico guarda só pares de pergunta e resposta. Se a IA falhar ou a cota acabar, a conversa mostra o motivo, a pergunta não entra no histórico e a falha fica na auditoria.
- O usuário pode limpar a própria conversa; a auditoria é mantida.
- Perguntas têm até 500 caracteres e são enviadas por AJAX (`$.ajax`) com CSRF.
- A resposta é Markdown sanitizado com nh3: as tags da descrição mais code, pre, blockquote e links com href só em http, https ou caminhos do próprio site.

### Recomendações (depois de 13/11)
- As preferências são opcionais: o jogador pode pular e editá-las depois.
- A pontuação de gêneros do jogador soma: um peso fixo para cada gênero marcado nas preferências; para cada jogo avaliado, (nota − 2,5) em cada gênero do jogo; um pequeno acréscimo para jogos Zerados ou Platinados e uma redução para Dropados. Os valores exatos ficam para o PRD.
- A recomendação nunca inclui jogos que já estão na lista ou que o jogador já avaliou.
- Se o jogador não tem preferências nem avaliações, recebe os jogos mais bem avaliados do catálogo.
- Toda recomendação mostra o motivo.

### Segredos
- Chaves (RAWG, Gemini) ficam só em variáveis de ambiente ou no Secret Manager, nunca no banco nem no repositório.

## 6. IA e Telegram

- **IA (Gemini), obrigatória:** tradução das descrições sem texto na Steam, classificação e respostas do assistente e, como item Desejável depois de 13/11, explicação em linguagem natural do motivo de cada recomendação. Tudo passa por `chamar_ia`.
- **Telegram:** fora do escopo desta versão.

## 7. Plano até 13/11

1. Atualizar esta proposta e criar a migration do grupo Moderador **(existe)**.
2. django-filter na Minha lista e no painel de moderação, com a templatetag de paginação **(novo)**.
3. Select2 e Bootbox **(novo)**.
4. App `ia`: models (configuração, auditoria e cota), `chamar_ia` e as quatro telas **(novo)**.
5. Tradução por IA como alternativa à Steam e o botão de nova tradução do Moderador **(novo)**.
6. Assistente **(novo)**.
7. Entrega **(novo)**:
   - `README.md` com uma tabela que liga cada requisito do plano ao arquivo que o cumpre;
   - conferência item por item contra o plano;
   - merge na `main` e deploy (Neon e App Engine);
   - texto do repositório gerado pelo gitingest a partir da `main`, sem o PDF, as skills de terceiros e o `skills-lock.json`, colado no TestAI.

## 8. Dúvidas

- Os pesos da recomendação (preferência declarada, nota, status) precisam de teste com dados reais para ficarem bons.
- Quantos jogos o comando de popular o catálogo deve importar por gênero, e se ele roda também contra o banco de produção.
- Quem é o Moderador em produção.
