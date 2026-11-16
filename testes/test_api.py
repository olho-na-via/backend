import unittest
from datetime import timedelta

from pymongo.errors import ServerSelectionTimeoutError

from app import criar_app
from datas import agora, agora_iso, para_iso
from testes.apoio import usar_banco_falso


class TesteApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cliente = criar_app().test_client()

    def setUp(self):
        self.banco = usar_banco_falso(self)

    def entrar_como(self, area):
        self.banco("sessoes").find_one.return_value = {
            "_id": "t", "usuarioId": "juliana", "area": area, "expiraEm": para_iso(agora() + timedelta(days=1)),
        }
        return {"Authorization": "Bearer t"}

    def test_rota_protegida_sem_token(self):
        for cabecalho in ({}, {"Authorization": "Token t"}, {"Authorization": "Bearer "}):
            resposta = self.cliente.get("/api/eu", headers=cabecalho)
            self.assertEqual(resposta.status_code, 401)
            self.assertEqual(resposta.get_json(), {"erro": "Entre na sua conta para continuar."})

    def test_token_do_cidadao_nao_abre_o_painel(self):
        resposta = self.cliente.get("/api/painel/fila", headers=self.entrar_como("app"))
        self.assertEqual(resposta.status_code, 401)

    def test_perfil_com_sessao_valida(self):
        self.banco("usuarios").find_one.return_value = {"_id": "juliana", "nome": "Juliana"}
        self.banco("notificacoes").count_documents.return_value = 3
        self.banco("movimentosCreditos").find.return_value.sort.return_value = [{"_id": "m1", "pontos": 40, "em": agora_iso()}]
        resposta = self.cliente.get("/api/eu", headers=self.entrar_como("app"))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json(), {"id": "juliana", "nome": "Juliana", "naoLidas": 3, "saldo": 40})

    def test_corpo_precisa_ser_um_objeto_json(self):
        resposta = self.cliente.post("/api/acesso/entrar", json=[1, 2])
        self.assertEqual((resposta.status_code, resposta.get_json()["erro"]), (400, "Envie os dados como um objeto JSON."))

    def test_erro_de_validacao_mostra_os_campos(self):
        resposta = self.cliente.post("/api/acesso/entrar", json={})
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(set(resposta.get_json()["campos"]), {"email", "senha"})

    def test_endereco_e_metodo_inexistentes(self):
        self.assertEqual(self.cliente.get("/nao-existe").get_json(), {"erro": "Não encontramos esse endereço."})
        self.assertEqual(self.cliente.delete("/api/acesso/entrar").status_code, 405)

    def test_banco_fora_do_ar_vira_503(self):
        self.banco("sessoes").find_one.side_effect = ServerSelectionTimeoutError("sem conexão")
        resposta = self.cliente.get("/api/eu", headers={"Authorization": "Bearer t"})
        self.assertEqual(resposta.status_code, 503)

    def test_erro_inesperado_vira_500_sem_detalhes(self):
        self.banco("sessoes").find_one.side_effect = RuntimeError("detalhe interno")
        resposta = self.cliente.get("/api/eu", headers={"Authorization": "Bearer t"})
        self.assertEqual(resposta.status_code, 500)
        self.assertNotIn("detalhe interno", resposta.get_data(as_text=True))

    def test_swagger_documenta_as_rotas(self):
        caminhos = self.cliente.get("/openapi.json").get_json()["paths"]
        self.assertIn("/api/acesso/entrar", caminhos)
        self.assertIn("/api/painel/chamados/{chamado_id}/despacho", caminhos)
        self.assertEqual(self.cliente.get("/").headers["Location"], "/docs/")


if __name__ == "__main__":
    unittest.main()
