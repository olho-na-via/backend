import logging

from banco import colecao, novo_id, para_json
from datas import agora, agora_iso, para_iso
from erros import Conflito, NaoEncontrado
from regras import (
    CATEGORIAS,
    IPV_INICIAL,
    ORGAO_DA_CATEGORIA,
    ORGAOS,
    PONTOS,
    achar_chamado_no_mesmo_ponto,
    calcular_ipv,
    endereco_aproximado,
    faixa_do_ipv,
    prazo_do_chamado,
    situacao_do_prazo,
    via_mais_proxima,
)
from servicos.conta import creditar, notificar
from validacao import conferir, ler_booleano, ler_numero, ler_opcao, ler_texto

CAMPOS_PESADOS = {"linhaDoTempo": 0, "fotos": 0, "descricao": 0, "deteccoes": 0}
PROTOCOLO_INICIAL = 51100

logger = logging.getLogger(__name__)


def evento(tipo, texto, texto_simples=None, autor=None):
    item = {"tipo": tipo, "em": agora_iso(), "texto": texto}
    if texto_simples:
        item["textoSimples"] = texto_simples
    if autor:
        item["autor"] = autor
    return item


def com_prioridade(chamado, momento=None):
    momento = momento or agora()
    ipv, contribuicoes = calcular_ipv(chamado)
    prazo = prazo_do_chamado(chamado)
    situacao, vencido = situacao_do_prazo(chamado, momento)
    resultado = para_json(chamado)
    resultado.update({
        "ipv": ipv,
        "faixa": faixa_do_ipv(ipv),
        "contribuicoes": contribuicoes,
        "prazoEm": para_iso(prazo) if prazo else None,
        "situacaoDoPrazo": situacao,
        "vencido": vencido,
    })
    return resultado


def buscar_chamado(chamado_id):
    chamado = colecao("chamados").find_one({"_id": chamado_id})
    if chamado is None:
        raise NaoEncontrado("Chamado não encontrado.")
    return chamado


def listar_para_o_mapa(categoria=None):
    filtro = {"status": {"$ne": "descartado"}}
    if categoria in CATEGORIAS:
        filtro["categoria"] = categoria
    momento = agora()
    return [com_prioridade(chamado, momento) for chamado in colecao("chamados").find(filtro, CAMPOS_PESADOS)]


def chamados_seguidos(usuario):
    filtro = {"_id": {"$in": usuario["seguindo"]}}
    momento = agora()
    return [com_prioridade(chamado, momento) for chamado in colecao("chamados").find(filtro, CAMPOS_PESADOS)]


def proximo_protocolo():
    numeros = [PROTOCOLO_INICIAL]
    for chamado in colecao("chamados").find({}, {"protocolo": 1}):
        if str(chamado.get("protocolo", "")).isdigit():
            numeros.append(int(chamado["protocolo"]))
    return str(max(numeros) + 1)


def criar_reporte(usuario, dados):
    erros = {}
    categoria = ler_opcao(dados, "categoria", erros, CATEGORIAS, "Escolha o tipo de problema.")
    lat = ler_numero(dados, "lat", erros, "Informe a latitude do local.", minimo=-90, maximo=90)
    lng = ler_numero(dados, "lng", erros, "Informe a longitude do local.", minimo=-180, maximo=180)
    foto = ler_texto(dados, "foto", erros, "Tire uma foto do problema.", maximo=2_000_000)
    descricao = ler_texto(
        dados, "descricao", erros, "Conte o que você viu.", maximo=200, obrigatorio=categoria == "outro"
    )
    endereco = ler_texto(dados, "endereco", erros, "", maximo=160, obrigatorio=False)
    referencia = ler_texto(dados, "referencia", erros, "", maximo=120, obrigatorio=False)
    conferir(erros)

    existentes = list(colecao("chamados").find({}, {"categoria": 1, "status": 1, "lat": 1, "lng": 1, "protocolo": 1}))
    mesmo_ponto = achar_chamado_no_mesmo_ponto(existentes, lat, lng, categoria)
    via, distancia = via_mais_proxima(list(colecao("vias").find()), lat, lng)
    protocolo = proximo_protocolo()
    momento = agora_iso()

    chamado = {
        "_id": novo_id(),
        "protocolo": protocolo,
        "categoria": categoria,
        "titulo": CATEGORIAS[categoria],
        "endereco": endereco or endereco_aproximado(via, distancia),
        "bairro": via["bairro"],
        "subprefeitura": via.get("subprefeitura", "Butantã"),
        "lat": lat,
        "lng": lng,
        "origem": "app",
        **IPV_INICIAL[categoria],
        "status": "recebido",
        "orgao": ORGAO_DA_CATEGORIA[categoria],
        "abertoEm": momento,
        "fotos": {"antes": foto, "antesEm": momento},
        "linhaDoTempo": [evento("recebido", "Reportado pelo app", "Recebemos seu aviso")],
        "reaberturas": 0,
        "seguidores": 1,
        "reportadoPor": usuario["_id"],
        "primeiroDoPonto": mesmo_ponto is None,
    }
    if descricao:
        chamado["descricao"] = descricao
    if referencia:
        chamado["referencia"] = referencia
    colecao("chamados").insert_one(chamado)
    colecao("usuarios").update_one({"_id": usuario["_id"]}, {"$addToSet": {"seguindo": chamado["_id"]}})
    logger.info("Reporte %s criado por %s", protocolo, usuario["_id"])

    resultado = com_prioridade(chamado)
    resultado["mesmoPonto"] = para_json(mesmo_ponto[0])["id"] if mesmo_ponto else None
    return resultado


def avancar_etapa_de_demonstracao(chamado_id):
    chamado = buscar_chamado(chamado_id)
    nome, _, na_orgao = ORGAOS[chamado["orgao"]]
    match chamado["status"]:
        case "recebido":
            colecao("chamados").update_one({"_id": chamado_id}, {
                "$set": {"status": "em_validacao"},
                "$push": {"linhaDoTempo": evento("em_validacao", "Em validação com uma segunda fonte")},
            })
        case "em_validacao":
            colecao("chamados").update_one({"_id": chamado_id}, {
                "$set": {"status": "validado"},
                "$push": {"linhaDoTempo": evento("aberto", f"Chamado aberto {na_orgao}", f"Avisamos: {nome}")},
            })
            if chamado.get("reportadoPor"):
                ganhou = chamado.get("primeiroDoPonto") is True
                creditar(
                    chamado["reportadoPor"],
                    PONTOS["reporte_validado"] if ganhou else 0,
                    f"Reporte validado · {CATEGORIAS[chamado['categoria']].lower()}" if ganhou else "Reporte já existia",
                    chamado["endereco"] if ganhou else "sem pontos, mas ajudou a confirmar",
                )
                bonus = f" Você ganhou {PONTOS['reporte_validado']} pts." if ganhou else ""
                notificar(
                    chamado["reportadoPor"],
                    "Seu reporte foi validado.",
                    f"Abrimos o chamado {na_orgao}.{bonus} Avisamos quando a equipe registrar o reparo.",
                    chamado_id=chamado_id,
                )
    return com_prioridade(buscar_chamado(chamado_id))


def seguir(usuario, chamado_id, deve_seguir):
    buscar_chamado(chamado_id)
    ja_segue = chamado_id in usuario["seguindo"]
    if deve_seguir == ja_segue:
        return
    operacao = "$addToSet" if deve_seguir else "$pull"
    colecao("usuarios").update_one({"_id": usuario["_id"]}, {operacao: {"seguindo": chamado_id}})
    filtro = {"_id": chamado_id} if deve_seguir else {"_id": chamado_id, "seguidores": {"$gt": 0}}
    colecao("chamados").update_one(filtro, {"$inc": {"seguidores": 1 if deve_seguir else -1}})


def avisar_seguidores(chamado, titulo, texto):
    for seguidor in colecao("usuarios").find({"seguindo": chamado["_id"]}, {"_id": 1}):
        notificar(seguidor["_id"], titulo, texto, chamado_id=chamado["_id"])


def reabrir(chamado, texto, autor=None):
    falhas = chamado.get("falhas12m", 0) + 1
    colecao("chamados").update_one({"_id": chamado["_id"]}, {
        "$set": {
            "status": "reaberto",
            "resolvidoEm": None,
            "r": min(round(chamado["r"] + 0.3, 2), 1),
            "falhas12m": falhas,
            "sugerirRecapeamento": falhas >= 3,
        },
        "$inc": {"reaberturas": 1},
        "$push": {"linhaDoTempo": evento("reaberto", texto, "O problema voltou", autor)},
    })


def confirmar_reparo(usuario, chamado_id, dados):
    erros = {}
    resolvido = ler_booleano(dados, "resolvido", erros, "Diga se o problema foi resolvido.")
    foto = ler_texto(dados, "foto", erros, "Tire uma foto de como está agora.", maximo=2_000_000)
    conferir(erros)

    chamado = buscar_chamado(chamado_id)
    if chamado["status"] == "descartado":
        raise Conflito("Este chamado foi descartado e não aceita confirmação.")
    momento = agora_iso()

    if resolvido:
        texto = (
            "Uma pessoa confirmou o reparo com foto"
            if chamado["status"] == "resolvido"
            else "Reparo confirmado com a foto de quem passou no local"
        )
        colecao("chamados").update_one({"_id": chamado_id}, {
            "$set": {
                "status": "resolvido",
                "resolvidoEm": chamado.get("resolvidoEm") or momento,
                "fotos.depois": foto,
                "fotos.depoisEm": momento,
            },
            "$push": {"linhaDoTempo": evento("confirmacao_cidadao", texto, "Reparo conferido com foto")},
        })
        creditar(usuario["_id"], PONTOS["foto_confirma_reparo"], "Confirmou um reparo", chamado["endereco"])
    else:
        reabrir(chamado, "O problema voltou. O chamado foi para a fila com prioridade maior")
        colecao("chamados").update_one({"_id": chamado_id}, {"$set": {"fotos": {"antes": foto, "antesEm": momento}}})
        notificar(
            usuario["_id"],
            "Recebemos seu aviso: o problema continua.",
            "O chamado voltou para a fila com prioridade maior.",
            chamado_id=chamado_id,
        )
    return com_prioridade(buscar_chamado(chamado_id))
