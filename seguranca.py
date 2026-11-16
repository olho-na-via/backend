import hashlib
import hmac
import secrets

ITERACOES = 200_000


def gerar_hash(senha):
    sal = secrets.token_hex(16)
    resumo = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), bytes.fromhex(sal), ITERACOES).hex()
    return f"pbkdf2_sha256${ITERACOES}${sal}${resumo}"


def senha_confere(senha, guardado):
    try:
        _, iteracoes, sal, resumo = guardado.split("$")
        calculado = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), bytes.fromhex(sal), int(iteracoes)).hex()
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(calculado, resumo)


def gerar_token():
    return secrets.token_urlsafe(32)


def gerar_codigo():
    return f"{secrets.randbelow(1_000_000):06d}"
