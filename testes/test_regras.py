import unittest
from datetime import timedelta

from datas import agora, para_iso
from erros import ErroDeValidacao
from regras import (
    achar_chamado_no_mesmo_ponto,
    alerta_valido,
    calcular_ipv,
    distancia_em_metros,
    faixa_do_ipv,
    nivel_da_rota,
    pesquisa_binaria,
    resgatado_no_mes,
    situacao_do_prazo,
    validar_resgate,
    validar_senha,
)


class TesteIpv(unittest.TestCase):
    def test_calcula_com_os_pesos_publicos(self):
        ipv, contribuicoes = calcular_ipv({"g": 0.8, "e": 0.9, "v": 1, "r": 0.5, "t": 0.1})
        self.assertEqual(ipv, 76.5)
        self.assertEqual(contribuicoes["g"], 28.0)

    def test_recusa_valor_fora_de_0_a_1(self):
        with self.assertRaises(ErroDeValidacao):
            calcular_ipv({"g": 1.2, "e": 0, "v": 0, "r": 0, "t": 0})

    def test_faixas(self):
        self.assertEqual(faixa_do_ipv(70), "critico")
        self.assertEqual(faixa_do_ipv(69.9), "alto")
        self.assertEqual(faixa_do_ipv(39.9), "programado")

    def test_prazo_vencido(self):
        chamado = {
            "status": "validado",
            "abertoEm": para_iso(agora() - timedelta(hours=30)),
            "g": 1, "e": 1, "v": 1, "r": 0, "t": 0,
        }
        texto, vencido = situacao_do_prazo(chamado, agora())
        self.assertTrue(vencido)
        self.assertEqual(texto, "Vencido há 6 h")


class TesteDeduplicacao(unittest.TestCase):
    def test_mesmo_ponto_a_ate_15_metros(self):
        chamados = [
            {"id": "a", "categoria": "buraco", "status": "validado", "lat": -23.5838, "lng": -46.7190},
            {"id": "b", "categoria": "buraco", "status": "resolvido", "lat": -23.5838, "lng": -46.7190},
        ]
        achado = achar_chamado_no_mesmo_ponto(chamados, -23.58385, -46.71905, "buraco")
        self.assertEqual(achado[0]["id"], "a")
        self.assertIsNone(achar_chamado_no_mesmo_ponto(chamados, -23.5850, -46.7190, "buraco"))
        self.assertIsNone(achar_chamado_no_mesmo_ponto(chamados, -23.5838, -46.7190, "faixa"))

    def test_distancia(self):
        self.assertAlmostEqual(distancia_em_metros(0, 0, 0, 0.001), 111.2, places=0)


class TesteCreditos(unittest.TestCase):
    def test_validar_resgate(self):
        self.assertIn("mínimo", validar_resgate(50, 500, 0))
        self.assertIn("Você tem 300", validar_resgate(400, 300, 0))
        self.assertIn("ainda pode usar 100", validar_resgate(200, 2000, 900))
        self.assertIsNone(validar_resgate(100, 300, 0))

    def test_resgatado_no_mes_soma_so_saidas_do_mes(self):
        momento = agora()
        movimentos = [
            {"pontos": -100, "em": para_iso(momento)},
            {"pontos": 50, "em": para_iso(momento)},
            {"pontos": -300, "em": para_iso(momento - timedelta(days=40))},
        ]
        self.assertEqual(resgatado_no_mes(movimentos, momento), 100)


class TesteAcessoEAlertas(unittest.TestCase):
    def test_validar_senha(self):
        self.assertIsNotNone(validar_senha("curta1", "curta1"))
        self.assertEqual(validar_senha("somenteletras", "somenteletras"), "Misture letras e números.")
        self.assertIsNone(validar_senha("senha1234", "senha1234"))

    def test_intransitavel_exige_camera_ou_duas_fontes(self):
        base = {"nivel": "intransitavel", "confirmadoEm": para_iso(agora()), "temCameraFixa": False}
        self.assertFalse(alerta_valido({**base, "fontes": ["Ônibus 4313"]}, agora()))
        self.assertTrue(alerta_valido({**base, "fontes": ["Ônibus 4313", "Kit"]}, agora()))

    def test_alerta_expira_em_30_minutos(self):
        alerta = {
            "nivel": "atencao", "fontes": [], "temCameraFixa": True,
            "confirmadoEm": para_iso(agora() - timedelta(minutes=31)),
        }
        self.assertFalse(alerta_valido(alerta, agora()))

    def test_nivel_da_rota_e_o_pior(self):
        alertas = [
            {"nivel": "atencao", "rotaIds": ["r1"]},
            {"nivel": "evitar", "rotaIds": ["r1", "r2"]},
        ]
        self.assertEqual(nivel_da_rota("r1", alertas)[0], "evitar")
        self.assertEqual(nivel_da_rota("r3", alertas)[0], "livre")


class TesteBusca(unittest.TestCase):
    def test_pesquisa_binaria(self):
        lista = [{"protocolo": n} for n in (10, 20, 30, 40)]
        self.assertEqual(pesquisa_binaria(lista, 30, lambda c: c["protocolo"]), 2)
        self.assertIsNone(pesquisa_binaria(lista, 25, lambda c: c["protocolo"]))


if __name__ == "__main__":
    unittest.main()
