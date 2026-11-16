import logging
from datetime import timedelta

from banco import colecao, novo_id, para_json
from config import CONFIG
from datas import agora, ler_data, para_iso
from erros import Conflito, ErroDeValidacao, NaoAutenticado, NaoEncontrado
from regras import CODIGO_MAX_TENTATIVAS, CODIGO_VALE_MIN, email_valido, validar_senha
from seguranca import gerar_codigo, gerar_hash, gerar_token, senha_confere
from validacao import conferir, ler_booleano, ler_opcao, ler_texto

AREAS = ("app", "painel")
COLECAO_DE_CREDENCIAIS = {"app": "credenciais", "painel": "credenciaisDeGestores"}
COLECAO_DE_PESSOAS = {"app": "usuarios", "painel": "gestores"}
PERSONAS_DE_DEMONSTRACAO = {"app": ("juliana", "lourdes", "marta", "rafael"), "painel": ("carla",)}
SESSAO_VALE_DIAS = 7
PREFERENCIAS_PADRAO = {
    "push": True,
    "whatsapp": False,
    "soGraves": False,
    "silenciar": True,
    "silenciarDe": "22:00",
    "silenciarAte": "06:00",
    "avisarOutraPessoa": False,
    "outraPessoaNome": "",
    "outraPessoaWhatsapp": "",
}

logger = logging.getLogger(__name__)


def normalizar_email(email):
    return email.strip().lower()


def credencial_do_email(email, area):
    return colecao(COLECAO_DE_CREDENCIAIS[area]).find_one({"email": normalizar_email(email)})


def buscar_pessoa(pessoa_id, area):
    pessoa = colecao(COLECAO_DE_PESSOAS[area]).find_one({"_id": pessoa_id})
    if pessoa is None:
        raise NaoEncontrado("Não encontramos essa conta.")
    return pessoa


def abrir_sessao(pessoa_id, area):
    token = gerar_token()
    expira_em = para_iso(agora() + timedelta(days=SESSAO_VALE_DIAS))
    colecao("sessoes").insert_one({"_id": token, "usuarioId": pessoa_id, "area": area, "expiraEm": expira_em})
    return {
        "token": token,
        "expiraEm": expira_em,
        "area": area,
        "pessoa": para_json(buscar_pessoa(pessoa_id, area)),
    }


def pessoa_da_sessao(token, area):
    sessao = colecao("sessoes").find_one({"_id": token})
    if sessao is None or sessao["area"] != area:
        raise NaoAutenticado("Entre na sua conta para continuar.")
    if ler_data(sessao["expiraEm"]) < agora():
        colecao("sessoes").delete_one({"_id": token})
        raise NaoAutenticado("Sua sessão venceu. Entre de novo.")
    pessoa = colecao(COLECAO_DE_PESSOAS[area]).find_one({"_id": sessao["usuarioId"]})
    if pessoa is None:
        raise NaoAutenticado("Essa conta não existe mais. Entre de novo.")
    return pessoa


def ler_area(dados, erros):
    return ler_opcao(dados, "area", erros, AREAS, "Use a área app ou painel.") if "area" in dados else "app"


def entrar(dados):
    erros = {}
    area = ler_area(dados, erros)
    email = ler_texto(dados, "email", erros, "Digite um e-mail válido, como nome@exemplo.com.")
    senha = ler_texto(dados, "senha", erros, "Digite sua senha.", maximo=200)
    if email and not email_valido(email):
        erros["email"] = "Digite um e-mail válido, como nome@exemplo.com."
    conferir(erros)

    credencial = credencial_do_email(email, area)
    if credencial is None or not senha_confere(senha, credencial["senhaHash"]):
        logger.info("Login recusado na área %s", area)
        raise NaoAutenticado("E-mail ou senha não conferem. Confira e tente de novo.")
    logger.info("Login de %s na área %s", credencial["usuarioId"], area)
    return abrir_sessao(credencial["usuarioId"], area)


def entrar_como_persona(dados):
    if not CONFIG["modo_demonstracao"]:
        raise NaoEncontrado("A entrada por persona só existe na demonstração.")
    erros = {}
    area = ler_area(dados, erros)
    conferir(erros)
    perfil = ler_opcao(dados, "perfil", erros, PERSONAS_DE_DEMONSTRACAO[area], "Não encontramos esse perfil.")
    conferir(erros)
    return abrir_sessao(perfil, area)


def sair(token):
    colecao("sessoes").delete_one({"_id": token})


def cadastrar(dados):
    erros = {}
    nome = ler_texto(dados, "nome", erros, "Diga como podemos chamar você.", maximo=80)
    email = ler_texto(dados, "email", erros, "Digite um e-mail válido, como nome@exemplo.com.")
    whatsapp = ler_texto(dados, "whatsapp", erros, "", maximo=20, obrigatorio=False) or ""
    bairro = ler_texto(dados, "bairro", erros, "Diga em que bairro você mora.", maximo=80)
    senha = dados.get("senha")
    aceite = ler_booleano(dados, "aceite", erros, "Para criar a conta, é preciso concordar.")

    if nome and len(nome) < 2:
        erros["nome"] = "Diga como podemos chamar você."
    if email and not email_valido(email):
        erros["email"] = "Digite um e-mail válido, como nome@exemplo.com."
    digitos = "".join(caractere for caractere in whatsapp if caractere.isdigit())
    if whatsapp and len(digitos) not in (10, 11):
        erros["whatsapp"] = "Digite o número com DDD, como (11) 91234-5678."
    erro_da_senha = validar_senha(senha, dados.get("senhaRepetida"))
    if erro_da_senha:
        erros["senha"] = erro_da_senha
    if aceite is False:
        erros["aceite"] = "Para criar a conta, é preciso concordar."
    conferir(erros)

    email = normalizar_email(email)
    if credencial_do_email(email, "app"):
        raise Conflito("Já existe uma conta com este e-mail. Entre ou troque a senha.", {"email": "E-mail já cadastrado."})

    nome = " ".join(nome.split())
    usuario_id = novo_id()
    colecao("usuarios").insert_one({
        "_id": usuario_id,
        "nome": nome.split()[0],
        "nomeCompleto": nome,
        "persona": "Cidadão",
        "bairro": bairro,
        "lat": -23.5715,
        "lng": -46.7084,
        "whatsapp": whatsapp,
        "temKit": False,
        "diasKitNoMes": 0,
        "bilheteFinal": "",
        "seguindo": [],
        "preferencias": dict(PREFERENCIAS_PADRAO),
    })
    colecao("credenciais").insert_one({
        "_id": usuario_id,
        "usuarioId": usuario_id,
        "email": email,
        "senhaHash": gerar_hash(senha),
    })
    logger.info("Conta criada: %s", usuario_id)
    return abrir_sessao(usuario_id, "app")


def pedir_codigo(dados):
    erros = {}
    area = ler_area(dados, erros)
    email = ler_texto(dados, "email", erros, "Digite um e-mail válido, como nome@exemplo.com.")
    if email and not email_valido(email):
        erros["email"] = "Digite um e-mail válido, como nome@exemplo.com."
    conferir(erros)

    email = normalizar_email(email)
    credencial = credencial_do_email(email, area)
    pedido = {
        "_id": novo_id(),
        "area": area,
        "email": email,
        "usuarioId": credencial["usuarioId"] if credencial else None,
        "codigo": gerar_codigo(),
        "expiraEm": para_iso(agora() + timedelta(minutes=CODIGO_VALE_MIN)),
        "tentativas": 0,
    }
    colecao("codigosDeRecuperacao").insert_one(pedido)

    resposta = {"pedidoId": pedido["_id"], "expiraEm": pedido["expiraEm"]}
    if CONFIG["modo_demonstracao"]:
        resposta["codigoDeDemonstracao"] = pedido["codigo"] if credencial else None
    return resposta


def pedido_valido(pedido):
    return pedido["tentativas"] < CODIGO_MAX_TENTATIVAS and ler_data(pedido["expiraEm"]) > agora()


def redefinir_senha(dados):
    erros = {}
    pedido_id = ler_texto(dados, "pedidoId", erros, "Informe o pedido de troca de senha.", maximo=40)
    codigo = ler_texto(dados, "codigo", erros, "O código tem 6 números.", maximo=6)
    if codigo and (len(codigo) != 6 or not codigo.isdigit()):
        erros["codigo"] = "O código tem 6 números."
    erro_da_senha = validar_senha(dados.get("senha"), dados.get("senhaRepetida"))
    if erro_da_senha:
        erros["senha"] = erro_da_senha
    conferir(erros)

    pedido = colecao("codigosDeRecuperacao").find_one({"_id": pedido_id})
    if pedido is None or not pedido_valido(pedido):
        raise ErroDeValidacao("Este código venceu. Peça um novo.", {"codigo": "Código vencido."})

    if pedido["usuarioId"] is None or pedido["codigo"] != codigo:
        colecao("codigosDeRecuperacao").update_one({"_id": pedido_id}, {"$inc": {"tentativas": 1}})
        restam = CODIGO_MAX_TENTATIVAS - pedido["tentativas"] - 1
        mensagem = (
            f"Código incorreto. Você tem mais {restam} {'tentativa' if restam == 1 else 'tentativas'}."
            if restam > 0
            else "Código incorreto. Peça um novo."
        )
        raise ErroDeValidacao(mensagem, {"codigo": mensagem})

    credenciais = colecao(COLECAO_DE_CREDENCIAIS[pedido["area"]])
    credenciais.update_one({"usuarioId": pedido["usuarioId"]}, {"$set": {"senhaHash": gerar_hash(dados["senha"])}})
    colecao("codigosDeRecuperacao").delete_one({"_id": pedido_id})
    colecao("sessoes").delete_many({"usuarioId": pedido["usuarioId"], "area": pedido["area"]})
    logger.info("Senha trocada por código: %s na área %s", pedido["usuarioId"], pedido["area"])
