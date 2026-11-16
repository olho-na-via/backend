from flask import Blueprint, jsonify, request

from servicos import dados_abertos

rotas_de_dados_abertos = Blueprint("dados_abertos", __name__, url_prefix="/api/dados-abertos")


@rotas_de_dados_abertos.get("/chamados")
def resumo_de_chamados():
    """Chamados abertos, resolvidos e descartados por subprefeitura. Público, sem imagens nem dados pessoais.
    ---
    tags: [Dados abertos]
    parameters:
      - {in: query, name: sub, type: string, example: Butantã}
    responses:
      200: {description: Totais por subprefeitura}
    """
    return jsonify(dados_abertos.resumo_de_chamados(request.args.get("sub")))


@rotas_de_dados_abertos.get("/indicadores")
def indicadores():
    """Indicadores mensais: tempo até o reparo, detecção antes de reclamação, reincidência e equidade.
    ---
    tags: [Dados abertos]
    parameters:
      - {in: query, name: sub, type: string, example: Butantã}
      - {in: query, name: mes, type: string, example: 2026-11}
    responses:
      200: {description: Indicadores}
    """
    return jsonify(dados_abertos.indicadores_publicos(request.args.get("sub"), request.args.get("mes")))


@rotas_de_dados_abertos.get("/prestadoras")
def prestadoras():
    """Ranking público das prestadoras de reparo.
    ---
    tags: [Dados abertos]
    responses:
      200: {description: Ranking}
    """
    return jsonify(dados_abertos.prestadoras_publicas())
