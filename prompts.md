# prompts.md · Uso de Inteligência Artificial no backend

Este arquivo documenta como ferramentas de Inteligência Artificial foram usadas no desenvolvimento do backend em Python do **Olho na Via**, como pede a página 31 do documento do desafio. Ele registra apenas interações que de fato aconteceram.

## 1. Ferramentas utilizadas

| Ferramenta | Tipo | Finalidade no projeto |
| --- | --- | --- |
| **Claude Code** (Anthropic) | Agente de programação no terminal | Ler o documento do desafio, os materiais de aula e o frontend; propor a arquitetura; escrever o código, os testes e a documentação; executar os testes e conferir as rotas contra o MongoDB Atlas; gravar os vídeos do README com Playwright. |

Nenhuma outra ferramenta de IA foi usada no backend.

## 2. O papel da IA: copiloto, não autora das decisões

O código deste repositório foi escrito pela ferramenta. O que ela implementou, porém, partiu de decisões que já existiam antes do backend:

- **As regras de negócio** (IPV, faixas de prazo, deduplicação, créditos e alertas) vêm do Sumário Executivo do projeto e já estavam no frontend, em `app/domain/regras.ts` e `app/domain/painel.ts`. A IA traduziu essas regras para Python; não as inventou.
- **As rotas e os dados** seguem o que o frontend já usava no mock do json-server. Por isso o backend e o frontend falam a mesma língua: os mesmos campos, os mesmos textos e os mesmos dados de demonstração.
- **O escopo e a arquitetura** foram decididos por mim, nas perguntas que a ferramenta fez antes de começar (seção 3).

O trabalho seguiu sempre o mesmo ciclo: eu fazia o pedido com as referências, a IA lia o projeto e implementava, eu revisava o resultado e pedia ajustes, e os testes rodavam antes de cada commit.

## 3. Fluxo de desenvolvimento

| Etapa | O que foi feito | Minha participação |
| --- | --- | --- |
| **1. Leitura e decisões** | A IA leu as páginas 29 a 32 do desafio, os materiais de aula em `referencias/` e o frontend, e apontou o conflito entre o meu pedido e as exigências do desafio. | Escolhi a arquitetura híbrida e o nome `prompts.md`. |
| **2. Regras e dados** | Estrutura base, conexão com o MongoDB, `regras.py` e o seed com os dados de demonstração em JSON. | Configurei o cluster no MongoDB Atlas e aceitei a sugestão de reaproveitar os dados de demonstração do frontend. |
| **3. API e Swagger** | Rotas de acesso, do cidadão, do painel e de dados abertos, com a documentação Swagger. | Defini que a API seguiria as rotas já documentadas no frontend. |
| **4. Menu no terminal** | Menu de opções para o gestor, com validação das entradas e exportação para JSON. | Exigência do desafio, que mantive junto com a API. |
| **5. Testes** | Testes unitários das regras, dos serviços e da API, sem usar o banco real. | Pedi os testes e conferi que rodavam sem internet. |
| **6. Documentação** | README com vídeos, funcionalidades, stack, arquitetura e Swagger, e este arquivo. | Pedi o mesmo formato do frontend. |

## 4. Prompts utilizados

Os pedidos estão transcritos como foram enviados.

### 4.1 Pedido inicial

> Certo, agora faça a implementação do repositório do backend em python. As instruções estão em @"Desafio-FIAP-GS-CitizenTech 1ES Paulista e Lins.pdf" entre as páginas 29 e 32. Não precisa fazer a integração dele com o frontend de fato ainda, mas no repositório do front tem documentado todas as rotas e funcionalidades que terão. Os materiais utilizados em sala estão em backend/referencias, além dos descritos no documento do desafio. Implemente o código na pasta backend sem fugir muito dos conceitos ensinados em aula, não insira comentários desnecessários, faça commits incrementais seguindo a pratica de conventional commits, faça uma documentação com swagger e implemente um arquivo IA.md que faça sentido com o projeto. Para banco de dados utilize o mongodb, já fiz a configuração no MongoDB Atlas as credenciais estão em atlas-credentials.env, crie um seed do banco de dados também.

**Resposta:** antes de escrever o código, a ferramenta apontou que o desafio exige menu de opções, persistência em JSON e o arquivo `prompts.md`, enquanto o pedido falava em API com Swagger, MongoDB e `IA.md`. Ela perguntou como seguir.

**Decisões que tomei:**

1. **Arquitetura híbrida:** API Flask com Swagger e MongoDB, mais um menu no terminal sobre os mesmos serviços, com JSON no seed e na exportação.
2. **Nome do arquivo:** `prompts.md`, como pede o desafio, no lugar de `IA.md`.

### 4.2 Testes unitários

> Faça a implantação de testes unitários no backend.

**Resposta:** a ferramenta acrescentou testes para o acesso, as ações do painel, os créditos, os utilitários e as rotas da API, chegando a 68 testes. O banco é trocado por objetos falsos com `unittest.mock`, então os testes rodam sem internet e sem mexer nos dados do Atlas.

### 4.3 README, vídeos e este arquivo

> Faça a implementação/atualização do README com vídeos, funcionalidades, stack e arquitetura, além do AI.md/prompts.md do backend, assim como foi feito no repositório do frontend. Lembre-se de citar a documentação swagger também.

**Resposta:** a ferramenta gravou três vídeos com Playwright: o uso do Swagger com login e token, as respostas de erro com os dados abertos e o menu no terminal. Também reorganizou o README com as funcionalidades, a stack, um diagrama da arquitetura e uma seção sobre o Swagger. Neste arquivo, acrescentou o fluxo de desenvolvimento e os prompts reais.

**Ajuste que veio da gravação:** ao rodar o menu para gravar, a ferramenta viu que a fila quebrava o alinhamento quando o prazo era longo ("Vencido há 10 diasdespachar") e alargou a coluna em `main.py`.

### 4.4 Revisão contra o desafio

> Revise as entregas de backend de acordo com o desafio @"Desafio-FIAP-GS-CitizenTech 1ES Paulista e Lins.pdf" faça apontamentos caso houver e sugestões de melhoria para ficar um trabalho mais completinho.

**Resposta:** a ferramenta comparou o backend com as páginas 21, 22 e 29 a 32 e encontrou um problema grave: sem o arquivo de credenciais do MongoDB, que fica fora do git e do ZIP, o programa fechava com um erro logo ao abrir. Também apontou a falta da Ficha da CitizenTech no README, a falta da origem dos dados, o traceback ao apertar Ctrl+C no menu e o nome `prompt.md` citado na página 32.

**Ajuste:** escolhi quais apontamentos corrigir ("Corrija 1, 2, 3, 4, 6, 7 e 8"). Deixei de fora a troca do Flask, que é uma escolha consciente já explicada na seção 7. As correções foram:

- **modo local em JSON:** sem `MONGODB_URI`, os dados ficam em `dados_locais/*.json`, carregados sozinhos no primeiro uso. O professor roda `python main.py` sem internet e sem banco. Isso também cumpre a persistência em JSON com leitura e gravação;
- Ctrl+C e fim da entrada no menu encerram o programa com uma mensagem, sem traceback;
- README com a Ficha da CitizenTech, a origem dos dados, o menu como primeiro passo do "Como rodar" e a explicação dos trechos mais técnicos;
- o arquivo `prompt.md`, que aponta para este.

## 5. Funcionalidades desenvolvidas com auxílio da IA

- **Regras de negócio** (`regras.py`): cálculo do IPV com os pesos públicos, faixas e prazos, deduplicação por distância (fórmula de Haversine), créditos e limite de resgate, validade dos alertas e pesquisa binária.
- **Acesso** (`servicos/acesso.py`): cadastro, login, sessões por token separadas entre app e painel, troca de senha por código de 6 números que vence em 15 minutos e aceita 5 tentativas.
- **App do cidadão** (`servicos/chamados.py` e `servicos/conta.py`): reporte com endereço pela via mais próxima, seguir um chamado, confirmar o reparo com foto, rotas e alertas, preferências de aviso, carteira e resgate.
- **Painel do gestor** (`servicos/painel.py`): fila do dia pelo IPV, lista com filtros e paginação, despacho, encaminhamento, agendamento, descarte, revisão do IPV, vistoria, reabertura, prestadoras, indicadores, relatórios e mapa operacional.
- **Dados abertos** (`servicos/dados_abertos.py`): totais por subprefeitura com agregação do MongoDB, indicadores e ranking das prestadoras, sem dados pessoais.
- **Modo local** (`banco_local.py`): as coleções guardadas em arquivos JSON, imitando a parte do PyMongo que o projeto usa, para rodar sem MongoDB.
- **Documentação Swagger** (`app.py` e as docstrings das rotas), **seed** (`seed.py` e `dados/*.json`), **menu no terminal** (`main.py`), **testes** (`testes/`), `README.md`, os vídeos em `docs/videos/` e este arquivo.

**Sugestões da IA que mudaram o pedido original:**

- Exportar os dados de demonstração do mock do frontend para `dados/*.json`, para que o backend e o frontend contem a mesma história. Como as datas ficam fixas no arquivo, o `seed.py` as desloca para o momento da carga.
- Guardar as senhas com PBKDF2 e sal (biblioteca padrão), no lugar do SHA-256 sem sal que o mock do frontend usa.
- Encerrar todas as sessões da conta quando a senha é trocada.
- Recusar ações que não fazem sentido para o status do chamado (por exemplo, despachar um chamado já despachado ou reabrir um que nunca foi reparado), com o código 409.
- Avisar todas as pessoas que seguem um chamado, e não só quem o reportou, como estava anotado como pendência no frontend.
- Marcar `sugerirRecapeamento` quando um ponto falha 3 vezes, regra que estava no plano do frontend e ainda não existia.

## 6. Como os resultados foram verificados, testados e ajustados

- **Testes automatizados:** 75 testes com `unittest` cobrem as regras de negócio, os utilitários, o acesso, os serviços, as rotas da API e o modo local. Rodam com `python -m unittest discover -s testes -t .`, sem internet e sem tocar no Atlas.
- **Testes das rotas contra o MongoDB Atlas:** cada grupo de rotas foi chamado com o cliente de testes do Flask antes do commit, incluindo os casos de erro: senha errada (401), campos inválidos (400), token de cidadão no painel (401), equipe de outro órgão (409), despacho repetido (409), resgate abaixo do mínimo e acima do saldo, e resgate de outra pessoa (404).
- **Swagger no navegador:** as gravações do README executam as rotas pela própria página do Swagger, com login, token, erro de validação, acesso sem token e rota pública.
- **Menu no terminal:** executado com entradas simuladas, incluindo senha errada, texto no lugar de número, opção inexistente e protocolo que não existe.
- **Ajustes feitos durante a verificação:**
  - um teste do IPV esperava 80,5, mas a conta correta dá 76,5. O erro estava no teste, não na regra, e foi corrigido;
  - a saída no terminal do Windows quebrava ao imprimir a seta "→". Os testes passaram a rodar com `PYTHONIOENCODING=utf-8`; o código não precisou mudar;
  - o login do menu passou a encerrar a sessão ao sair, para não deixar tokens abertos no banco;
  - a coluna de prazo da fila no menu foi alargada, porque "Vencido há 10 dias" encostava na coluna seguinte;
  - o modo local foi conferido rodando o menu e todas as áreas da API numa cópia do projeto sem credenciais: login, fila, busca, despacho, descarte, cadastro, reporte, seguir, rotas, dados abertos e troca de senha. Os totais dos dados abertos bateram com o número de chamados, e as mudanças continuaram lá ao abrir o programa de novo.

## 7. Análise crítica

**Benefícios**

- **Mesma língua do frontend:** a ferramenta leu o desafio, as aulas e o frontend inteiro antes de escrever. Por isso os campos, os textos e as regras do backend são os mesmos do frontend.
- **Conflitos apontados antes do código:** ela notou que o pedido e o desafio pediam coisas diferentes (API ou menu, `IA.md` ou `prompts.md`) e perguntou antes de começar. Isso evitou entregar algo fora do formato pedido, que perde 10 pontos.
- **Segunda opinião:** sugestões como o hash com sal e a recusa de ações inválidas com 409 deixaram o backend mais seguro do que o pedido original.

**Limitações**

- **O código precisa de revisão humana.** A IA não sabe o que foi cobrado em sala além do que está nos PDFs. A aula de APIs é teórica e não mostra nenhum framework, então o uso do Flask e do Flasgger foi uma escolha, não um conteúdo visto em aula.
- **Testes no banco real:** os testes das rotas durante o desenvolvimento rodaram no banco de demonstração. Depois deles, é preciso rodar o `seed.py` de novo (ou a opção 8 do menu) para voltar aos dados originais.
- **A IA também erra:** o teste do IPV com o valor errado e o desalinhamento do menu só apareceram porque o resultado foi executado e conferido, e não apenas lido.

**Dificuldades**

- **Leitura do PDF:** o PDF do desafio não pôde ser lido como imagem no ambiente (faltava o poppler) e foi lido como texto, o que perde a formatação.
- **Nome do arquivo:** o documento cita o arquivo de IA com dois nomes diferentes, `prompts.md` nas páginas 22 e 31 e `prompt.md` na página 32. O conteúdo fica em `prompts.md`, e um `prompt.md` curto aponta para ele.
- **Um erro que só aparece fora da máquina de quem desenvolve:** o programa funcionava aqui porque as credenciais estavam no disco. Só a revisão contra o desafio mostrou que o ZIP, sem elas, não abriria. Daí veio o modo local.
- **Gravar um programa de terminal:** um navegador não grava o terminal. O vídeo do menu foi feito rodando o `main.py` de verdade com entradas roteirizadas e reproduzindo a saída capturada.
