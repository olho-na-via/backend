import math
import re
from datetime import timedelta

from datas import dia_em_sao_paulo, ler_data
from erros import ErroDeValidacao

CATEGORIAS = {
    "buraco": "Buraco",
    "alagamento": "Alagamento",
    "faixa": "Faixa apagada",
    "semaforo": "Semáforo",
    "infraestrutura": "Placa ou estrutura",
    "outro": "Outro problema",
}

ORGAOS = {
    "subprefeitura": ("Subprefeitura", "à subprefeitura", "na subprefeitura"),
    "cet": ("CET", "à CET", "na CET"),
    "cge": ("CGE", "ao CGE", "no CGE"),
    "sabesp": ("Sabesp", "à Sabesp", "na Sabesp"),
    "enel": ("Enel", "à Enel", "na Enel"),
    "sptrans": ("SPTrans", "à SPTrans", "na SPTrans"),
}

ORGAO_DA_CATEGORIA = {
    "buraco": "subprefeitura",
    "alagamento": "subprefeitura",
    "faixa": "cet",
    "semaforo": "cet",
    "infraestrutura": "cet",
    "outro": "subprefeitura",
}

IPV_INICIAL = {
    "buraco": {"g": 0.6, "e": 0.5, "v": 0.5, "r": 0, "t": 0},
    "alagamento": {"g": 0.6, "e": 0.5, "v": 0.7, "r": 0, "t": 0},
    "faixa": {"g": 0.5, "e": 0.5, "v": 0.8, "r": 0, "t": 0},
    "semaforo": {"g": 0.9, "e": 0.8, "v": 0.6, "r": 0, "t": 0},
    "infraestrutura": {"g": 0.4, "e": 0.4, "v": 0.4, "r": 0, "t": 0},
    "outro": {"g": 0.3, "e": 0.3, "v": 0.3, "r": 0, "t": 0},
}

STATUS = (
    "recebido", "em_validacao", "validado", "enviado", "despachado",
    "reparo_registrado", "resolvido", "reaberto", "descartado", "programado",
)
STATUS_ENCERRADOS = ("resolvido", "descartado")
NA_FILA = ("validado", "enviado", "despachado", "reparo_registrado", "programado", "reaberto")
SEM_REPARO = ("validado", "enviado", "despachado", "reaberto")

# ───────────── IPV ─────────────

PESOS_IPV = {"g": 0.35, "e": 0.25, "v": 0.20, "r": 0.10, "t": 0.10}
PRAZO_HORAS = {"critico": 24, "alto": 72, "programado": None}


def calcular_ipv(variaveis):
    contribuicoes = {}
    total = 0
    for chave, peso in PESOS_IPV.items():
        valor = variaveis.get(chave)
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not 0 <= valor <= 1:
            raise ErroDeValidacao(f"A variável {chave} do IPV precisa estar entre 0 e 1.")
        contribuicoes[chave] = round(100 * peso * valor, 1)
        total += 100 * peso * valor
    return round(total, 1), contribuicoes


def faixa_do_ipv(ipv):
    if ipv >= 70:
        return "critico"
    if ipv >= 40:
        return "alto"
    return "programado"


def prazo_do_chamado(chamado):
    ipv, _ = calcular_ipv(chamado)
    horas = PRAZO_HORAS[faixa_do_ipv(ipv)]
    if horas is None:
        return None
    return ler_data(chamado["abertoEm"]) + timedelta(hours=horas)


def duracao_por_extenso(intervalo):
    horas = abs(intervalo.total_seconds()) / 3600
    if horas < 1:
        return f"{max(round(horas * 60), 1)} min"
    if horas < 48:
        return f"{round(horas)} h"
    return f"{round(horas / 24)} dias"


def situacao_do_prazo(chamado, momento):
    match chamado["status"]:
        case "resolvido":
            return "Concluído", False
        case "descartado":
            return "Descartado", False
    prazo = prazo_do_chamado(chamado)
    if prazo is None:
        return "Plano semanal", False
    if chamado["status"] == "reparo_registrado":
        return "Aguarda imagem", False
    if prazo < momento:
        return f"Vencido há {duracao_por_extenso(momento - prazo)}", True
    return f"Vence em {duracao_por_extenso(prazo - momento)}", False


def vence_hoje(chamado, momento):
    ipv, _ = calcular_ipv(chamado)
    prazo = prazo_do_chamado(chamado)
    return (
        faixa_do_ipv(ipv) == "critico"
        and chamado["status"] in SEM_REPARO
        and prazo is not None
        and dia_em_sao_paulo(prazo) == dia_em_sao_paulo(momento)
    )


def acao_da_fila(chamado, equipes):
    match chamado["status"]:
        case "programado":
            return "ver" if chamado.get("agendado") else "agendar"
        case "validado" | "reaberto":
            tem_equipe = any(equipe["orgao"] == chamado["orgao"] for equipe in equipes)
            return "despachar" if tem_equipe else "encaminhar"
        case _:
            return "ver"


# ───────────── Distância e deduplicação ─────────────

RAIO_MESMO_PONTO_M = 15


def distancia_em_metros(lat1, lng1, lat2, lng2):
    raio_da_terra = 6371000
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    h = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lng / 2) ** 2
    )
    return 2 * raio_da_terra * math.asin(math.sqrt(h))


def chamado_ativo(chamado):
    return chamado["status"] not in STATUS_ENCERRADOS


def achar_chamado_no_mesmo_ponto(chamados, lat, lng, categoria):
    melhor = None
    for chamado in chamados:
        if chamado["categoria"] != categoria or not chamado_ativo(chamado):
            continue
        distancia = distancia_em_metros(chamado["lat"], chamado["lng"], lat, lng)
        if distancia <= RAIO_MESMO_PONTO_M and (melhor is None or distancia < melhor[1]):
            melhor = (chamado, distancia)
    return melhor


def via_mais_proxima(vias, lat, lng):
    melhor = None
    for via in vias:
        distancia = distancia_em_metros(via["lat"], via["lng"], lat, lng)
        if melhor is None or distancia < melhor[1]:
            melhor = (via, distancia)
    return melhor


def endereco_aproximado(via, distancia):
    numero = 20 + (round(distancia / 10) * 10 or 100)
    return f"{via['nome']}, {numero}"


# ───────────── Créditos ─────────────

PONTOS = {"reporte_validado": 10, "foto_confirma_reparo": 5, "kit_ativo": 50}
REAIS_POR_100_PONTOS = 5
RESGATE_MINIMO = 100
LIMITE_MENSAL_RESGATE = 1000
DESTINOS_DE_RESGATE = ("bilhete-unico", "iptu")


def pontos_em_reais(pontos):
    return pontos / 100 * REAIS_POR_100_PONTOS


def saldo_de(movimentos):
    return sum(movimento["pontos"] for movimento in movimentos)


def resgatado_no_mes(movimentos, momento):
    total = 0
    for movimento in movimentos:
        em = ler_data(movimento["em"])
        if movimento["pontos"] < 0 and (em.year, em.month) == (momento.year, momento.month):
            total -= movimento["pontos"]
    return total


def validar_resgate(pontos, saldo, ja_resgatado_no_mes):
    if isinstance(pontos, bool) or not isinstance(pontos, int) or pontos < RESGATE_MINIMO:
        return f"O mínimo para usar é {RESGATE_MINIMO} pts."
    if pontos > saldo:
        return f"Você tem {saldo} pts. Escolha um valor até esse limite."
    if ja_resgatado_no_mes + pontos > LIMITE_MENSAL_RESGATE:
        resta = max(LIMITE_MENSAL_RESGATE - ja_resgatado_no_mes, 0)
        return f"O limite é de {LIMITE_MENSAL_RESGATE} pts por mês. Neste mês você ainda pode usar {resta} pts."
    return None


# ───────────── Acesso ─────────────

SENHA_MINIMA = 8
CODIGO_VALE_MIN = 15
CODIGO_MAX_TENTATIVAS = 5
EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def email_valido(email):
    return isinstance(email, str) and EMAIL.match(email.strip()) is not None


def validar_senha(senha, repetida):
    if not isinstance(senha, str) or len(senha) < SENHA_MINIMA:
        return f"Use pelo menos {SENHA_MINIMA} caracteres."
    if not re.search(r"\d", senha) or not re.search(r"[a-zA-Z]", senha):
        return "Misture letras e números."
    if senha != repetida:
        return "As duas senhas estão diferentes."
    return None


# ───────────── Alertas de rota ─────────────

ALERTA_EXPIRA_MIN = 30
ORDEM_NIVEL = {"livre": 0, "atencao": 1, "evitar": 2, "intransitavel": 3}


def alerta_valido(alerta, momento):
    if ler_data(alerta["confirmadoEm"]) + timedelta(minutes=ALERTA_EXPIRA_MIN) < momento:
        return False
    if alerta["nivel"] == "intransitavel" and not alerta["temCameraFixa"] and len(alerta["fontes"]) < 2:
        return False
    return True


def nivel_da_rota(rota_id, alertas):
    pior = None
    for alerta in alertas:
        if rota_id not in alerta["rotaIds"]:
            continue
        if pior is None or ORDEM_NIVEL[alerta["nivel"]] > ORDEM_NIVEL[pior["nivel"]]:
            pior = alerta
    return (pior["nivel"] if pior else "livre"), pior


def pior_alerta(alertas):
    if not alertas:
        return None
    return max(alertas, key=lambda alerta: ORDEM_NIVEL[alerta["nivel"]])


# ───────────── Busca ─────────────


def pesquisa_binaria(lista, item, chave):
    baixo = 0
    alto = len(lista) - 1
    while baixo <= alto:
        meio = (baixo + alto) // 2
        chute = chave(lista[meio])
        if chute == item:
            return meio
        if chute > item:
            alto = meio - 1
        else:
            baixo = meio + 1
    return None
