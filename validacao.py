import re

from erros import ErroDeValidacao

HORARIO = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def ler_texto(dados, campo, erros, mensagem, maximo=200, obrigatorio=True):
    valor = dados.get(campo)
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        if obrigatorio:
            erros[campo] = mensagem
        return None
    if not isinstance(valor, str):
        erros[campo] = mensagem
        return None
    valor = valor.strip()
    if len(valor) > maximo:
        erros[campo] = f"Use até {maximo} caracteres."
        return None
    return valor


def ler_numero(dados, campo, erros, mensagem, minimo=None, maximo=None, inteiro=False):
    valor = dados.get(campo)
    tipos = (int,) if inteiro else (int, float)
    if isinstance(valor, bool) or not isinstance(valor, tipos):
        erros[campo] = mensagem
        return None
    if (minimo is not None and valor < minimo) or (maximo is not None and valor > maximo):
        erros[campo] = mensagem
        return None
    return valor


def ler_opcao(dados, campo, erros, opcoes, mensagem):
    valor = dados.get(campo)
    if valor not in opcoes:
        erros[campo] = mensagem
        return None
    return valor


def ler_booleano(dados, campo, erros, mensagem):
    valor = dados.get(campo)
    if not isinstance(valor, bool):
        erros[campo] = mensagem
        return None
    return valor


def ler_horario(dados, campo, erros, mensagem):
    valor = dados.get(campo)
    if not isinstance(valor, str) or not HORARIO.match(valor):
        erros[campo] = mensagem
        return None
    return valor


def conferir(erros):
    if erros:
        raise ErroDeValidacao("Confira os campos destacados.", erros)
