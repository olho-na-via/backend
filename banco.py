from bson import ObjectId
from pymongo import MongoClient

from config import CONFIG

_cliente = None


def obter_banco():
    global _cliente
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
