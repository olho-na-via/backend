import unittest
from datetime import timedelta

from datas import agora, para_iso
from erros import Conflito, ErroDeValidacao, NaoAutenticado
from seguranca import gerar_hash, senha_confere
from servicos import acesso
from testes.apoio import usar_banco_falso


class TesteEntrar(unittest.TestCase):
    def setUp(self):
        self.banco = usar_banco_falso(self)
        self.banco("credenciais").find_one.return_value = {"usuarioId": "juliana", "senhaHash": gerar_hash("senha1234")}
        self.banco("usuarios").find_one.return_value = {"_id": "juliana", "nome": "Juliana"}

    def test_abre_sessao_com_a_senha_certa(self):
        sessao = acesso.entrar({"email": " Juliana@Demo.com ", "senha": "senha1234"})
        self.assertEqual((sessao["area"], sessao["pessoa"]["id"]), ("app", "juliana"))
        self.banco("credenciais").find_one.assert_called_with({"email": "juliana@demo.com"})
        self.banco("sessoes").insert_one.assert_called_once()

    def test_senha_errada_e_email_desconhecido_dao_a_mesma_mensagem(self):
        with self.assertRaises(NaoAutenticado) as senha_errada:
            acesso.entrar({"email": "juliana@demo.com", "senha": "outra1234"})
        self.banco("credenciais").find_one.return_value = None
        with self.assertRaises(NaoAutenticado) as email_desconhecido:
            acesso.entrar({"email": "ninguem@demo.com", "senha": "senha1234"})
        self.assertEqual(senha_errada.exception.mensagem, email_desconhecido.exception.mensagem)
        self.banco("sessoes").insert_one.assert_not_called()

    def test_campos_invalidos(self):
        with self.assertRaises(ErroDeValidacao) as contexto:
            acesso.entrar({"email": "sem-arroba", "area": "outra"})
        self.assertEqual(set(contexto.exception.campos), {"email", "senha", "area"})

    def test_painel_usa_as_credenciais_dos_gestores(self):
        self.banco("credenciaisDeGestores").find_one.return_value = {"usuarioId": "carla", "senhaHash": gerar_hash("senha1234")}
        self.banco("gestores").find_one.return_value = {"_id": "carla", "nome": "Carla M."}
        sessao = acesso.entrar({"email": "carla@demo.com", "senha": "senha1234", "area": "painel"})
        self.assertEqual(sessao["pessoa"]["id"], "carla")
        self.banco("credenciais").find_one.assert_not_called()


class TesteSessao(unittest.TestCase):
    def setUp(self):
        self.banco = usar_banco_falso(self)
        self.sessoes = self.banco("sessoes")
        self.banco("usuarios").find_one.return_value = {"_id": "juliana"}

    def sessao(self, area="app", dias=1):
        return {"_id": "t", "usuarioId": "juliana", "area": area, "expiraEm": para_iso(agora() + timedelta(days=dias))}

    def test_sessao_valida_devolve_a_pessoa(self):
        self.sessoes.find_one.return_value = self.sessao()
        self.assertEqual(acesso.pessoa_da_sessao("t", "app")["_id"], "juliana")

    def test_token_desconhecido_ou_de_outra_area(self):
        self.sessoes.find_one.return_value = None
        with self.assertRaises(NaoAutenticado):
            acesso.pessoa_da_sessao("t", "app")
        self.sessoes.find_one.return_value = self.sessao(area="app")
        with self.assertRaises(NaoAutenticado):
            acesso.pessoa_da_sessao("t", "painel")

    def test_sessao_vencida_e_apagada(self):
        self.sessoes.find_one.return_value = self.sessao(dias=-1)
        with self.assertRaises(NaoAutenticado):
            acesso.pessoa_da_sessao("t", "app")
        self.sessoes.delete_one.assert_called_once_with({"_id": "t"})


class TesteCadastro(unittest.TestCase):
    DADOS = {
        "nome": "Ana  Souza",
        "email": "ANA@exemplo.com",
        "whatsapp": "(11) 91234-5678",
        "bairro": "Butantã",
        "senha": "senha1234",
        "senhaRepetida": "senha1234",
        "aceite": True,
    }

    def setUp(self):
        self.banco = usar_banco_falso(self)
        self.banco("credenciais").find_one.return_value = None
        self.banco("usuarios").find_one.return_value = {"_id": "novo", "nome": "Ana"}

    def test_cria_usuario_e_credencial_com_hash(self):
        acesso.cadastrar(self.DADOS)
        usuario = self.banco("usuarios").insert_one.call_args.args[0]
        credencial = self.banco("credenciais").insert_one.call_args.args[0]
        self.assertEqual((usuario["nome"], usuario["nomeCompleto"]), ("Ana", "Ana Souza"))
        self.assertEqual(credencial["email"], "ana@exemplo.com")
        self.assertTrue(senha_confere("senha1234", credencial["senhaHash"]))

    def test_email_repetido(self):
        self.banco("credenciais").find_one.return_value = {"usuarioId": "juliana"}
        with self.assertRaises(Conflito):
            acesso.cadastrar(self.DADOS)
        self.banco("usuarios").insert_one.assert_not_called()

    def test_campos_invalidos(self):
        dados = {**self.DADOS, "whatsapp": "1234", "senhaRepetida": "outra1234", "aceite": False}
        with self.assertRaises(ErroDeValidacao) as contexto:
            acesso.cadastrar(dados)
        self.assertEqual(set(contexto.exception.campos), {"whatsapp", "senha", "aceite"})


class TesteTrocaDeSenha(unittest.TestCase):
    def setUp(self):
        self.banco = usar_banco_falso(self)
        self.codigos = self.banco("codigosDeRecuperacao")

    def pedido(self, **mudancas):
        pedido = {
            "_id": "p1",
            "area": "app",
            "usuarioId": "juliana",
            "codigo": "123456",
            "expiraEm": para_iso(agora() + timedelta(minutes=10)),
            "tentativas": 0,
        }
        return {**pedido, **mudancas}

    def redefinir(self, codigo):
        return acesso.redefinir_senha({"pedidoId": "p1", "codigo": codigo, "senha": "nova12345", "senhaRepetida": "nova12345"})

    def test_email_sem_conta_nao_revela_nada(self):
        self.banco("credenciais").find_one.return_value = None
        resposta = acesso.pedir_codigo({"email": "ninguem@exemplo.com"})
        self.assertIsNone(resposta["codigoDeDemonstracao"])
        self.assertIn("pedidoId", resposta)
        self.codigos.insert_one.assert_called_once()

    def test_codigo_errado_conta_tentativa(self):
        self.codigos.find_one.return_value = self.pedido()
        with self.assertRaises(ErroDeValidacao) as contexto:
            self.redefinir("000000")
        self.assertIn("mais 4 tentativas", contexto.exception.mensagem)
        self.codigos.update_one.assert_called_once_with({"_id": "p1"}, {"$inc": {"tentativas": 1}})

    def test_ultima_tentativa_pede_novo_codigo(self):
        self.codigos.find_one.return_value = self.pedido(tentativas=4)
        with self.assertRaises(ErroDeValidacao) as contexto:
            self.redefinir("000000")
        self.assertEqual(contexto.exception.mensagem, "Código incorreto. Peça um novo.")

    def test_codigo_vencido(self):
        self.codigos.find_one.return_value = self.pedido(expiraEm=para_iso(agora() - timedelta(minutes=1)))
        with self.assertRaises(ErroDeValidacao) as contexto:
            self.redefinir("123456")
        self.assertIn("venceu", contexto.exception.mensagem)

    def test_codigo_certo_troca_a_senha_e_encerra_as_sessoes(self):
        self.codigos.find_one.return_value = self.pedido()
        self.redefinir("123456")
        filtro, mudanca = self.banco("credenciais").update_one.call_args.args
        self.assertEqual(filtro, {"usuarioId": "juliana"})
        self.assertTrue(senha_confere("nova12345", mudanca["$set"]["senhaHash"]))
        self.codigos.delete_one.assert_called_once_with({"_id": "p1"})
        self.banco("sessoes").delete_many.assert_called_once_with({"usuarioId": "juliana", "area": "app"})


if __name__ == "__main__":
    unittest.main()
