<p align="center">
  <img src="docs/logo.svg" alt="Olho na Via" width="280" />
</p>

<h3 align="center">Backend · aplicação Python, API REST com Swagger e menu no terminal</h3>

<p align="center">
  FIAP · Global Solution 2026.2 · CitizenTech · Engenharia de Software, 1º ano
</p>

---

## Ficha da CitizenTech

| Campo | Olho na Via |
| --- | --- |
| Nome da CitizenTech | **Olho na Via**: fiscalização urbana com IA |
| Cidade e bairro | São Paulo (SP). Piloto proposto: linhas de ônibus que cruzam a região central e a Av. Paulista (entorno da FIAP Paulista) e seguem até bairros da periferia, em duas subprefeituras a definir com a Prefeitura. Os dados de demonstração usam Butantã, Lapa e Pinheiros. |
| Cidadão beneficiado | Quem usa a rua todos os dias: passageiros de ônibus, motociclistas e entregadores, ciclistas, pedestres (principalmente idosos e pessoas com deficiência) e moradores de áreas que alagam. Também o gestor público, que precisa decidir onde agir primeiro. |
| Problema, em uma frase | Em São Paulo, buracos, alagamentos, faixas apagadas e semáforos apagados só entram na fila de reparo quando alguém reclama, e ninguém confere de forma sistemática se o conserto foi bem feito. |
| Como funciona | Um dispositivo IoT com câmera, acelerômetro e GPS, instalado em ônibus, e a análise das câmeras do Smart Sampa detectam problemas com IA. O sistema abre o chamado no órgão responsável, prioriza pela gravidade e, quando o ônibus passa de novo, confirma se o reparo foi feito. Também avisa cidadãos e ambulâncias sobre vias alagadas ou bloqueadas. Cidadãos contribuem pelo app e com um kit próprio em troca de créditos. |
| O que cada parte faz | **Sensor (Edge/ESP32):** mede impacto, lâmina d'água e luz e decide o estado sozinho · **Lógica (Python, este repositório):** organiza os chamados, calcula a prioridade, decide a ação da gestão e guarda os dados em JSON ou no MongoDB · **Matemática:** modela o crescimento do buraco e o custo acumulado do atraso · **Interface e Interação (React):** app do cidadão e painel do gestor · **Experiência:** jornada, requisitos e roadmap · **Pitch:** a história em 3 minutos. |
| Link do repositório | Backend: [github.com/olho-na-via/backend](https://github.com/olho-na-via/backend) · Frontend: [github.com/olho-na-via/frontend](https://github.com/olho-na-via/frontend) |
| Indicador de impacto | **Tempo entre o surgimento do problema e o reparo confirmado** (meta: de 6 para no máximo 3 dias nas áreas piloto) e **% de problemas detectados antes de qualquer reclamação** (meta: 60% ou mais). |
| ODS conectados | `ODS 11` `ODS 9` `ODS 3` `ODS 13` `ODS 10` `ODS 16 · complementar` |
| Equipe | **Erick Nathan Capito Pereira** · RM573635 |

## Sobre

Aplicação Python do **Olho na Via**, projeto de fiscalização urbana com IA para São Paulo. Ônibus e câmeras públicas detectam buracos, alagamentos, faixas apagadas e semáforos apagados. Esta aplicação processa os dados da zeladoria das vias e toma as decisões do sistema:

- calcula o **Índice de Prioridade da Via (IPV)** de cada chamado e a faixa de prazo (crítico em 24 h, alto em 72 h ou plano semanal);
- junta reportes do mesmo ponto (até 15 m, mesma categoria) para não abrir chamados repetidos;
- decide o que a gestão deve fazer com cada caso (despachar, encaminhar ao órgão, agendar ou só acompanhar);
- valida alertas de rota (expiram em 30 min; "intransitável" exige câmera fixa ou duas fontes);
- aplica as regras dos créditos cidadãos (pontos por reporte validado e por foto de reparo, resgate mínimo e limite mensal).

São duas formas de usar, sobre as mesmas regras e o mesmo banco:

| Interface | Para quem | Como abrir |
| --- | --- | --- |
| **Menu no terminal** (entrega principal da disciplina) | Gestor da zeladoria | `python main.py` |
| **API REST** (Flask) com documentação **Swagger** | App do cidadão, painel do gestor e portal de dados abertos (frontend) | `python app.py` e acesse `http://localhost:5000/docs/` |

Os dados ficam em um de dois lugares:

| Modo | Quando | Onde ficam os dados |
| --- | --- | --- |
| **Local** (padrão) | Sem `MONGODB_URI` configurado | Um arquivo **JSON** por coleção, na pasta `dados_locais/`. Cada alteração é lida e gravada nesses arquivos |
| **MongoDB Atlas** | Com `MONGODB_URI` no `.env` ou em `atlas-credentials.env` | No banco `olho_na_via` do cluster |

Nos dois modos, os dados de demonstração saem dos arquivos **JSON** da pasta `dados/` e são carregados pelo `seed.py`. O menu também exporta os chamados para JSON na pasta `exportacoes/`.

## Funcionalidades

| Área | O que a aplicação faz |
| --- | --- |
| **Acesso** | Cadastro, login com sessões separadas para o app e o painel, saída e troca de senha por código de 6 números (vence em 15 minutos, aceita 5 tentativas) |
| **App do cidadão** | Mapa de chamados, reporte com deduplicação e endereço pela via mais próxima, seguir um chamado, confirmar o reparo com foto, rotas cadastradas e alertas, avisos, preferências, carteira de créditos e resgate |
| **Painel do gestor** | Fila do dia pelo IPV com a ação sugerida, lista com filtros e paginação, despacho, encaminhamento ao órgão, agendamento, descarte, revisão do IPV, vistoria, reabertura, equipes, prestadoras, indicadores, relatórios e mapa operacional |
| **Dados abertos** | Chamados por subprefeitura (agregação do MongoDB), indicadores mensais e ranking das prestadoras, sem dados pessoais |
| **Menu no terminal** | Fila do dia, busca por protocolo (pesquisa binária), despacho, descarte, reabertura, resumo por categoria e faixa, exportação para JSON e restauração dos dados de demonstração |

## Funcionalidades em vídeo

Gravações da aplicação rodando com os dados de demonstração no MongoDB Atlas. Clique em uma prévia para abrir o vídeo em MP4, em qualidade completa.

### Documentação Swagger

Visão geral das rotas, login como gestora em `POST /api/acesso/entrar`, uso do token no botão **Authorize** e consulta da fila do dia em `GET /api/painel/fila`.

[![Swagger: login, Authorize e fila do dia](docs/videos/01-swagger.gif)](docs/videos/01-swagger.mp4)

### Validação, autenticação e dados abertos

Login com e-mail inválido e senha vazia (400, com a mensagem de cada campo), fila do painel sem token (401) e indicadores públicos em `GET /api/dados-abertos/indicadores`, que não pedem login.

[![Erros de validação, 401 e dados abertos](docs/videos/02-erros-e-dados-abertos.gif)](docs/videos/02-erros-e-dados-abertos.mp4)

### Menu no terminal

Login com senha errada e depois certa, fila do dia, opção inválida, busca do chamado 48213 com o IPV explicado, despacho para uma equipe, resumo por categoria, exportação para JSON e restauração dos dados.

[![Menu no terminal](docs/videos/03-menu-terminal.gif)](docs/videos/03-menu-terminal.mp4)

> O vídeo do menu reproduz a saída de uma execução real do `main.py`. As entradas foram digitadas por um roteiro, e a gravação mostra o texto na ordem e com as respostas que o programa deu.

## Stack

| Uso | Tecnologia |
| --- | --- |
| Linguagem | [Python](https://www.python.org) 3.11 ou mais novo |
| API REST | [Flask](https://flask.palletsprojects.com) 3.1 |
| Documentação da API | [Flasgger](https://github.com/flasgger/flasgger) 0.9.7 (Swagger UI e especificação OpenAPI 2.0) |
| Banco de dados | Arquivos JSON locais (padrão) ou [MongoDB Atlas](https://www.mongodb.com/atlas), acessado com [PyMongo](https://pymongo.readthedocs.io) 4.20 |
| Dados de demonstração e exportação | Arquivos JSON (`json` da biblioteca padrão) |
| Senhas e tokens | `hashlib` (PBKDF2 com sal) e `secrets`, da biblioteca padrão |
| Logs | `logging`, em `logs/olho_na_via.log` |
| Testes | `unittest` e `unittest.mock`, sem banco real |

As únicas dependências externas são as três do `requirements.txt`. O resto vem da biblioteca padrão do Python.

## Arquitetura

A API e o menu são duas portas de entrada para os mesmos serviços. As regras de negócio não sabem de HTTP nem de terminal, e as leituras e gravações no banco ficam nos serviços.

```mermaid
flowchart TD
    F["Frontend<br/>(app, painel e dados abertos)"] -->|HTTP + JSON| A
    G["Gestor no terminal"] --> M
    A["app.py + rotas/<br/>Flask, Swagger e tratamento de erros"] --> S
    M["main.py<br/>menu de opções"] --> S
    S["servicos/<br/>acesso, chamados, conta, painel e dados abertos"] --> R
    S --> V["validacao.py · erros.py · seguranca.py · datas.py"]
    S --> B["banco.py"]
    R["regras.py<br/>IPV, prazos, deduplicação, créditos, alertas e busca"]
    B -->|com MONGODB_URI| D[("MongoDB Atlas")]
    B -->|sem MONGODB_URI| L["banco_local.py<br/>dados_locais/*.json"]
    J["dados/*.json"] -->|seed.py| D
    J -->|seed.py| L
```

| Camada | Onde | Responsabilidade |
| --- | --- | --- |
| Entrada | `app.py`, `rotas/`, `main.py` | Receber a requisição ou a opção do menu, conferir a sessão, chamar o serviço e devolver a resposta (JSON com o código HTTP certo, ou texto no terminal) |
| Serviços | `servicos/` | Os casos de uso: abrir um chamado, despachar, resgatar créditos. Leem e gravam no banco e aplicam as regras |
| Regras | `regras.py` | Funções puras: IPV, faixa, prazo, ação sugerida, distância, deduplicação, créditos e pesquisa binária. São as mais testadas |
| Apoio | `validacao.py`, `erros.py`, `seguranca.py`, `datas.py`, `registro.py` | Validação dos campos, exceções com código HTTP, hash de senha e token, datas no fuso de São Paulo e logs |
| Dados | `banco.py`, `banco_local.py`, `seed.py`, `dados/` | Escolha entre o MongoDB e os arquivos JSON locais, e carga dos dados de demonstração |

Cada exceção de `erros.py` carrega o seu código HTTP. A API transforma qualquer uma delas na mesma resposta de erro, e o menu mostra a mensagem sem fechar o programa.

## Documentação Swagger

Com a API no ar (`python app.py`), a documentação interativa fica em **`http://localhost:5000/docs/`**, e a especificação OpenAPI em `http://localhost:5000/openapi.json`. A raiz `/` redireciona para a documentação.

- As rotas estão agrupadas por área: Acesso, Cidadão (chamados, alertas, conta e créditos), Painel (fila, chamados, ações, prestadoras e relatórios) e Dados abertos.
- Cada rota traz a descrição, os parâmetros, o corpo de exemplo e as respostas possíveis, inclusive as de erro.
- Os modelos `Erro`, `Sessao`, `Chamado` e `Rota` aparecem no fim da página.
- Para testar uma rota protegida, entre em `POST /api/acesso/entrar` com uma conta de demonstração. Depois, clique em **Authorize** e cole `Bearer <token>`. As rotas com cadeado passam a usar esse token.

A descrição de cada rota fica na docstring da própria função, em `rotas/`, e o modelo geral (título, segurança e modelos) fica em `MODELO_DO_SWAGGER`, no `app.py`.

## Como rodar

Requisito: Python 3.11 ou mais novo. Não é preciso internet nem banco de dados.

**1. Instale as dependências**

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux e macOS
pip install -r requirements.txt
```

**2. Abra o menu do gestor**

```bash
python main.py
```

Entre com `carla@demo.olhonavia.com.br` e a senha `olhonavia`. No primeiro uso, o programa carrega sozinho os dados de demonstração em `dados_locais/`. A opção 8 do menu volta os dados ao estado inicial.

**3. (Opcional) Suba a API e abra o Swagger**

```bash
python app.py
```

A documentação fica em `http://localhost:5000/docs/`.

**4. (Opcional) Use o MongoDB Atlas no lugar dos arquivos JSON**

Crie um `.env` (veja `.env.example`). O programa lê, nesta ordem, `atlas-credentials.env`, `.env` e as variáveis de ambiente:

```
MONGODB_URI=mongodb+srv://usuario:senha@cluster.exemplo.mongodb.net/
MONGODB_BANCO=olho_na_via
OLHO_MODO_DEMONSTRACAO=1
OLHO_PORTA=5000
```

Depois, carregue os dados de demonstração no banco (apaga o que houver no banco `olho_na_via`):

```bash
python seed.py
```

**Testes unitários**

```bash
python -m unittest discover -s testes -t .
```

Os testes não usam o MongoDB: `testes/apoio.py` troca as coleções por objetos falsos (`unittest.mock`), então rodam sem internet e não mexem nos dados do Atlas.

| Arquivo | O que testa |
| --- | --- |
| `test_regras.py` | IPV, faixas, prazos, deduplicação, créditos, senha, alertas e pesquisa binária |
| `test_utilitarios.py` | hash de senha, validação dos campos, exceções, datas, leitura do `.env` e deslocamento de datas do seed |
| `test_acesso.py` | login, sessões por área, cadastro, código de troca de senha e tentativas |
| `test_servicos.py` | ações do painel e status permitidos, reabertura e recapeamento, confirmação de reparo, resgate de créditos e preferências |
| `test_api.py` | rotas da API: 401 sem token, sessão de outra área, formato dos erros, 404/405, banco fora do ar (503), erro inesperado (500) e Swagger |
| `test_banco_local.py` | modo local em JSON: filtros, projeção, ordem, atualizações, remoção, agregação e leitura do arquivo gravado |

## Contas de demonstração

Todas usam a senha `olhonavia`.

| Área | E-mail | Persona |
| --- | --- | --- |
| App do cidadão | `juliana@demo.olhonavia.com.br` | Ciclista, reporta problemas |
| App do cidadão | `lourdes@demo.olhonavia.com.br` | Pedestre, 71 anos |
| App do cidadão | `marta@demo.olhonavia.com.br` | Mora em área de alagamento, recebe alertas de rota |
| App do cidadão | `rafael@demo.olhonavia.com.br` | Fiscal da Via, troca pontos por créditos |
| Painel do gestor | `carla@demo.olhonavia.com.br` | Gestora da zeladoria do Butantã |

Com `OLHO_MODO_DEMONSTRACAO=1`, a rota `POST /api/acesso/demonstracao` entra como uma persona sem senha, e a troca de senha devolve o código na resposta (não há envio de e-mail).

## Origem dos dados

**Todos os dados deste repositório são simulados.** Nenhuma pessoa, chamado ou conta é real.

- **Pessoas:** as personas (Juliana, Lourdes, Marta, Rafael e a gestora Carla) foram criadas a partir das entrevistas e das jornadas do Sumário Executivo. Os e-mails usam o domínio fictício `demo.olhonavia.com.br`.
- **Chamados, alertas, equipes, prestadoras e indicadores:** foram escritos à mão para o mock do frontend (json-server) e exportados para `dados/*.json`, para que o backend e o frontend contem a mesma história. O `seed.py` desloca as datas para o momento da carga, para que os prazos façam sentido em qualquer dia.
- **Ruas, bairros e subprefeituras:** são nomes reais de São Paulo, com coordenadas aproximadas (Butantã, Lapa e Pinheiros), usados só para dar contexto ao mapa. Os problemas apontados nelas são inventados.
- **Pesos do IPV, prazos e metas:** vêm do Sumário Executivo do projeto, ajustados com o feedback das entrevistas feitas pela equipe.

## Rotas da API

A documentação completa de cada rota está no [Swagger](#documentação-swagger). As rotas protegidas usam o cabeçalho `Authorization: Bearer <token>`, recebido no login. O app e o painel têm sessões separadas: o token de um cidadão não abre o painel.

| Grupo | Rotas |
| --- | --- |
| Acesso | `POST /api/acesso/cadastro`, `/entrar`, `/demonstracao`, `/sair`, `/recuperar-senha`, `/redefinir-senha` |
| Cidadão · chamados | `GET /api/chamados`, `GET /api/chamados/{id}`, `POST /api/chamados`, `POST /api/chamados/{id}/confirmacao`, `PUT` e `DELETE /api/chamados/{id}/seguir`, `POST /api/chamados/{id}/avancar-etapa`, `GET /api/vias` |
| Cidadão · conta | `GET /api/eu`, `PATCH /api/eu/preferencias`, `GET /api/eu/chamados`, `GET /api/eu/notificacoes`, `POST /api/eu/notificacoes/lidas` |
| Cidadão · alertas | `GET /api/alertas`, `GET /api/eu/alertas`, `GET` e `POST /api/eu/rotas`, `PUT` e `DELETE /api/eu/rotas/{id}` |
| Cidadão · créditos | `GET /api/eu/creditos`, `POST /api/eu/resgates`, `GET /api/eu/resgates/{id}` |
| Painel | `GET /api/painel/eu`, `/fila`, `/chamados`, `/chamados/{id}`, `/equipes`, `/prestadoras`, `/prestadoras/{id}`, `/indicadores`, `/relatorios`, `/mapa` |
| Painel · ações | `POST /api/painel/chamados/{id}/despacho`, `/encaminhamento`, `/agendamento`, `/descarte`, `/revisao-ipv`, `/vistoria`, `/reabertura` |
| Dados abertos (público) | `GET /api/dados-abertos/chamados`, `/indicadores`, `/prestadoras` |

Os erros sempre voltam no mesmo formato, com o código HTTP certo (400, 401, 404, 409, 503):

```json
{ "erro": "Confira os campos destacados.", "campos": { "email": "Digite um e-mail válido, como nome@exemplo.com." } }
```

## Menu no terminal

```
  1. Ver a fila do dia
  2. Buscar chamado pelo protocolo
  3. Despachar chamado para uma equipe
  4. Descartar chamado (falso positivo)
  5. Reabrir chamado
  6. Resumo por categoria e faixa
  7. Exportar chamados para JSON
  8. Restaurar dados de demonstração
  0. Sair
```

O gestor entra com e-mail e senha (a senha não aparece na tela). Toda entrada é validada e repetida até ficar correta; erros de regra e de conexão aparecem como mensagens, sem derrubar o programa.

## Estrutura

```
app.py            API Flask, Swagger e tratamento de erros
main.py           menu no terminal
seed.py           carga dos dados de demonstração (dados/*.json → MongoDB)
config.py         leitura do .env e do atlas-credentials.env
banco.py          escolhe entre o MongoDB e o modo local
banco_local.py    modo local: cada coleção em um arquivo JSON
regras.py         regras de negócio: IPV, prazos, deduplicação, créditos, alertas e busca
validacao.py      validação dos dados recebidos
erros.py          exceções da aplicação, cada uma com o seu código HTTP
seguranca.py      hash de senha (PBKDF2), token de sessão e código de recuperação
datas.py          datas em ISO 8601 e fuso de São Paulo
registro.py       logs em logs/olho_na_via.log
servicos/         acesso, chamados, conta, painel e dados abertos
rotas/            rotas da API, uma por área
dados/            dados de demonstração em JSON
dados_locais/     dados do modo local (criada no primeiro uso, fora do git)
testes/           testes unitários (unittest), sem banco real
docs/             logo e gravações das funcionalidades
```

## Conceitos da disciplina aplicados

| Conceito | Onde |
| --- | --- |
| Menu de opções | `main.py` (`OPCOES` e o laço principal) |
| Validação de entradas | `validacao.py`, `ler_inteiro`, `ler_texto` e `confirmar` em `main.py` |
| `try/except` e exceções próprias | `erros.py` (herança de `Exception`), `config.py`, `main.py`, `seguranca.py`, `app.py` |
| `if/elif/else` e `match/case` | `regras.py` (`situacao_do_prazo`, `acao_da_fila`), `servicos/painel.py`, `main.py` |
| `while` e `for` | laços de entrada em `main.py`, `pesquisa_binaria`, cálculos em `regras.py` |
| Funções com parâmetros e retorno | todos os módulos |
| Listas, tuplas e dicionários | `CATEGORIAS`, `ORGAOS` (tuplas), `PESOS_IPV`, filas e resumos |
| Arquivos JSON | leitura e gravação de cada coleção em `banco_local.py` (modo local), `seed.py` (leitura de `dados/`) e exportação em `main.py` |
| Logs | `registro.py` e `logging` nos serviços |
| Banco de dados não relacional | MongoDB com `pymongo`: documentos aninhados, índices e agregação (`$group` em `servicos/dados_abertos.py`) |
| Algoritmos de busca | pesquisa binária por protocolo (`regras.pesquisa_binaria`, opção 2 do menu) |
| Orientação a objetos | hierarquia de exceções em `erros.py` e as classes `BancoLocal`, `ColecaoLocal` e `Cursor` em `banco_local.py` |
| APIs REST | rotas com verbos e códigos HTTP corretos, JSON e documentação Swagger |

## Os trechos mais técnicos, explicados

**IPV (`regras.calcular_ipv`).** Cada chamado tem cinco notas de 0 a 1: gravidade (G), exposição (E), vulnerabilidade de quem passa (V), reincidência (R) e tempo em aberto (T). O IPV é a soma ponderada `100 × (0,35·G + 0,25·E + 0,20·V + 0,10·R + 0,10·T)`. O resultado vai de 0 a 100: 70 ou mais é crítico (prazo de 24 h), de 40 a 70 é alto (72 h), e abaixo de 40 entra no plano semanal. A função também devolve quanto cada nota contribuiu, que é o que o menu mostra no detalhe do chamado.

**Distância entre dois pontos (`regras.distancia_em_metros`).** Latitude e longitude são ângulos sobre uma esfera, então não dá para usar a distância de uma reta. A fórmula de Haversine converte a diferença dos ângulos em radianos e calcula o arco entre os pontos sobre a Terra, com raio de 6.371 km. Com ela, o sistema junta reportes da mesma categoria a até 15 m (`achar_chamado_no_mesmo_ponto`) e acha a via mais próxima para montar o endereço.

**Pesquisa binária (`regras.pesquisa_binaria`, opção 2 do menu).** O menu ordena os chamados pelo protocolo e procura o número olhando sempre o meio da lista. Se o protocolo do meio for maior, descarta a metade de cima; se for menor, a de baixo. Com 103 chamados, acha qualquer protocolo em no máximo 7 comparações, contra até 103 de uma busca item por item.

**Senha guardada como hash (`seguranca.py`).** A senha nunca é gravada. O sistema gera um sal aleatório de 16 bytes (`secrets.token_hex`) e aplica o PBKDF2 com SHA-256 200 mil vezes (`hashlib.pbkdf2_hmac`). Grava só o resultado e o sal. No login, refaz a conta com a senha digitada e compara com `hmac.compare_digest`, que leva o mesmo tempo com acerto ou erro e não dá pista a quem tenta adivinhar. O sal faz duas senhas iguais virarem hashes diferentes.

**Agrupamento dos dados abertos (`servicos/dados_abertos.py`).** O portal precisa de totais por subprefeitura e por status. A etapa `$group` do MongoDB junta os chamados com a mesma combinação `{subprefeitura, status}` e soma 1 para cada um (`$sum: 1`). O Python depois soma os grupos em resolvidos, descartados e abertos com `match/case`. No modo local, `banco_local.agrupar` faz o mesmo com um dicionário.

**Modo local (`banco_local.py`).** Imita só a parte do PyMongo que o projeto usa, para que os serviços funcionem igual nos dois modos. Cada coleção vira uma lista de dicionários, lida do arquivo JSON na primeira consulta. Cada alteração (`insert_one`, `update_one`, `delete_one`...) muda a lista e regrava o arquivo inteiro. A gravação vai primeiro para um arquivo temporário e só depois troca o original (`os.replace`), para não corromper os dados se o programa fechar no meio.

## Privacidade

O Olho na Via olha para a via, não para as pessoas. As senhas são guardadas só como hash PBKDF2 com sal. O portal de dados abertos devolve apenas números agregados, sem fotos e sem dados pessoais. A troca de senha não revela se um e-mail tem conta.

## Uso de IA

O registro de como a IA foi usada no desenvolvimento está em [prompts.md](prompts.md), como pede o desafio. Como a página 32 cita o nome `prompt.md`, esse arquivo também existe e aponta para o `prompts.md`.

## Autor

Erick Nathan Capito Pereira · RM573635
