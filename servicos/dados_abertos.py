from banco import colecao
from servicos.painel import listar_indicadores, ranking_de_prestadoras

CAMPOS_PUBLICOS_DE_PRESTADORA = (
    "id", "nome", "tipo", "orgao", "posicao", "reparosNoMes",
    "aprovadosPrimeiraVerificacao", "tempoMedioDias", "reaberturas90d",
)


def resumo_de_chamados(subprefeitura=None):
    etapas = []
    if subprefeitura:
        etapas.append({"$match": {"subprefeitura": subprefeitura}})
    etapas.append({"$group": {"_id": {"subprefeitura": "$subprefeitura", "status": "$status"}, "total": {"$sum": 1}}})

    resumo = {}
    for grupo in colecao("chamados").aggregate(etapas):
        nome = grupo["_id"]["subprefeitura"]
        item = resumo.setdefault(nome, {"subprefeitura": nome, "total": 0, "resolvidos": 0, "abertos": 0, "descartados": 0})
        item["total"] += grupo["total"]
        match grupo["_id"]["status"]:
            case "resolvido":
                item["resolvidos"] += grupo["total"]
            case "descartado":
                item["descartados"] += grupo["total"]
            case _:
                item["abertos"] += grupo["total"]
    return sorted(resumo.values(), key=lambda item: item["subprefeitura"])


def indicadores_publicos(subprefeitura=None, mes=None):
    return listar_indicadores(subprefeitura, mes)


def prestadoras_publicas():
    return [
        {campo: prestadora.get(campo) for campo in CAMPOS_PUBLICOS_DE_PRESTADORA}
        for prestadora in ranking_de_prestadoras()
    ]
