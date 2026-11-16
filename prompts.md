# prompts.md · Uso de Inteligência Artificial no backend

Este arquivo documenta como ferramentas de Inteligência Artificial foram usadas no desenvolvimento do backend em Python do **Olho na Via**, como pede a página 31 do documento do desafio. Ele registra apenas interações que de fato aconteceram.

## 1. Ferramentas utilizadas

| Ferramenta | Tipo | Finalidade |
| --- | --- | --- |
| **Claude Code** (Anthropic) | Agente de programação no terminal | Ler o documento do desafio, os materiais de aula e o frontend; propor a arquitetura; escrever o código, os testes e a documentação; executar os testes e conferir as rotas contra o MongoDB Atlas; fazer os commits. |

Nenhuma outra ferramenta de IA foi usada no backend.

## 2. Prompts utilizados

O desenvolvimento partiu de um único pedido, seguido de duas decisões respondidas pelo grupo.

**Pedido inicial:**

> Certo, agora faça a implementação do repositório do backend em python. As instruções estão em @"Desafio-FIAP-GS-CitizenTech 1ES Paulista e Lins.pdf" entre as páginas 29 e 32. Não precisa fazer a integração dele com o frontend de fato ainda, mas no repositório do front tem documentado todas as rotas e funcionalidades que terão. Os materiais utilizados em sala estão em backend/referencias, além dos descritos no documento do desafio. Implemente o código na pasta backend sem fugir muito dos conceitos ensinados em aula, não insira comentários desnecessários, faça commits incrementais seguindo a pratica de conventional commits, faça uma documentação com swagger e implemente um arquivo IA.md que faça sentido com o projeto. Para banco de dados utilize o mongodb, já fiz a configuração no MongoDB Atlas as credenciais estão em atlas-credentials.env, crie um seed do banco de dados também.

**Decisões pedidas pela IA ao grupo.** Ao ler as páginas 29 a 32, a ferramenta apontou que o desafio exige menu de opções, persistência em JSON e o arquivo `prompts.md`, enquanto o pedido falava em API com Swagger, MongoDB e `IA.md`. Ela perguntou como seguir, e o grupo escolheu:

1. **Arquitetura híbrida:** API Flask com Swagger e MongoDB, mais um menu no terminal sobre os mesmos serviços, com JSON no seed e na exportação.
2. **Nome do arquivo:** `prompts.md`, como pede o desafio, no lugar de `IA.md`.

## 3. Funcionalidades desenvolvidas com auxílio da IA

Todo o código deste repositório foi escrito pela ferramenta a partir do pedido acima, seguindo as regras de negócio que já estavam no frontend (`app/domain/regras.ts` e `app/domain/painel.ts`):

- **Regras de negócio** (`regras.py`): cálculo do IPV com os pesos públicos, faixas e prazos, deduplicação por distância (fórmula de Haversine), créditos e limite de resgate, validade dos alertas e pesquisa binária.
- **Acesso** (`servicos/acesso.py`): cadastro, login, sessões por token separadas entre app e painel, troca de senha por código de 6 números que vence em 15 minutos e aceita 5 tentativas.
- **App do cidadão** (`servicos/chamados.py` e `servicos/conta.py`): reporte com endereço pela via mais próxima, seguir um chamado, confirmar o reparo com foto, rotas e alertas, preferências de aviso, carteira e resgate.
- **Painel do gestor** (`servicos/painel.py`): fila do dia pelo IPV, lista com filtros e paginação, despacho, encaminhamento, agendamento, descarte, revisão do IPV, vistoria, reabertura, prestadoras, indicadores, relatórios e mapa operacional.
- **Dados abertos** (`servicos/dados_abertos.py`): totais por subprefeitura com agregação do MongoDB, indicadores e ranking das prestadoras, sem dados pessoais.
- **Documentação Swagger** (`app.py` e as docstrings das rotas), **seed** (`seed.py` e `dados/*.json`), **menu no terminal** (`main.py`), **testes** (`testes/test_regras.py`), `README.md` e este arquivo.

**Sugestões da IA que mudaram o pedido original:**

- Exportar os dados de demonstração do mock do frontend para `dados/*.json`, para que o backend e o frontend contem a mesma história. Como as datas ficam fixas no arquivo, o `seed.py` as desloca para o momento da carga.
- Guardar as senhas com PBKDF2 e sal (biblioteca padrão), no lugar do SHA-256 sem sal que o mock do frontend usa.
- Encerrar todas as sessões da conta quando a senha é trocada.
- Recusar ações que não fazem sentido para o status do chamado (por exemplo, despachar um chamado já despachado ou reabrir um que nunca foi reparado), com o código 409.
- Avisar todas as pessoas que seguem um chamado, e não só quem o reportou, como estava anotado como pendência no frontend.
- Marcar `sugerirRecapeamento` quando um ponto falha 3 vezes, regra que estava no plano do frontend e ainda não existia.

## 4. Como os resultados foram verificados, testados e ajustados

- **Testes automatizados:** 13 testes com `unittest` cobrem o IPV, as faixas, o prazo vencido, a deduplicação, a distância, o resgate, a validação de senha, os alertas e a pesquisa binária. Rodam com `python -m unittest discover -s testes -t .`.
- **Testes unitários dos serviços e da API:** num segundo pedido ("Faça a implantação de testes unitários no backend."), a ferramenta acrescentou testes para o acesso, as ações do painel, os créditos, os utilitários e as rotas da API, chegando a 68 testes. O banco é trocado por objetos falsos com `unittest.mock`, então os testes rodam sem internet e sem mexer nos dados do Atlas.
- **Testes das rotas contra o MongoDB Atlas:** cada grupo de rotas foi chamado com o cliente de testes do Flask antes do commit, incluindo os casos de erro: senha errada (401), campos inválidos (400), token de cidadão no painel (401), equipe de outro órgão (409), despacho repetido (409), resgate abaixo do mínimo e acima do saldo, e resgate de outra pessoa (404).
- **Menu no terminal:** executado com entradas simuladas, incluindo senha errada, texto no lugar de número, opção inexistente e protocolo que não existe.
- **Ajustes feitos durante a verificação:**
  - um teste do IPV esperava 80,5, mas a conta correta dá 76,5. O erro estava no teste, não na regra, e foi corrigido;
  - a saída no terminal do Windows quebrava ao imprimir a seta "→". Os testes passaram a rodar com `PYTHONIOENCODING=utf-8`; o código não precisou mudar;
  - o login do menu passou a encerrar a sessão ao sair, para não deixar tokens abertos no banco.

## 5. Análise crítica

**Benefícios.** A ferramenta leu o desafio, as aulas e o frontend inteiro antes de escrever, e por isso o backend fala a mesma língua do frontend: os mesmos campos, os mesmos textos e as mesmas regras. Ela também apontou o conflito entre o pedido e as exigências do desafio antes de começar, o que evitou entregar algo fora do formato pedido.

**Limitações.** O código gerado precisa de revisão humana. A IA não sabe o que foi cobrado em sala além do que está nos PDFs: a aula de APIs é teórica e não mostra nenhum framework, então o uso do Flask e do flasgger foi uma escolha, não um conteúdo visto em aula. Os testes das rotas rodaram no banco real de demonstração; por isso, depois deles, é preciso rodar o `seed.py` de novo para voltar aos dados originais.

**Dificuldades.** O PDF do desafio não pôde ser lido como imagem no ambiente (faltava o poppler) e foi lido como texto, o que perde a formatação. O documento também cita o arquivo de IA com dois nomes diferentes (`prompts.md` na página 31 e `prompt.md` na página 32); o grupo ficou com `prompts.md`.
