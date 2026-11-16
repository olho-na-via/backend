from flask import Blueprint, g, jsonify, request

from banco import colecao, para_json
from rotas.sessao import corpo, usuario_logado
from servicos import chamados, conta

rotas_do_cidadao = Blueprint("cidadao", __name__, url_prefix="/api")


@rotas_do_cidadao.before_request
def exigir_login():
    g.usuario = usuario_logado()


@rotas_do_cidadao.get("/chamados")
def listar_chamados():
    """Pontos do mapa: chamados não descartados, sem linha do tempo nem fotos.
    ---
    tags: [Cidadão · chamados]
    security: [{Bearer: []}]
    parameters:
      - {in: query, name: categoria, type: string, enum: [buraco, alagamento, faixa, semaforo, infraestrutura, outro]}
    responses:
      200: {description: Lista de chamados, schema: {type: array, items: {$ref: '#/definitions/Chamado'}}}
      401: {description: Sem sessão, schema: {$ref: '#/definitions/Erro'}}
    """
    return jsonify(chamados.listar_para_o_mapa(request.args.get("categoria")))


@rotas_do_cidadao.get("/chamados/<chamado_id>")
def detalhar_chamado(chamado_id):
    """Chamado completo, com linha do tempo, fotos e o IPV explicado.
    ---
    tags: [Cidadão · chamados]
    security: [{Bearer: []}]
    parameters:
      - {in: path, name: chamado_id, type: string, required: true, example: "48213"}
    responses:
      200: {description: Chamado, schema: {$ref: '#/definitions/Chamado'}}
      404: {description: Não encontrado, schema: {$ref: '#/definitions/Erro'}}
    """
    chamado = chamados.com_prioridade(chamados.buscar_chamado(chamado_id))
    chamado["seguindo"] = chamado_id in g.usuario["seguindo"]
    return jsonify(chamado)


@rotas_do_cidadao.post("/chamados")
def reportar():
    """Reporta um problema na via. Aplica a deduplicação de 15 m e o endereço aproximado.
    ---
    tags: [Cidadão · chamados]
    security: [{Bearer: []}]
    parameters:
      - in: body
        name: corpo
        required: true
        schema:
          type: object
          required: [categoria, lat, lng, foto]
          properties:
            categoria: {type: string, enum: [buraco, alagamento, faixa, semaforo, infraestrutura, outro], example: buraco}
            lat: {type: number, example: -23.5672}
            lng: {type: number, example: -46.7012}
            foto: {type: string, description: Imagem em data URL ou caminho, example: /fotos/buraco.jpg}
            descricao: {type: string, description: Obrigatória quando a categoria é outro}
            endereco: {type: string}
            referencia: {type: string, example: em frente à escola}
    responses:
      201: {description: Reporte recebido, schema: {$ref: '#/definitions/Chamado'}}
      400: {description: Campos inválidos, schema: {$ref: '#/definitions/Erro'}}
    """
    return jsonify(chamados.criar_reporte(g.usuario, corpo())), 201


@rotas_do_cidadao.post("/chamados/<chamado_id>/avancar-etapa")
def avancar_etapa(chamado_id):
    """Demonstração: avança o reporte uma etapa (recebido → em validação → validado), como faria a validação.
    ---
    tags: [Cidadão · chamados]
    security: [{Bearer: []}]
    parameters:
      - {in: path, name: chamado_id, type: string, required: true}
    responses:
      200: {description: Chamado atualizado, schema: {$ref: '#/definitions/Chamado'}}
      404: {description: Não encontrado, schema: {$ref: '#/definitions/Erro'}}
    """
    return jsonify(chamados.avancar_etapa_de_demonstracao(chamado_id))


@rotas_do_cidadao.put("/chamados/<chamado_id>/seguir")
def seguir(chamado_id):
    """Passa a seguir o chamado e a receber os avisos dele.
    ---
    tags: [Cidadão · chamados]
    security: [{Bearer: []}]
    parameters:
      - {in: path, name: chamado_id, type: string, required: true}
    responses:
      204: {description: Seguindo}
      404: {description: Não encontrado, schema: {$ref: '#/definitions/Erro'}}
    """
    chamados.seguir(g.usuario, chamado_id, True)
    return "", 204


@rotas_do_cidadao.delete("/chamados/<chamado_id>/seguir")
def deixar_de_seguir(chamado_id):
    """Deixa de seguir o chamado.
    ---
    tags: [Cidadão · chamados]
    security: [{Bearer: []}]
    parameters:
      - {in: path, name: chamado_id, type: string, required: true}
    responses:
      204: {description: Não segue mais}
    """
    chamados.seguir(g.usuario, chamado_id, False)
    return "", 204


@rotas_do_cidadao.post("/chamados/<chamado_id>/confirmacao")
def confirmar_reparo(chamado_id):
    """Confirma com foto se o reparo resolveu. Se não resolveu, o chamado volta para a fila com prioridade maior.
    ---
    tags: [Cidadão · chamados]
    security: [{Bearer: []}]
    parameters:
      - {in: path, name: chamado_id, type: string, required: true}
      - in: body
        name: corpo
        required: true
        schema:
          type: object
          required: [resolvido, foto]
          properties:
            resolvido: {type: boolean, example: true}
            foto: {type: string, example: /fotos/buraco.jpg}
    responses:
      200: {description: Chamado atualizado, schema: {$ref: '#/definitions/Chamado'}}
      409: {description: Chamado descartado, schema: {$ref: '#/definitions/Erro'}}
    """
    return jsonify(chamados.confirmar_reparo(g.usuario, chamado_id, corpo()))


@rotas_do_cidadao.get("/vias")
def listar_vias():
    """Vias cadastradas, usadas para sugerir o endereço e as rotas.
    ---
    tags: [Cidadão · chamados]
    security: [{Bearer: []}]
    responses:
      200: {description: Lista de vias}
    """
    return jsonify([para_json(via) for via in colecao("vias").find()])


@rotas_do_cidadao.get("/alertas")
def listar_alertas():
    """Alertas de via ainda válidos (expiram 30 min após a última confirmação).
    ---
    tags: [Cidadão · alertas]
    security: [{Bearer: []}]
    responses:
      200: {description: Lista de alertas}
    """
    return jsonify(conta.listar_alertas_ativos())


@rotas_do_cidadao.get("/eu")
def meu_perfil():
    """Dados de quem entrou, com avisos não lidos e saldo de créditos.
    ---
    tags: [Cidadão · conta]
    security: [{Bearer: []}]
    responses:
      200: {description: Perfil}
    """
    return jsonify(conta.perfil(g.usuario))


@rotas_do_cidadao.patch("/eu/preferencias")
def alterar_preferencias():
    """Como avisar você: push, WhatsApp, horário de silêncio e outra pessoa.
    ---
    tags: [Cidadão · conta]
    security: [{Bearer: []}]
    parameters:
      - in: body
        name: corpo
        required: true
        schema:
          type: object
          properties:
            push: {type: boolean}
            whatsapp: {type: boolean}
            soGraves: {type: boolean}
            silenciar: {type: boolean}
            silenciarDe: {type: string, example: "22:00"}
            silenciarAte: {type: string, example: "06:00"}
            avisarOutraPessoa: {type: boolean}
            outraPessoaNome: {type: string}
            outraPessoaWhatsapp: {type: string}
    responses:
      200: {description: Preferências salvas}
      400: {description: Campos inválidos, schema: {$ref: '#/definitions/Erro'}}
    """
    return jsonify(conta.atualizar_preferencias(g.usuario, corpo()))


@rotas_do_cidadao.get("/eu/chamados")
def meus_chamados():
    """Chamados que a pessoa reportou ou segue.
    ---
    tags: [Cidadão · conta]
    security: [{Bearer: []}]
    responses:
      200: {description: Lista de chamados, schema: {type: array, items: {$ref: '#/definitions/Chamado'}}}
    """
    return jsonify(chamados.chamados_seguidos(g.usuario))


@rotas_do_cidadao.get("/eu/notificacoes")
def minhas_notificacoes():
    """Avisos de cada etapa dos chamados e dos alertas, do mais novo ao mais antigo.
    ---
    tags: [Cidadão · conta]
    security: [{Bearer: []}]
    responses:
      200: {description: Lista de notificações}
    """
    return jsonify(conta.listar_notificacoes(g.usuario["_id"]))


@rotas_do_cidadao.post("/eu/notificacoes/lidas")
def marcar_notificacoes():
    """Marca todos os avisos como lidos.
    ---
    tags: [Cidadão · conta]
    security: [{Bearer: []}]
    responses:
      200: {description: Quantidade marcada}
    """
    return jsonify({"marcadas": conta.marcar_como_lidas(g.usuario["_id"])})


@rotas_do_cidadao.get("/eu/rotas")
def minhas_rotas():
    """Rotas que a pessoa faz sempre.
    ---
    tags: [Cidadão · alertas]
    security: [{Bearer: []}]
    responses:
      200: {description: Lista de rotas, schema: {type: array, items: {$ref: '#/definitions/Rota'}}}
    """
    return jsonify(conta.listar_rotas(g.usuario["_id"]))


@rotas_do_cidadao.post("/eu/rotas")
def criar_rota():
    """Adiciona uma rota para receber alertas.
    ---
    tags: [Cidadão · alertas]
    security: [{Bearer: []}]
    parameters:
      - {in: body, name: corpo, required: true, schema: {$ref: '#/definitions/Rota'}}
    responses:
      201: {description: Rota criada, schema: {$ref: '#/definitions/Rota'}}
      400: {description: Campos inválidos, schema: {$ref: '#/definitions/Erro'}}
    """
    return jsonify(conta.criar_rota(g.usuario, corpo())), 201


@rotas_do_cidadao.put("/eu/rotas/<rota_id>")
def alterar_rota(rota_id):
    """Edita uma rota.
    ---
    tags: [Cidadão · alertas]
    security: [{Bearer: []}]
    parameters:
      - {in: path, name: rota_id, type: string, required: true}
      - {in: body, name: corpo, required: true, schema: {$ref: '#/definitions/Rota'}}
    responses:
      200: {description: Rota salva, schema: {$ref: '#/definitions/Rota'}}
      404: {description: Não encontrada, schema: {$ref: '#/definitions/Erro'}}
    """
    return jsonify(conta.alterar_rota(g.usuario, rota_id, corpo()))


@rotas_do_cidadao.delete("/eu/rotas/<rota_id>")
def excluir_rota(rota_id):
    """Exclui uma rota.
    ---
    tags: [Cidadão · alertas]
    security: [{Bearer: []}]
    parameters:
      - {in: path, name: rota_id, type: string, required: true}
    responses:
      204: {description: Rota excluída}
      404: {description: Não encontrada, schema: {$ref: '#/definitions/Erro'}}
    """
    conta.excluir_rota(g.usuario, rota_id)
    return "", 204


@rotas_do_cidadao.get("/eu/alertas")
def meus_alertas():
    """Alertas ativos nas rotas da pessoa, com o nível de cada rota e o pior alerta.
    ---
    tags: [Cidadão · alertas]
    security: [{Bearer: []}]
    responses:
      200: {description: Rotas, alertas e pior alerta}
    """
    return jsonify(conta.alertas_do_usuario(g.usuario["_id"]))


@rotas_do_cidadao.get("/eu/creditos")
def minha_carteira():
    """Saldo, limite do mês e extrato de créditos.
    ---
    tags: [Cidadão · créditos]
    security: [{Bearer: []}]
    responses:
      200: {description: Carteira}
    """
    return jsonify(conta.carteira(g.usuario))


@rotas_do_cidadao.post("/eu/resgates")
def resgatar():
    """Troca pontos por recarga do Bilhete Único ou abatimento do IPTU (mínimo 100, até 1000 por mês).
    ---
    tags: [Cidadão · créditos]
    security: [{Bearer: []}]
    parameters:
      - in: body
        name: corpo
        required: true
        schema:
          type: object
          required: [destino, pontos]
          properties:
            destino: {type: string, enum: [bilhete-unico, iptu]}
            pontos: {type: integer, example: 100}
    responses:
      201: {description: Comprovante do resgate}
      400: {description: Valor fora das regras, schema: {$ref: '#/definitions/Erro'}}
    """
    return jsonify(conta.resgatar(g.usuario, corpo())), 201


@rotas_do_cidadao.get("/eu/resgates/<resgate_id>")
def meu_resgate(resgate_id):
    """Comprovante de um resgate.
    ---
    tags: [Cidadão · créditos]
    security: [{Bearer: []}]
    parameters:
      - {in: path, name: resgate_id, type: string, required: true}
    responses:
      200: {description: Comprovante}
      404: {description: Não encontrado, schema: {$ref: '#/definitions/Erro'}}
    """
    return jsonify(conta.buscar_resgate(g.usuario, resgate_id))
