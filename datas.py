from datetime import datetime, timedelta, timezone

FUSO_DE_SAO_PAULO = timezone(timedelta(hours=-3))


def agora():
    return datetime.now(timezone.utc)


def para_iso(momento):
    return momento.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def agora_iso():
    return para_iso(agora())


def ler_data(texto):
    return datetime.fromisoformat(texto.replace("Z", "+00:00"))


def dia_em_sao_paulo(momento):
    return momento.astimezone(FUSO_DE_SAO_PAULO).date()
