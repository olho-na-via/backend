from unittest import mock

MODULOS_QUE_USAM_O_BANCO = (
    "servicos.acesso",
    "servicos.chamados",
    "servicos.conta",
    "servicos.painel",
    "servicos.dados_abertos",
)


class BancoFalso:
    def __init__(self):
        self.colecoes = {}

    def __call__(self, nome):
        return self.colecoes.setdefault(nome, mock.MagicMock(name=nome))


def usar_banco_falso(caso):
    banco = BancoFalso()
    for modulo in MODULOS_QUE_USAM_O_BANCO:
        troca = mock.patch(f"{modulo}.colecao", banco)
        troca.start()
        caso.addCleanup(troca.stop)
    return banco
