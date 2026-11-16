import logging

from flasgger import Swagger
from flask import Flask, jsonify, redirect
from pymongo.errors import PyMongoError
from werkzeug.exceptions import HTTPException

from config import CONFIG
from erros import ErroDaApi
from registro import configurar_logs
from rotas.acesso import rotas_de_acesso

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
