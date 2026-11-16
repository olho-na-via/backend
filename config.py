import os

PASTA_DO_PROJETO = os.path.dirname(os.path.abspath(__file__))
ARQUIVOS_DE_AMBIENTE = ("atlas-credentials.env", ".env")
PADROES = {
    "MONGODB_BANCO": "olho_na_via",
    "OLHO_MODO_DEMONSTRACAO": "1",
    "OLHO_PORTA": "5000",
}


def ler_arquivo_de_ambiente(caminho):
    valores = {}
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            for linha in arquivo:
                linha = linha.strip()
                if not linha or linha.startswith("#") or "=" not in linha:
                    continue
                chave, valor = linha.split("=", 1)
                valores[chave.strip()] = valor.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return valores


def carregar_configuracao():
    valores = dict(PADROES)
    for nome in ARQUIVOS_DE_AMBIENTE:
        valores.update(ler_arquivo_de_ambiente(os.path.join(PASTA_DO_PROJETO, nome)))
    for chave, valor in os.environ.items():
        if chave.startswith(("MONGODB_", "OLHO_")):
            valores[chave] = valor

    if not valores.get("MONGODB_URI"):
        raise RuntimeError("Defina MONGODB_URI no arquivo .env ou em atlas-credentials.env.")

    return {
        "mongodb_uri": valores["MONGODB_URI"],
        "mongodb_usuario": valores.get("MONGODB_USERNAME"),
        "mongodb_senha": valores.get("MONGODB_PASSWORD"),
        "mongodb_banco": valores["MONGODB_BANCO"],
        "modo_demonstracao": valores["OLHO_MODO_DEMONSTRACAO"] == "1",
        "porta": int(valores["OLHO_PORTA"]),
    }


CONFIG = carregar_configuracao()
