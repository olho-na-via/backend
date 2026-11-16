from datetime import timedelta

from pymongo import DESCENDING

from banco import colecao, novo_id, para_json
from datas import agora, agora_iso, para_iso
from erros import ErroDeValidacao, NaoEncontrado
from regras import (
    DESTINOS_DE_RESGATE,
    LIMITE_MENSAL_RESGATE,
    alerta_valido,
    nivel_da_rota,
    pior_alerta,
    pontos_em_reais,
    resgatado_no_mes,
    saldo_de,
    validar_resgate,
)
from validacao import conferir, ler_booleano, ler_horario, ler_numero, ler_opcao, ler_texto

DIAS_DA_SEMANA = ("seg", "ter", "qua", "qui", "sex", "sab", "dom")
MEIOS = ("a-pe", "bicicleta", "onibus", "carro", "moto")
CAMPOS_BOOLEANOS = ("push", "whatsapp", "soGraves", "silenciar", "avisarOutraPessoa")
CAMPOS_DE_HORARIO = ("silenciarDe", "silenciarAte")
CAMPOS_DE_TEXTO = ("outraPessoaNome", "outraPessoaWhatsapp")


def perfil(usuario):
    nao_lidas = colecao("notificacoes").count_documents({"usuarioId": usuario["_id"], "lida": False})
    resultado = para_json(usuario)
    resultado["naoLidas"] = nao_lidas
    resultado["saldo"] = saldo_de(listar_movimentos(usuario["_id"]))
    return resultado


def atualizar_preferencias(usuario, dados):
    erros = {}
    novas = {}
    for campo in CAMPOS_BOOLEANOS:
        if campo in dados:
            novas[campo] = ler_booleano(dados, campo, erros, "Use verdadeiro ou falso.")
    for campo in CAMPOS_DE_HORARIO:
        if campo in dados:
            novas[campo] = ler_horario(dados, campo, erros, "Use o formato 22:00.")
    for campo in CAMPOS_DE_TEXTO:
        if campo in dados:
            novas[campo] = ler_texto(dados, campo, erros, "", maximo=80, obrigatorio=False) or ""
    conferir(erros)

    preferencias = {**usuario["preferencias"], **novas}
    if preferencias["avisarOutraPessoa"] and not preferencias["outraPessoaWhatsapp"]:
        raise ErroDeValidacao(
            "Diga o WhatsApp de quem também deve receber os avisos.",
            {"outraPessoaWhatsapp": "Informe o número."},
        )
    colecao("usuarios").update_one({"_id": usuario["_id"]}, {"$set": {"preferencias": preferencias}})
    return preferencias


# ───────────── Notificações ─────────────


def listar_notificacoes(usuario_id):
    cursor = colecao("notificacoes").find({"usuarioId": usuario_id}).sort("em", DESCENDING)
    return [para_json(notificacao) for notificacao in cursor]


def notificar(usuario_id, titulo, texto, chamado_id=None, alerta_id=None, canal="app"):
    notificacao = {
        "_id": novo_id(),
        "usuarioId": usuario_id,
        "canal": canal,
        "titulo": titulo,
        "texto": texto,
        "em": agora_iso(),
        "lida": False,
    }
    if chamado_id:
        notificacao["chamadoId"] = chamado_id
    if alerta_id:
        notificacao["alertaId"] = alerta_id
    colecao("notificacoes").insert_one(notificacao)


def marcar_como_lidas(usuario_id):
    resultado = colecao("notificacoes").update_many({"usuarioId": usuario_id, "lida": False}, {"$set": {"lida": True}})
    return resultado.modified_count


# ───────────── Rotas e alertas ─────────────


def listar_rotas(usuario_id):
    return [para_json(rota) for rota in colecao("rotas").find({"usuarioId": usuario_id})]


def buscar_rota(usuario, rota_id):
    rota = colecao("rotas").find_one({"_id": rota_id, "usuarioId": usuario["_id"]})
    if rota is None:
        raise NaoEncontrado("Rota não encontrada.")
    return rota


def ler_rota(dados):
    erros = {}
    rota = {
        "nome": ler_texto(dados, "nome", erros, "Dê um nome para a rota, como “Casa → Trabalho”.", maximo=60),
        "origem": ler_texto(dados, "origem", erros, "Diga de onde você sai.", maximo=120),
        "destino": ler_texto(dados, "destino", erros, "Diga para onde você vai.", maximo=120),
        "horario": ler_horario(dados, "horario", erros, "Diga a que horas você costuma sair."),
        "meio": ler_opcao(dados, "meio", erros, MEIOS, "Escolha como você vai."),
    }
    dias = dados.get("dias")
    if not isinstance(dias, list) or not dias or any(dia not in DIAS_DA_SEMANA for dia in dias):
        erros["dias"] = "Escolha pelo menos um dia."
    else:
        rota["dias"] = [dia for dia in DIAS_DA_SEMANA if dia in dias]
    if rota["origem"] and rota["origem"] == rota["destino"]:
        erros["destino"] = "A saída e a chegada estão iguais. Mude uma delas."
    conferir(erros)
    return rota


def criar_rota(usuario, dados):
    rota = {"_id": novo_id(), "usuarioId": usuario["_id"], **ler_rota(dados)}
    colecao("rotas").insert_one(rota)
    return para_json(rota)


def alterar_rota(usuario, rota_id, dados):
    buscar_rota(usuario, rota_id)
    novos = ler_rota(dados)
    colecao("rotas").update_one({"_id": rota_id}, {"$set": novos})
    return para_json(buscar_rota(usuario, rota_id))


def excluir_rota(usuario, rota_id):
    buscar_rota(usuario, rota_id)
    colecao("rotas").delete_one({"_id": rota_id})


def listar_alertas_ativos():
    momento = agora()
    ativos = []
    for alerta in colecao("alertas").find():
        if alerta.get("demoConfirmadoHaMin") is not None:
            alerta["confirmadoEm"] = para_iso(momento - timedelta(minutes=alerta["demoConfirmadoHaMin"]))
        if alerta_valido(alerta, momento):
            ativos.append(para_json(alerta))
    return ativos


def alertas_do_usuario(usuario_id):
    rotas = listar_rotas(usuario_id)
    ids = {rota["id"] for rota in rotas}
    alertas = [alerta for alerta in listar_alertas_ativos() if ids & set(alerta["rotaIds"])]
    for rota in rotas:
        rota["nivel"], pior = nivel_da_rota(rota["id"], alertas)
        rota["alertaId"] = pior["id"] if pior else None
    return {"rotas": rotas, "alertas": alertas, "piorAlerta": pior_alerta(alertas)}


# ───────────── Créditos ─────────────


def listar_movimentos(usuario_id):
    cursor = colecao("movimentosCreditos").find({"usuarioId": usuario_id}).sort("em", DESCENDING)
    return [para_json(movimento) for movimento in cursor]


def creditar(usuario_id, pontos, motivo, detalhe):
    colecao("movimentosCreditos").insert_one({
        "_id": novo_id(),
        "usuarioId": usuario_id,
        "pontos": pontos,
        "motivo": motivo,
        "detalhe": detalhe,
        "em": agora_iso(),
    })


def carteira(usuario):
    movimentos = listar_movimentos(usuario["_id"])
    ja_usado = resgatado_no_mes(movimentos, agora())
    saldo = saldo_de(movimentos)
    return {
        "saldo": saldo,
        "saldoEmReais": pontos_em_reais(saldo),
        "resgatadoNoMes": ja_usado,
        "disponivelNoMes": max(LIMITE_MENSAL_RESGATE - ja_usado, 0),
        "temKit": usuario["temKit"],
        "diasKitNoMes": usuario["diasKitNoMes"],
        "movimentos": movimentos,
    }


def resgatar(usuario, dados):
    erros = {}
    destino = ler_opcao(dados, "destino", erros, DESTINOS_DE_RESGATE, "Escolha Bilhete Único ou IPTU.")
    pontos = ler_numero(dados, "pontos", erros, "Informe quantos pontos quer usar.", minimo=1, inteiro=True)
    conferir(erros)

    movimentos = listar_movimentos(usuario["_id"])
    saldo = saldo_de(movimentos)
    erro = validar_resgate(pontos, saldo, resgatado_no_mes(movimentos, agora()))
    if erro:
        raise ErroDeValidacao(erro, {"pontos": erro})

    em = agora_iso()
    comprovante = f"RC-{20931 + colecao('resgates').count_documents({})}"
    resgate = {
        "_id": novo_id(),
        "comprovante": comprovante,
        "usuarioId": usuario["_id"],
        "pontos": pontos,
        "valor": pontos_em_reais(pontos),
        "destino": destino,
        "final": usuario["bilheteFinal"] if destino == "bilhete-unico" else "0387",
        "em": em,
        "saldoDepois": saldo - pontos,
    }
    colecao("resgates").insert_one(resgate)
    colecao("movimentosCreditos").insert_one({
        "_id": novo_id(),
        "usuarioId": usuario["_id"],
        "pontos": -pontos,
        "motivo": "Recarga do Bilhete Único" if destino == "bilhete-unico" else "Abatimento do IPTU",
        "detalhe": f"comprovante #{comprovante}",
        "em": em,
    })
    return para_json(resgate)


def buscar_resgate(usuario, resgate_id):
    resgate = colecao("resgates").find_one({"_id": resgate_id, "usuarioId": usuario["_id"]})
    if resgate is None:
        raise NaoEncontrado("Resgate não encontrado.")
    return para_json(resgate)
