class ErroDaApi(Exception):
    status = 400

    def __init__(self, mensagem, campos=None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.campos = campos or {}

    def para_dict(self):
        resposta = {"erro": self.mensagem}
        if self.campos:
            resposta["campos"] = self.campos
        return resposta


class ErroDeValidacao(ErroDaApi):
    status = 400


class NaoAutenticado(ErroDaApi):
    status = 401


class Proibido(ErroDaApi):
    status = 403


class NaoEncontrado(ErroDaApi):
    status = 404


class Conflito(ErroDaApi):
    status = 409
