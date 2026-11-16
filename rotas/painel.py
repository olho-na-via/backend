from flask import Blueprint, g, jsonify, request

from banco import para_json
from rotas.sessao import corpo, gestor_logado
from servicos import painel

rotas_do_painel = Blueprint("painel", __name__, url_prefix="/api/painel")


@rotas_do_painel.before_request
def exigir_login_de_gestor():
    g.gestor = gestor_logado()


@rotas_do_painel.get("/eu")
def meu_perfil():
    """Gestor que entrou no painel.
    ---
    tags: [Painel · fila]
    security: [{Bearer: []}]
    responses:
      200: {description: Gestor}
      401: {description: Sem sessão de gestor, schema: {$ref: '#/definitions/Erro'}}
    """
    return jsonify(para_json(g.gestor))


@rotas_do_painel.get("/fila")
def fila_do_dia():
    """Fila do dia da subprefeitura do gestor, do maior para o menor IPV, com a ação sugerida para cada caso.
    ---
    tags: [Painel · fila]
    security: [{Bearer: []}]
    responses:
      200: {description: Fila e totais por faixa}
    """
    return jsonify(painel.fila_do_dia(g.gestor))


@rotas_do_painel.get("/chamados")
def listar_chamados():
    """Todos os chamados, com filtros, ordenação e paginação.
    ---
    tags: [Painel · chamados]
    security: [{Bearer: []}]
    parameters:
      - {in: query, name: sub, type: string, description: "Subprefeitura ou todas. Padrão: a do gestor"}
      - {in: query, name: status, type: string}
      - {in: query, name: categoria, type: string}
      - {in: query, name: faixa, type: string, enum: [critico, alto, programado]}
      - {in: query, name: busca, type: string, description: Protocolo, endereço, título ou bairro}
      - {in: query, name: ordem, type: string, enum: [ipv, recentes, prazo], default: ipv}
      - {in: query, name: pagina, type: integer, default: 1}
      - {in: query, name: porPagina, type: integer, default: 20}
    responses:
      200: {description: Página de chamados}
      400: {description: Parâmetro inválido, schema: {$ref: '#/definitions/Erro'}}
    """
    return jsonify(painel.listar_chamados(g.gestor, request.args))


@rotas_do_painel.get("/chamados/<chamado_id>")
def detalhar_chamado(chamado_id):
    """Chamado com o IPV explicado, a fórmula pública e as equipes que podem atendê-lo.
    ---
    tags: [Painel · chamados]
    security: [{Bearer: []}]
    parameters:
      - {in: path, name: chamado_id, type: string, required: true, example: "48213"}
    responses:
      200: {description: Chamado, schema: {$ref: '#/definitions/Chamado'}}
      404: {description: Não encontrado, schema: {$ref: '#/definitions/Erro'}}
    """
    return jsonify(painel.detalhar_chamado(chamado_id))


@rotas_do_painel.post("/chamados/<chamado_id>/despacho")
def despachar(chamado_id):
    """Despacha o chamado para uma equipe do mesmo órgão e avisa quem segue o ponto.
    ---
    tags: [Painel · ações]
    security: [{Bearer: []}]
    parameters:
      - {in: path, name: chamado_id, type: string, required: true}
      - in: body
        name: corpo
        required: true
        schema: {type: object, required: [equipeId], properties: {equipeId: {type: string, example: leste-2}}}
    responses:
      200: {description: Aviso de sucesso}
      409: {description: Status ou equipe não permitem, schema: {$ref: '#/definitions/Erro'}}
    """
    return jsonify(painel.despachar(g.gestor, chamado_id, corpo()))


@rotas_do_painel.post("/chamados/<chamado_id>/encaminhamento")
def encaminhar(chamado_id):
    """Encaminha o chamado ao órgão responsável (CET, CGE, Sabesp, Enel, SPTrans).
    ---
    tags: [Painel · ações]
    security: [{Bearer: []}]
    parameters:
      - {in: path, name: chamado_id, type: string, required: true}
    responses:
      200: {description: Aviso de sucesso}
      409: {description: Status não permite, schema: {$ref: '#/definitions/Erro'}}
    """
    return jsonify(painel.encaminhar(g.gestor, chamado_id))


@rotas_do_painel.post("/chamados/<chamado_id>/agendamento")
def agendar(chamado_id):
    """Inclui um chamado do plano semanal no roteiro da semana.
    ---
    tags: [Painel · ações]
    security: [{Bearer: []}]
    parameters:
      - {in: path, name: chamado_id, type: string, required: true}
    responses:
      200: {description: Aviso de sucesso}
      409: {description: Status não permite, schema: {$ref: '#/definitions/Erro'}}
    """
    return jsonify(painel.agendar(g.gestor, chamado_id))


@rotas_do_painel.post("/chamados/<chamado_id>/descarte")
def descartar(chamado_id):
    """Descarta o chamado como falso positivo, com motivo registrado para auditoria.
    ---
    tags: [Painel · ações]
    security: [{Bearer: []}]
    parameters:
      - {in: path, name: chamado_id, type: string, required: true}
      - in: body
        name: corpo
        required: true
        schema: {type: object, required: [motivo], properties: {motivo: {type: string, example: sombra de árvore}}}
    responses:
      200: {description: Aviso de sucesso}
      409: {description: Chamado já encerrado, schema: {$ref: '#/definitions/Erro'}}
    """
    return jsonify(painel.descartar(g.gestor, chamado_id, corpo()))


@rotas_do_painel.post("/chamados/<chamado_id>/revisao-ipv")
def revisar_ipv(chamado_id):
    """Revisão humana das variáveis do IPV (supervisão humana da IA), com motivo.
    ---
    tags: [Painel · ações]
    security: [{Bearer: []}]
    parameters:
      - {in: path, name: chamado_id, type: string, required: true}
      - in: body
        name: corpo
        required: true
        schema:
          type: object
          required: [g, e, v, r, t, motivo]
          properties:
            g: {type: number, example: 0.8}
            e: {type: number, example: 0.9}
            v: {type: number, example: 1}
            r: {type: number, example: 0.5}
            t: {type: number, example: 0.1}
            motivo: {type: string, example: rota escolar confirmada no local}
    responses:
      200: {description: Chamado com o novo IPV, schema: {$ref: '#/definitions/Chamado'}}
      400: {description: Valores fora de 0 a 1, schema: {$ref: '#/definitions/Erro'}}
    """
    return jsonify(painel.revisar_ipv(g.gestor, chamado_id, corpo()))


@rotas_do_painel.post("/chamados/<chamado_id>/vistoria")
def registrar_vistoria(chamado_id):
    """Registra a vistoria humana da detecção, usada para medir a precisão da IA.
    ---
    tags: [Painel · ações]
    security: [{Bearer: []}]
    parameters:
      - {in: path, name: chamado_id, type: string, required: true}
      - in: body
        name: corpo
        required: true
        schema: {type: object, required: [resultado], properties: {resultado: {type: string, enum: [confirmado, nao_confirmado]}}}
    responses:
      200: {description: Aviso de sucesso}
    """
    return jsonify(painel.registrar_vistoria(g.gestor, chamado_id, corpo()))


@rotas_do_painel.post("/chamados/<chamado_id>/reabertura")
def reabrir(chamado_id):
    """Reabre um chamado com reparo registrado ou resolvido. Aumenta R e conta a falha do ponto.
    ---
    tags: [Painel · ações]
    security: [{Bearer: []}]
    parameters:
      - {in: path, name: chamado_id, type: string, required: true}
      - in: body
        name: corpo
        required: true
        schema: {type: object, required: [motivo], properties: {motivo: {type: string, example: buraco voltou após a chuva}}}
    responses:
      200: {description: Aviso de sucesso}
      409: {description: Status não permite, schema: {$ref: '#/definitions/Erro'}}
    """
    return jsonify(painel.reabrir_pela_gestao(g.gestor, chamado_id, corpo()))


@rotas_do_painel.get("/equipes")
def listar_equipes():
    """Equipes de campo e o órgão de cada uma.
    ---
    tags: [Painel · prestadoras]
    security: [{Bearer: []}]
    responses:
      200: {description: Lista de equipes}
    """
    return jsonify(painel.listar_equipes())


@rotas_do_painel.get("/prestadoras")
def ranking_de_prestadoras():
    """Ranking das prestadoras por aprovação na 1ª verificação por imagem.
    ---
    tags: [Painel · prestadoras]
    security: [{Bearer: []}]
    responses:
      200: {description: Ranking}
    """
    return jsonify(painel.ranking_de_prestadoras())


@rotas_do_painel.get("/prestadoras/<prestadora_id>")
def detalhar_prestadora(prestadora_id):
    """Prestadora com equipes e chamados em andamento.
    ---
    tags: [Painel · prestadoras]
    security: [{Bearer: []}]
    parameters:
      - {in: path, name: prestadora_id, type: string, required: true}
    responses:
      200: {description: Prestadora}
      404: {description: Não encontrada, schema: {$ref: '#/definitions/Erro'}}
    """
    return jsonify(painel.detalhar_prestadora(prestadora_id))


@rotas_do_painel.get("/indicadores")
def listar_indicadores():
    """Indicadores mensais de impacto por subprefeitura.
    ---
    tags: [Painel · relatórios]
    security: [{Bearer: []}]
    parameters:
      - {in: query, name: sub, type: string, example: Butantã}
      - {in: query, name: mes, type: string, example: 2026-11}
    responses:
      200: {description: Indicadores}
    """
    return jsonify(painel.listar_indicadores(request.args.get("sub"), request.args.get("mes")))


@rotas_do_painel.get("/relatorios")
def relatorios():
    """Melhores horários de reparo, precisão da IA por bairro e equidade entre distritos.
    ---
    tags: [Painel · relatórios]
    security: [{Bearer: []}]
    responses:
      200: {description: Relatórios}
    """
    return jsonify(painel.buscar_relatorios())


@rotas_do_painel.get("/mapa")
def mapa_operacional():
    """Mapa operacional: chamados, vias com zonas cegas (sem inspeção há 30 dias), linhas de ônibus e alertas.
    ---
    tags: [Painel · fila]
    security: [{Bearer: []}]
    responses:
      200: {description: Camadas do mapa}
    """
    return jsonify(painel.mapa_operacional(g.gestor))
