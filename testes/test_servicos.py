import unittest

from datas import agora_iso
from erros import Conflito, ErroDeValidacao
from servicos import chamados, conta, painel
from testes.apoio import usar_banco_falso

GESTOR = {"_id": "carla", "nome": "Carla M.", "cargo": "Zeladoria", "subprefeitura": "Butantã"}
EQUIPE_DA_SUBPREFEITURA = {"_id": "e1", "nome": "Equipe Butantã 1", "orgao": "subprefeitura", "prestadoraId": "p1"}


def chamado(**mudancas):
    base = {
        "_id": "c1",
        "protocolo": "48213",
        "status": "validado",
        "orgao": "subprefeitura",
        "endereco": "R. Butantã, 500",
        "abertoEm": agora_iso(),
        "g": 0.8, "e": 0.9, "v": 1, "r": 0.5, "t": 0.1,
    }
    return {**base, **mudancas}


class TesteAcoesDoPainel(unittest.TestCase):
    def setUp(self):
        self.banco = usar_banco_falso(self)
        self.chamados = self.banco("chamados")
        self.chamados.find_one.return_value = chamado()
        self.banco("equipes").find_one.return_value = EQUIPE_DA_SUBPREFEITURA
        self.banco("usuarios").find.return_value = [{"_id": "juliana"}, {"_id": "marta"}]

    def test_despacho_muda_o_status_e_avisa_quem_segue(self):
        resposta = painel.despachar(GESTOR, "c1", {"equipeId": "e1"})
        self.assertIn("#48213", resposta["aviso"])
        mudanca = self.chamados.update_one.call_args.args[1]
        self.assertEqual(mudanca["$set"]["status"], "despachado")
        self.assertEqual(self.banco("notificacoes").insert_one.call_count, 2)

    def test_despacho_exige_a_equipe(self):
        with self.assertRaises(ErroDeValidacao):
            painel.despachar(GESTOR, "c1", {})

    def test_nao_despacha_duas_vezes(self):
        self.chamados.find_one.return_value = chamado(status="despachado")
        with self.assertRaises(Conflito):
            painel.despachar(GESTOR, "c1", {"equipeId": "e1"})
        self.chamados.update_one.assert_not_called()

    def test_equipe_de_outro_orgao(self):
        self.banco("equipes").find_one.return_value = {**EQUIPE_DA_SUBPREFEITURA, "orgao": "cet"}
        with self.assertRaises(Conflito):
            painel.despachar(GESTOR, "c1", {"equipeId": "e1"})

    def test_nao_descarta_chamado_resolvido(self):
        self.chamados.find_one.return_value = chamado(status="resolvido")
        with self.assertRaises(Conflito):
            painel.descartar(GESTOR, "c1", {"motivo": "Sombra de árvore"})

    def test_so_reabre_chamado_com_reparo(self):
        with self.assertRaises(Conflito):
            painel.reabrir_pela_gestao(GESTOR, "c1", {"motivo": "Voltou"})

    def test_status_para_o_gestor(self):
        equipes = [EQUIPE_DA_SUBPREFEITURA]
        self.assertEqual(painel.status_para_gestor(chamado(status="despachado", equipeId="e1"), equipes), "Despachado · Equipe Butantã 1")
        self.assertEqual(painel.status_para_gestor(chamado(status="enviado", orgao="cet"), equipes), "Enviado à CET")
        self.assertEqual(painel.status_para_gestor(chamado(status="programado", agendado=True), equipes), "Agendado no plano semanal")


class TesteChamados(unittest.TestCase):
    def setUp(self):
        self.banco = usar_banco_falso(self)
        self.chamados = self.banco("chamados")

    def test_terceira_falha_sugere_recapeamento(self):
        chamados.reabrir(chamado(r=0.9, falhas12m=2), "O problema voltou")
        mudanca = self.chamados.update_one.call_args.args[1]["$set"]
        self.assertEqual((mudanca["status"], mudanca["r"], mudanca["falhas12m"]), ("reaberto", 1, 3))
        self.assertTrue(mudanca["sugerirRecapeamento"])

    def test_primeira_falha_nao_sugere_recapeamento(self):
        chamados.reabrir(chamado(), "O problema voltou")
        self.assertFalse(self.chamados.update_one.call_args.args[1]["$set"]["sugerirRecapeamento"])

    def test_chamado_descartado_nao_aceita_confirmacao(self):
        self.chamados.find_one.return_value = chamado(status="descartado")
        with self.assertRaises(Conflito):
            chamados.confirmar_reparo({"_id": "juliana"}, "c1", {"resolvido": True, "foto": "data:image/jpeg;base64,AAAA"})

    def test_com_prioridade_explica_o_ipv(self):
        resultado = chamados.com_prioridade(chamado())
        self.assertEqual((resultado["id"], resultado["ipv"], resultado["faixa"]), ("c1", 76.5, "critico"))
        self.assertFalse(resultado["vencido"])


class TesteConta(unittest.TestCase):
    RAFAEL = {"_id": "rafael", "bilheteFinal": "4421", "preferencias": {"avisarOutraPessoa": False, "outraPessoaWhatsapp": ""}}

    def setUp(self):
        self.banco = usar_banco_falso(self)
        self.movimentos = self.banco("movimentosCreditos")
        self.movimentos.find.return_value.sort.return_value = [{"_id": "m1", "pontos": 300, "em": agora_iso()}]
        self.banco("resgates").count_documents.return_value = 2

    def test_resgate_gera_comprovante_e_debita_os_pontos(self):
        resgate = conta.resgatar(self.RAFAEL, {"destino": "bilhete-unico", "pontos": 200})
        self.assertEqual(
            (resgate["comprovante"], resgate["valor"], resgate["saldoDepois"], resgate["final"]),
            ("RC-20933", 10.0, 100, "4421"),
        )
        self.assertEqual(self.movimentos.insert_one.call_args.args[0]["pontos"], -200)

    def test_resgate_acima_do_saldo(self):
        with self.assertRaises(ErroDeValidacao) as contexto:
            conta.resgatar(self.RAFAEL, {"destino": "iptu", "pontos": 400})
        self.assertIn("pontos", contexto.exception.campos)
        self.banco("resgates").insert_one.assert_not_called()

    def test_resgate_com_destino_invalido(self):
        with self.assertRaises(ErroDeValidacao) as contexto:
            conta.resgatar(self.RAFAEL, {"destino": "pix", "pontos": 100})
        self.assertEqual(set(contexto.exception.campos), {"destino"})

    def test_avisar_outra_pessoa_exige_o_whatsapp(self):
        with self.assertRaises(ErroDeValidacao):
            conta.atualizar_preferencias(self.RAFAEL, {"avisarOutraPessoa": True})
        self.banco("usuarios").update_one.assert_not_called()


if __name__ == "__main__":
    unittest.main()
