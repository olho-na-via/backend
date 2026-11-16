import logging

from flasgger import Swagger
from flask import Flask, jsonify, redirect
from pymongo.errors import PyMongoError
from werkzeug.exceptions import HTTPException

from config import CONFIG
from erros import ErroDaApi
from registro import configurar_logs
from rotas.acesso import rotas_de_acesso
from rotas.cidadao import rotas_do_cidadao
from rotas.painel import rotas_do_painel

logger = logging.getLogger(__name__)

MODELO_DO_SWAGGER = {
    "swagger": "2.0",
    "info": {
        "title": "Olho na Via · API",
        "description": (
            "API do Olho na Via: reportes da população, fila de reparos pelo Índice de Prioridade da Via (IPV), "
            "alertas de rota, créditos cidadãos e dados abertos. Para as rotas protegidas, entre em "
            "/api/acesso/entrar e clique em Authorize com o valor `Bearer <token>`."
        ),
        "version": "1.0.0",
    },
    "securityDefinitions": {
        "Bearer": {"type": "apiKey", "name": "Authorization", "in": "header", "description": "Bearer <token>"},
    },
    "definitions": {
        "Erro": {
            "type": "object",
            "properties": {
                "erro": {"type": "string", "example": "Confira os campos destacados."},
                "campos": {"type": "object", "additionalProperties": {"type": "string"}},
            },
        },
        "Sessao": {
            "type": "object",
            "properties": {
                "token": {"type": "string"},
                "expiraEm": {"type": "string", "format": "date-time"},
                "area": {"type": "string", "enum": ["app", "painel"]},
                "pessoa": {"type": "object"},
            },
        },
        "Chamado": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "example": "48213"},
                "protocolo": {"type": "string", "example": "48213"},
                "categoria": {"type": "string", "example": "buraco"},
                "titulo": {"type": "string"},
                "endereco": {"type": "string"},
                "bairro": {"type": "string"},
                "subprefeitura": {"type": "string"},
                "lat": {"type": "number"},
                "lng": {"type": "number"},
                "status": {"type": "string", "example": "validado"},
                "orgao": {"type": "string", "example": "subprefeitura"},
                "g": {"type": "number"},
                "e": {"type": "number"},
                "v": {"type": "number"},
                "r": {"type": "number"},
                "t": {"type": "number"},
                "ipv": {"type": "number", "example": 76.5},
                "faixa": {"type": "string", "enum": ["critico", "alto", "programado"]},
                "prazoEm": {"type": "string", "format": "date-time", "x-nullable": True},
                "situacaoDoPrazo": {"type": "string", "example": "Vence em 6 h"},
                "vencido": {"type": "boolean"},
                "linhaDoTempo": {"type": "array", "items": {"type": "object"}},
            },
        },
        "Rota": {
            "type": "object",
            "required": ["nome", "origem", "destino", "dias", "horario", "meio"],
            "properties": {
                "id": {"type": "string", "readOnly": True},
                "nome": {"type": "string", "example": "Casa → Trabalho"},
                "origem": {"type": "string", "example": "R. Butantã"},
                "destino": {"type": "string", "example": "Av. Brig. Faria Lima"},
                "dias": {"type": "array", "items": {"type": "string"}, "example": ["seg", "ter", "qua"]},
                "horario": {"type": "string", "example": "08:00"},
                "meio": {"type": "string", "enum": ["a-pe", "bicicleta", "onibus", "carro", "moto"]},
            },
        },
    },
}


def criar_app():
    configurar_logs()
    app = Flask(__name__)
    app.json.ensure_ascii = False
    app.json.sort_keys = False
    Swagger(app, template=MODELO_DO_SWAGGER, config={
        "headers": [],
        "specs": [{"endpoint": "openapi", "route": "/openapi.json"}],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/docs/",
    })

    app.register_blueprint(rotas_de_acesso)
    app.register_blueprint(rotas_do_cidadao)
    app.register_blueprint(rotas_do_painel)

    @app.get("/")
    def inicio():
        return redirect("/docs/")

    @app.errorhandler(ErroDaApi)
    def erro_da_api(erro):
        return jsonify(erro.para_dict()), erro.status

    @app.errorhandler(HTTPException)
    def erro_http(erro):
        mensagens = {404: "Não encontramos esse endereço.", 405: "Método não permitido nesse endereço."}
        return jsonify({"erro": mensagens.get(erro.code, erro.description)}), erro.code

    @app.errorhandler(PyMongoError)
    def erro_do_banco(erro):
        logger.exception("Falha ao falar com o MongoDB")
        return jsonify({"erro": "Não conseguimos falar com o banco de dados. Tente de novo em instantes."}), 503

    @app.errorhandler(Exception)
    def erro_inesperado(erro):
        logger.exception("Erro inesperado")
        return jsonify({"erro": "Algo não saiu como esperado."}), 500

    return app


if __name__ == "__main__":
    criar_app().run(port=CONFIG["porta"], debug=False)
