# Olho na Via · Backend em Python

Aplicação Python do **Olho na Via**, projeto da Global Solution FIAP 2026.2 (CitizenTech). Ela processa os dados da zeladoria das vias de São Paulo e toma as decisões do sistema:

- calcula o **Índice de Prioridade da Via (IPV)** de cada chamado e a faixa de prazo (crítico em 24 h, alto em 72 h ou plano semanal);
- junta reportes do mesmo ponto (até 15 m, mesma categoria) para não abrir chamados repetidos;
- decide o que a gestão deve fazer com cada caso (despachar, encaminhar ao órgão, agendar ou só acompanhar);
- valida alertas de rota (expiram em 30 min; "intransitável" exige câmera fixa ou duas fontes);
- aplica as regras dos créditos cidadãos (pontos por reporte validado e por foto de reparo, resgate mínimo e limite mensal).

São duas formas de usar, sobre as mesmas regras e o mesmo banco:

| Interface | Para quem | Como abrir |
| --- | --- | --- |
| **API REST** (Flask) com documentação **Swagger** | App do cidadão, painel do gestor e portal de dados abertos (frontend) | `python app.py` e acesse `http://localhost:5000/docs/` |
| **Menu no terminal** | Gestor da zeladoria | `python main.py` |

Os dados ficam no **MongoDB Atlas**. Os dados de demonstração ficam em arquivos **JSON** na pasta `dados/` e são carregados pelo `seed.py`. O menu exporta os chamados para JSON na pasta `exportacoes/`.

## Como rodar

Requisitos: Python 3.11 ou mais novo e acesso a um cluster MongoDB.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux e macOS
pip install -r requirements.txt
```

Configure a conexão. O programa lê, nesta ordem, `atlas-credentials.env`, `.env` e as variáveis de ambiente (veja `.env.example`):

```
MONGODB_URI=mongodb+srv://usuario:senha@cluster.exemplo.mongodb.net/
MONGODB_BANCO=olho_na_via
OLHO_MODO_DEMONSTRACAO=1
OLHO_PORTA=5000
```

Carregue os dados de demonstração (apaga o que houver no banco `olho_na_via`):

```bash
python seed.py
```

Suba a API ou abra o menu:

```bash
python app.py
python main.py
```

Rode os testes das regras de negócio:

```bash
python -m unittest discover -s testes -t .
```

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

## Rotas da API

A documentação completa, com exemplos e o botão **Authorize** para o token, fica em `/docs/` (especificação em `/openapi.json`). As rotas protegidas usam o cabeçalho `Authorization: Bearer <token>`, recebido no login. O app e o painel têm sessões separadas: o token de um cidadão não abre o painel.

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
banco.py          conexão com o MongoDB
regras.py         regras de negócio: IPV, prazos, deduplicação, créditos, alertas e busca
validacao.py      validação dos dados recebidos
erros.py          exceções da aplicação, cada uma com o seu código HTTP
seguranca.py      hash de senha (PBKDF2), token de sessão e código de recuperação
datas.py          datas em ISO 8601 e fuso de São Paulo
registro.py       logs em logs/olho_na_via.log
servicos/         acesso, chamados, conta, painel e dados abertos
rotas/            rotas da API, uma por área
dados/            dados de demonstração em JSON
testes/           testes das regras de negócio (unittest)
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
| Arquivos JSON | `seed.py` (leitura de `dados/`), exportação em `main.py` |
| Logs | `registro.py` e `logging` nos serviços |
| Banco de dados não relacional | MongoDB com `pymongo`: documentos aninhados, índices e agregação (`$group` em `servicos/dados_abertos.py`) |
| Algoritmos de busca | pesquisa binária por protocolo (`regras.pesquisa_binaria`, opção 2 do menu) |
| Orientação a objetos | hierarquia de exceções em `erros.py` |
| APIs REST | rotas com verbos e códigos HTTP corretos, JSON e documentação Swagger |

## Privacidade

O Olho na Via olha para a via, não para as pessoas. As senhas são guardadas só como hash PBKDF2 com sal. O portal de dados abertos devolve apenas números agregados, sem fotos e sem dados pessoais. A troca de senha não revela se um e-mail tem conta.
