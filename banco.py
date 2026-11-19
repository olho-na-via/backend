import os

from bson import ObjectId
from pymongo import MongoClient

from banco_local import BancoLocal
from config import CONFIG, PASTA_DO_PROJETO

PASTA_DO_BANCO_LOCAL = os.path.join(PASTA_DO_PROJETO, "dados_locais")

_cliente = None
_banco_local = None


def modo_local():
    return not CONFIG["mongodb_uri"]


def banco_local_vazio():
    return modo_local() and not os.path.exists(os.path.join(PASTA_DO_BANCO_LOCAL, "chamados.json"))


def obter_banco():
    global _cliente, _banco_local
    if modo_local():
        if _banco_local is None:
            _banco_local = BancoLocal(PASTA_DO_BANCO_LOCAL)
        return _banco_local
    if _cliente is None:
        opcoes = {"serverSelectionTimeoutMS": 8000}
        if "@" not in CONFIG["mongodb_uri"] and CONFIG["mongodb_usuario"]:
            opcoes["username"] = CONFIG["mongodb_usuario"]
            opcoes["password"] = CONFIG["mongodb_senha"]
        _cliente = MongoClient(CONFIG["mongodb_uri"], **opcoes)
    return _cliente[CONFIG["mongodb_banco"]]


def colecao(nome):
    return obter_banco()[nome]


def novo_id():
    return str(ObjectId())


def para_json(documento):
    if documento is None:
        return None
    resultado = dict(documento)
    resultado["id"] = resultado.pop("_id")
    return resultado
