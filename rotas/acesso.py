from flask import Blueprint, jsonify

from servicos import acesso
from rotas.sessao import corpo, token_da_requisicao

rotas_de_acesso = Blueprint("acesso", __name__, url_prefix="/api/acesso")


@rotas_de_acesso.post("/cadastro")
def cadastrar():
    """Cria a conta de um cidadão e já abre a sessão.
    ---
    tags: [Acesso]
    parameters:
      - in: body
        name: corpo
        required: true
        schema:
          type: object
          required: [nome, email, bairro, senha, senhaRepetida, aceite]
          properties:
            nome: {type: string, example: Ana Souza}
            email: {type: string, example: ana@exemplo.com}
            whatsapp: {type: string, example: (11) 91234-5678}
            bairro: {type: string, example: Butantã}
            senha: {type: string, example: senha1234}
            senhaRepetida: {type: string, example: senha1234}
            aceite: {type: boolean, example: true}
    responses:
      201: {description: Conta criada, schema: {$ref: '#/definitions/Sessao'}}
      400: {description: Campos inválidos, schema: {$ref: '#/definitions/Erro'}}
      409: {description: E-mail já cadastrado, schema: {$ref: '#/definitions/Erro'}}
    """
    return jsonify(acesso.cadastrar(corpo())), 201


@rotas_de_acesso.post("/entrar")
def entrar():
    """Confere e-mail e senha e devolve o token de sessão.
    ---
    tags: [Acesso]
    parameters:
      - in: body
        name: corpo
        required: true
        schema:
          type: object
          required: [email, senha]
          properties:
            email: {type: string, example: juliana@demo.olhonavia.com.br}
            senha: {type: string, example: olhonavia}
            area: {type: string, enum: [app, painel], default: app}
    responses:
      200: {description: Sessão aberta, schema: {$ref: '#/definitions/Sessao'}}
      400: {description: Campos inválidos, schema: {$ref: '#/definitions/Erro'}}
      401: {description: E-mail ou senha não conferem, schema: {$ref: '#/definitions/Erro'}}
    """
    return jsonify(acesso.entrar(corpo()))


@rotas_de_acesso.post("/demonstracao")
def entrar_como_persona():
    """Entra como uma persona de demonstração, sem senha (só no modo de demonstração).
    ---
    tags: [Acesso]
    parameters:
      - in: body
        name: corpo
        required: true
        schema:
          type: object
          required: [perfil]
          properties:
            perfil: {type: string, enum: [juliana, lourdes, marta, rafael, carla], example: juliana}
            area: {type: string, enum: [app, painel], default: app}
    responses:
      200: {description: Sessão aberta, schema: {$ref: '#/definitions/Sessao'}}
      400: {description: Perfil inválido, schema: {$ref: '#/definitions/Erro'}}
    """
    return jsonify(acesso.entrar_como_persona(corpo()))


@rotas_de_acesso.post("/sair")
def sair():
    """Encerra a sessão do token enviado.
    ---
    tags: [Acesso]
    security: [{Bearer: []}]
    responses:
      204: {description: Sessão encerrada}
      401: {description: Sem token, schema: {$ref: '#/definitions/Erro'}}
    """
    acesso.sair(token_da_requisicao())
    return "", 204


@rotas_de_acesso.post("/recuperar-senha")
def recuperar_senha():
    """Gera um código de 6 números para trocar a senha.

    A resposta é igual exista ou não a conta, para não revelar quem está cadastrado.
    No modo de demonstração, o código volta em codigoDeDemonstracao.
    ---
    tags: [Acesso]
    parameters:
      - in: body
        name: corpo
        required: true
        schema:
          type: object
          required: [email]
          properties:
            email: {type: string, example: marta@demo.olhonavia.com.br}
            area: {type: string, enum: [app, painel], default: app}
    responses:
      201:
        description: Pedido criado
        schema:
          type: object
          properties:
            pedidoId: {type: string}
            expiraEm: {type: string, format: date-time}
            codigoDeDemonstracao: {type: string, x-nullable: true}
      400: {description: E-mail inválido, schema: {$ref: '#/definitions/Erro'}}
    """
    return jsonify(acesso.pedir_codigo(corpo())), 201


@rotas_de_acesso.post("/redefinir-senha")
def redefinir_senha():
    """Troca a senha com o código recebido e encerra as sessões abertas da conta.
    ---
    tags: [Acesso]
    parameters:
      - in: body
        name: corpo
        required: true
        schema:
          type: object
          required: [pedidoId, codigo, senha, senhaRepetida]
          properties:
            pedidoId: {type: string}
            codigo: {type: string, example: "123456"}
            senha: {type: string, example: nova12345}
            senhaRepetida: {type: string, example: nova12345}
    responses:
      204: {description: Senha trocada}
      400: {description: Código incorreto ou vencido, schema: {$ref: '#/definitions/Erro'}}
    """
    acesso.redefinir_senha(corpo())
    return "", 204
