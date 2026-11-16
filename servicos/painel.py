import logging
import math
import re
from datetime import timedelta

from banco import colecao, para_json
from datas import agora, agora_iso, ler_data
from erros import Conflito, ErroDeValidacao, NaoEncontrado
from regras import CATEGORIAS, NA_FILA, ORGAOS, PESOS_IPV, STATUS, acao_da_fila, vence_hoje
from servicos.chamados import CAMPOS_PESADOS, avisar_seguidores, buscar_chamado, com_prioridade, evento, reabrir
from servicos.conta import listar_alertas_ativos
from validacao import conferir, ler_numero, ler_opcao, ler_texto

ORDENS = ("ipv", "recentes", "prazo")
POR_PAGINA_MAXIMO = 50
DIAS_PARA_ZONA_CEGA = 30

logger = logging.getLogger(__name__)


def autor(gestor):
    return f"{gestor['nome']} · {gestor['cargo']}"


def status_para_gestor(chamado, equipes):
    nome, a_orgao, _ = ORGAOS[chamado["orgao"]]
    equipe = next((item["nome"] for item in equipes if item["_id"] == chamado.get("equipeId")), None)
    match chamado["status"]:
        case "recebido":
            return "Reporte recebido"
        case "em_validacao":
            return "Aguarda 2ª fonte"
        case "validado":
            return "Aguarda equipe" if nome == "Subprefeitura" else "Validado"
        case "enviado":
            return f"Enviado {a_orgao}"
        case "despachado":
            return f"Despachado · {equipe}" if equipe else "Despachado"
        case "reparo_registrado":
            return "Aguarda imagem"
        case "resolvido":
            return "Confirmado por imagem"
        case "reaberto":
            return "Reaberto · prioridade maior"
        case "descartado":
            return "Descartado · falso positivo"
        case _:
            return "Agendado no plano semanal" if chamado.get("agendado") else "Plano semanal"


def para_o_painel(chamado, equipes, momento):
    resultado = com_prioridade(chamado, momento)
    resultado["statusParaGestor"] = status_para_gestor(chamado, equipes)
    resultado["acaoSugerida"] = acao_da_fila(chamado, equipes)
    return resultado


def fila_do_dia(gestor):
    momento = agora()
    equipes = list(colecao("equipes").find())
    filtro = {"subprefeitura": gestor["subprefeitura"], "status": {"$in": list(NA_FILA)}}
    chamados = list(colecao("chamados").find(filtro, CAMPOS_PESADOS))
    fila = sorted((para_o_painel(chamado, equipes, momento) for chamado in chamados), key=lambda c: c["ipv"], reverse=True)

    por_faixa = {"critico": 0, "alto": 0, "programado": 0}
    for chamado in fila:
        por_faixa[chamado["faixa"]] += 1
    return {
        "subprefeitura": gestor["subprefeitura"],
        "geradaEm": agora_iso(),
        "totais": {
            "naFila": len(fila),
            "porFaixa": por_faixa,
            "vencidos": sum(1 for chamado in fila if chamado["vencido"]),
            "criticosVencemHoje": sum(1 for chamado in chamados if vence_hoje(chamado, momento)),
        },
        "fila": fila,
    }


def ler_inteiro_da_consulta(argumentos, nome, padrao, minimo, maximo):
    try:
        valor = int(argumentos.get(nome, padrao))
    except ValueError:
        raise ErroDeValidacao(f"O parâmetro {nome} precisa ser um número inteiro.")
    return min(max(valor, minimo), maximo)


def listar_chamados(gestor, argumentos):
    filtro = {}
    subprefeitura = argumentos.get("sub", gestor["subprefeitura"])
    if subprefeitura != "todas":
        filtro["subprefeitura"] = subprefeitura
    if argumentos.get("status") in STATUS:
        filtro["status"] = argumentos["status"]
    if argumentos.get("categoria") in CATEGORIAS:
        filtro["categoria"] = argumentos["categoria"]
    busca = argumentos.get("busca", "").strip()
    if busca:
        padrao = {"$regex": re.escape(busca), "$options": "i"}
        filtro["$or"] = [{"protocolo": padrao}, {"endereco": padrao}, {"titulo": padrao}, {"bairro": padrao}]

    momento = agora()
    equipes = list(colecao("equipes").find())
    itens = [para_o_painel(chamado, equipes, momento) for chamado in colecao("chamados").find(filtro, CAMPOS_PESADOS)]
    if argumentos.get("faixa") in ("critico", "alto", "programado"):
        itens = [item for item in itens if item["faixa"] == argumentos["faixa"]]

    match argumentos.get("ordem", "ipv"):
        case "recentes":
            itens.sort(key=lambda c: c["abertoEm"], reverse=True)
        case "prazo":
            itens.sort(key=lambda c: (c["prazoEm"] is None, c["prazoEm"] or ""))
        case _:
            itens.sort(key=lambda c: c["ipv"], reverse=True)

    por_pagina = ler_inteiro_da_consulta(argumentos, "porPagina", 20, 1, POR_PAGINA_MAXIMO)
    paginas = max(math.ceil(len(itens) / por_pagina), 1)
    pagina = ler_inteiro_da_consulta(argumentos, "pagina", 1, 1, paginas)
    inicio = (pagina - 1) * por_pagina
    return {
        "itens": itens[inicio:inicio + por_pagina],
        "total": len(itens),
        "pagina": pagina,
        "paginas": paginas,
        "porPagina": por_pagina,
    }


def detalhar_chamado(chamado_id):
    chamado = buscar_chamado(chamado_id)
    equipes = list(colecao("equipes").find())
    resultado = para_o_painel(chamado, equipes, agora())
    resultado["equipesCompativeis"] = [para_json(equipe) for equipe in equipes if equipe["orgao"] == chamado["orgao"]]
    resultado["formulaDoIpv"] = {"pesos": PESOS_IPV, "faixas": {"critico": ">= 70", "alto": ">= 40", "programado": "< 40"}}
    return resultado


def exigir_status(chamado, permitidos, mensagem):
    if chamado["status"] not in permitidos:
        raise Conflito(mensagem)


def despachar(gestor, chamado_id, dados):
    erros = {}
    equipe_id = ler_texto(dados, "equipeId", erros, "Escolha a equipe.", maximo=40)
    conferir(erros)
    chamado = buscar_chamado(chamado_id)
    exigir_status(chamado, ("validado", "reaberto"), "Só dá para despachar chamado validado ou reaberto.")
    equipe = colecao("equipes").find_one({"_id": equipe_id})
    if equipe is None:
        raise NaoEncontrado("Não encontramos essa equipe.")
    if equipe["orgao"] != chamado["orgao"]:
        raise Conflito(f"A {equipe['nome']} não atende chamados {ORGAOS[chamado['orgao']][2]}.")

    colecao("chamados").update_one({"_id": chamado_id}, {
        "$set": {"status": "despachado", "equipeId": equipe["_id"], "prestadoraId": equipe["prestadoraId"]},
        "$push": {"linhaDoTempo": evento("despachado", "Equipe a caminho", autor=f"{gestor['nome']} → {equipe['nome']}")},
    })
    avisar_seguidores(chamado, "A equipe está a caminho.", f"O chamado de {chamado['endereco']} entrou no roteiro de hoje.")
    logger.info("Chamado %s despachado para %s por %s", chamado["protocolo"], equipe["_id"], gestor["_id"])
    return {"aviso": f"Chamado #{chamado['protocolo']} despachado para a {equipe['nome']}."}


def encaminhar(gestor, chamado_id):
    chamado = buscar_chamado(chamado_id)
    exigir_status(chamado, ("validado", "reaberto"), "Só dá para encaminhar chamado validado ou reaberto.")
    a_orgao = ORGAOS[chamado["orgao"]][1]
    colecao("chamados").update_one({"_id": chamado_id}, {
        "$set": {"status": "enviado"},
        "$push": {"linhaDoTempo": evento("aberto", f"Chamado enviado {a_orgao}", autor=autor(gestor))},
    })
    return {"aviso": f"Chamado #{chamado['protocolo']} enviado {a_orgao}."}


def agendar(gestor, chamado_id):
    chamado = buscar_chamado(chamado_id)
    exigir_status(chamado, ("programado",), "Só chamados do plano semanal podem ser agendados.")
    colecao("chamados").update_one({"_id": chamado_id}, {
        "$set": {"agendado": True},
        "$push": {"linhaDoTempo": evento("agendado", "Incluído no plano semanal por rota", autor=autor(gestor))},
    })
    return {"aviso": f"Chamado #{chamado['protocolo']} agendado no plano da semana."}


def descartar(gestor, chamado_id, dados):
    erros = {}
    motivo = ler_texto(dados, "motivo", erros, "Diga por que o chamado é um falso positivo.", maximo=200)
    conferir(erros)
    chamado = buscar_chamado(chamado_id)
    exigir_status(chamado, [status for status in STATUS if status not in ("resolvido", "descartado")], "Este chamado já foi encerrado.")
    colecao("chamados").update_one({"_id": chamado_id}, {
        "$set": {"status": "descartado", "descarte": {"motivo": motivo, "em": agora_iso(), "por": gestor["nome"]}},
        "$push": {"linhaDoTempo": evento("descartado", f"Descartado como falso positivo: {motivo}", "Não confirmado", autor(gestor))},
    })
    logger.info("Chamado %s descartado por %s", chamado["protocolo"], gestor["_id"])
    return {"aviso": f"Chamado #{chamado['protocolo']} descartado. O motivo ficou registrado."}


def revisar_ipv(gestor, chamado_id, dados):
    erros = {}
    valores = {}
    for chave in PESOS_IPV:
        valores[chave] = ler_numero(dados, chave, erros, "Use um valor entre 0 e 1.", minimo=0, maximo=1)
    motivo = ler_texto(dados, "motivo", erros, "Explique o motivo da revisão.", maximo=200)
    conferir(erros)

    chamado = buscar_chamado(chamado_id)
    mudancas = [f"{chave.upper()} {chamado[chave]} → {valor}" for chave, valor in valores.items() if chamado[chave] != valor]
    descricao = ", ".join(mudancas) or "sem mudança de valores"
    colecao("chamados").update_one({"_id": chamado_id}, {
        "$set": {**valores, "revisaoManual": {"motivo": motivo, "em": agora_iso(), "por": gestor["nome"]}},
        "$push": {"linhaDoTempo": evento("revisao", f"Prioridade revista ({descricao}): {motivo}", autor=autor(gestor))},
    })
    logger.info("IPV do chamado %s revisto por %s: %s", chamado["protocolo"], gestor["_id"], descricao)
    return detalhar_chamado(chamado_id)


def registrar_vistoria(gestor, chamado_id, dados):
    erros = {}
    resultado = ler_opcao(dados, "resultado", erros, ("confirmado", "nao_confirmado"), "Use confirmado ou nao_confirmado.")
    conferir(erros)
    chamado = buscar_chamado(chamado_id)
    texto = (
        "Vistoria humana confirmou a detecção"
        if resultado == "confirmado"
        else "Vistoria humana não confirmou a detecção"
    )
    colecao("chamados").update_one({"_id": chamado_id}, {
        "$set": {"vistoria": {"resultado": resultado, "em": agora_iso(), "por": gestor["nome"]}},
        "$push": {"linhaDoTempo": evento("vistoria", texto, autor=autor(gestor))},
    })
    return {"aviso": f"Vistoria do chamado #{chamado['protocolo']} registrada. Ela entra na medição de precisão da IA."}


def reabrir_pela_gestao(gestor, chamado_id, dados):
    erros = {}
    motivo = ler_texto(dados, "motivo", erros, "Explique por que o chamado volta para a fila.", maximo=200)
    conferir(erros)
    chamado = buscar_chamado(chamado_id)
    exigir_status(chamado, ("resolvido", "reparo_registrado"), "Só dá para reabrir chamado com reparo registrado ou resolvido.")
    reabrir(chamado, f"Reaberto pela gestão: {motivo}", autor(gestor))
    avisar_seguidores(
        chamado,
        "O chamado voltou para a fila.",
        f"A gestão reabriu o chamado de {chamado['endereco']} com prioridade maior.",
    )
    return {"aviso": f"Chamado #{chamado['protocolo']} reaberto com prioridade maior."}


# ───────────── Prestadoras, indicadores e mapa ─────────────


def listar_equipes():
    return [para_json(equipe) for equipe in colecao("equipes").find()]


def ranking_de_prestadoras():
    prestadoras = [para_json(prestadora) for prestadora in colecao("prestadoras").find()]
    prestadoras.sort(key=lambda p: (p["aprovadosPrimeiraVerificacao"], -p["tempoMedioDias"]), reverse=True)
    for posicao, prestadora in enumerate(prestadoras, start=1):
        prestadora["posicao"] = posicao
    return prestadoras


def detalhar_prestadora(prestadora_id):
    prestadora = colecao("prestadoras").find_one({"_id": prestadora_id})
    if prestadora is None:
        raise NaoEncontrado("Prestadora não encontrada.")
    resultado = para_json(prestadora)
    resultado["equipes"] = [para_json(equipe) for equipe in colecao("equipes").find({"prestadoraId": prestadora_id})]
    resultado["chamadosEmAndamento"] = colecao("chamados").count_documents(
        {"prestadoraId": prestadora_id, "status": {"$in": ["despachado", "reparo_registrado", "reaberto"]}}
    )
    return resultado


def listar_indicadores(subprefeitura=None, mes=None):
    filtro = {}
    if subprefeitura:
        filtro["subprefeitura"] = subprefeitura
    if mes:
        filtro["mes"] = mes
    return [para_json(indicador) for indicador in colecao("indicadoresMensais").find(filtro).sort("mes", 1)]


def buscar_relatorios():
    relatorios = colecao("relatorios").find_one({"_id": "atual"})
    if relatorios is None:
        raise NaoEncontrado("Os relatórios ainda não foram gerados.")
    relatorios.pop("_id")
    return relatorios


def mapa_operacional(gestor):
    momento = agora()
    limite = momento - timedelta(days=DIAS_PARA_ZONA_CEGA)
    vias = []
    for via in colecao("vias").find({"subprefeitura": gestor["subprefeitura"]}):
        via = para_json(via)
        via["zonaCega"] = "ultimaInspecaoEm" in via and ler_data(via["ultimaInspecaoEm"]) < limite
        vias.append(via)
    equipes = list(colecao("equipes").find())
    filtro = {"subprefeitura": gestor["subprefeitura"], "status": {"$ne": "descartado"}}
    return {
        "vias": vias,
        "linhasDeOnibus": [para_json(linha) for linha in colecao("linhasDeOnibus").find()],
        "alertas": listar_alertas_ativos(),
        "chamados": [para_o_painel(chamado, equipes, momento) for chamado in colecao("chamados").find(filtro, CAMPOS_PESADOS)],
    }
