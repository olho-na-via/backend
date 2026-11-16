from flask import request

from erros import ErroDeValidacao, NaoAutenticado
from servicos.acesso import pessoa_da_sessao


def corpo():
    dados = request.get_json(silent=True)
    if dados is None:
        return {}
    if not isinstance(dados, dict):
        raise ErroDeValidacao("Envie os dados como um objeto JSON.")
    return dados


def token_da_requisicao():
    tipo, _, token = request.headers.get("Authorization", "").partition(" ")
    if tipo.lower() != "bearer" or not token.strip():
        raise NaoAutenticado("Entre na sua conta para continuar.")
    return token.strip()


def usuario_logado():
    return pessoa_da_sessao(token_da_requisicao(), "app")


def gestor_logado():
    return pessoa_da_sessao(token_da_requisicao(), "painel")
