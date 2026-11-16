import json
import logging
import os
import re
import sys

from pymongo import ASCENDING, DESCENDING

from banco import obter_banco
from config import PASTA_DO_PROJETO
from datas import agora, ler_data, para_iso
from registro import configurar_logs
from seguranca import gerar_hash

PASTA_DE_DADOS = os.path.join(PASTA_DO_PROJETO, "dados")
SENHA_DEMO = "olhonavia"
DOMINIO_DEMO = "demo.olhonavia.com.br"
COLECOES = (
    "usuarios", "gestores", "chamados", "vias", "rotas", "alertas", "notificacoes",
    "movimentosCreditos", "prestadoras", "equipes", "indicadoresMensais", "linhasDeOnibus",
)
COLECOES_ZERADAS = ("resgates", "sessoes", "codigosDeRecuperacao")
DATA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")

logger = logging.getLogger(__name__)


def ler_json(nome):
    with open(os.path.join(PASTA_DE_DADOS, f"{nome}.json"), encoding="utf-8") as arquivo:
        return json.load(arquivo)


def deslocar_datas(valor, deslocamento):
    if isinstance(valor, dict):
        return {chave: deslocar_datas(item, deslocamento) for chave, item in valor.items()}
    if isinstance(valor, list):
        return [deslocar_datas(item, deslocamento) for item in valor]
    if isinstance(valor, str) and DATA_ISO.match(valor):
        return para_iso(ler_data(valor) + deslocamento)
    return valor


def para_documento(registro):
    documento = dict(registro)
    documento["_id"] = str(documento.pop("id"))
    return documento


def credenciais_de(pessoas):
    return [
        {
            "_id": pessoa["id"],
            "usuarioId": pessoa["id"],
            "email": f"{pessoa['id']}@{DOMINIO_DEMO}",
            "senhaHash": gerar_hash(SENHA_DEMO),
        }
        for pessoa in pessoas
    ]


def criar_indices(banco):
    banco.chamados.create_index([("protocolo", ASCENDING)], unique=True)
    banco.chamados.create_index([("subprefeitura", ASCENDING), ("status", ASCENDING)])
    banco.credenciais.create_index([("email", ASCENDING)], unique=True)
    banco.credenciaisDeGestores.create_index([("email", ASCENDING)], unique=True)
    for nome in ("notificacoes", "movimentosCreditos", "rotas", "resgates"):
        banco[nome].create_index([("usuarioId", ASCENDING)])
    banco.notificacoes.create_index([("em", DESCENDING)])


def popular_banco():
    banco = obter_banco()
    referencia = ler_data(ler_json("_referencia")["geradoEm"])
    deslocamento = agora() - referencia
    contagem = {}

    for nome in COLECOES:
        registros = deslocar_datas(ler_json(nome), deslocamento)
        banco[nome].drop()
        banco[nome].insert_many([para_documento(registro) for registro in registros])
        contagem[nome] = len(registros)

    banco.relatorios.drop()
    banco.relatorios.insert_one({"_id": "atual", **ler_json("relatorios")})

    for nome in COLECOES_ZERADAS:
        banco[nome].drop()

    banco.credenciais.drop()
    banco.credenciais.insert_many(credenciais_de(ler_json("usuarios")))
    banco.credenciaisDeGestores.drop()
    banco.credenciaisDeGestores.insert_many(credenciais_de(ler_json("gestores")))

    criar_indices(banco)
    logger.info("Banco populado com os dados de demonstração: %s", contagem)
    return contagem


def main():
    configurar_logs()
    if "--sim" not in sys.argv:
        resposta = input("Isto apaga os dados atuais do banco e grava os de demonstração. Continuar? (s/n) ")
        if resposta.strip().lower() != "s":
            print("Nada foi alterado.")
            return
    try:
        contagem = popular_banco()
    except FileNotFoundError as erro:
        print(f"Arquivo de dados não encontrado: {erro.filename}")
        sys.exit(1)
    for nome, total in contagem.items():
        print(f"{nome:<20} {total:>4} registros")
    print(f"\nLogins de demonstração: <persona>@{DOMINIO_DEMO} e carla@{DOMINIO_DEMO}, senha {SENHA_DEMO}")


if __name__ == "__main__":
    main()
