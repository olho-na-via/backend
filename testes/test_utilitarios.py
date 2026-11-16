import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from config import ler_arquivo_de_ambiente
from datas import dia_em_sao_paulo, ler_data, para_iso
from erros import Conflito, ErroDaApi, ErroDeValidacao, NaoAutenticado, NaoEncontrado
from seed import deslocar_datas
from seguranca import gerar_codigo, gerar_hash, gerar_token, senha_confere
from validacao import conferir, ler_booleano, ler_horario, ler_numero, ler_opcao, ler_texto


class TesteSeguranca(unittest.TestCase):
    def test_hash_confere_so_com_a_senha_certa(self):
        guardado = gerar_hash("senha1234")
        self.assertNotIn("senha1234", guardado)
        self.assertTrue(senha_confere("senha1234", guardado))
        self.assertFalse(senha_confere("senha1235", guardado))

    def test_mesma_senha_gera_hashes_diferentes(self):
        self.assertNotEqual(gerar_hash("senha1234"), gerar_hash("senha1234"))

    def test_hash_estragado_nao_confere(self):
        self.assertFalse(senha_confere("senha1234", "texto-qualquer"))
        self.assertFalse(senha_confere("senha1234", None))

    def test_codigo_tem_6_numeros_e_token_e_unico(self):
        codigo = gerar_codigo()
        self.assertEqual(len(codigo), 6)
        self.assertTrue(codigo.isdigit())
        self.assertNotEqual(gerar_token(), gerar_token())


class TesteValidacao(unittest.TestCase):
    def test_ler_texto(self):
        erros = {}
        self.assertEqual(ler_texto({"nome": "  Ana  "}, "nome", erros, "Obrigatório"), "Ana")
        self.assertIsNone(ler_texto({"nome": "   "}, "nome", erros, "Obrigatório"))
        self.assertEqual(erros["nome"], "Obrigatório")

    def test_ler_texto_opcional_tipo_errado_e_limite(self):
        erros = {}
        self.assertIsNone(ler_texto({}, "apelido", erros, "", obrigatorio=False))
        ler_texto({"nome": 42}, "nome", erros, "Use texto.")
        ler_texto({"bairro": "x" * 81}, "bairro", erros, "", maximo=80)
        self.assertEqual(erros, {"nome": "Use texto.", "bairro": "Use até 80 caracteres."})

    def test_ler_numero_recusa_booleano_e_fora_do_limite(self):
        erros = {}
        self.assertEqual(ler_numero({"g": 0.5}, "g", erros, "erro", minimo=0, maximo=1), 0.5)
        self.assertIsNone(ler_numero({"g": True}, "g", erros, "erro"))
        self.assertIsNone(ler_numero({"r": 1.5}, "r", erros, "erro", minimo=0, maximo=1))
        self.assertIsNone(ler_numero({"pontos": 10.5}, "pontos", erros, "erro", inteiro=True))
        self.assertEqual(set(erros), {"g", "r", "pontos"})

    def test_ler_opcao_booleano_e_horario(self):
        erros = {}
        self.assertEqual(ler_opcao({"meio": "onibus"}, "meio", erros, ("onibus",), "erro"), "onibus")
        self.assertIsNone(ler_booleano({"push": "sim"}, "push", erros, "erro"))
        self.assertEqual(ler_horario({"de": "22:00"}, "de", erros, "erro"), "22:00")
        self.assertIsNone(ler_horario({"ate": "24:00"}, "ate", erros, "erro"))
        self.assertEqual(set(erros), {"push", "ate"})

    def test_conferir_junta_os_campos_no_erro(self):
        conferir({})
        with self.assertRaises(ErroDeValidacao) as contexto:
            conferir({"email": "Digite um e-mail."})
        self.assertEqual(contexto.exception.campos, {"email": "Digite um e-mail."})


class TesteErros(unittest.TestCase):
    def test_cada_erro_tem_o_seu_codigo_http(self):
        self.assertEqual(
            [ErroDaApi.status, ErroDeValidacao.status, NaoAutenticado.status, NaoEncontrado.status, Conflito.status],
            [400, 400, 401, 404, 409],
        )

    def test_para_dict_so_mostra_campos_quando_existem(self):
        self.assertEqual(Conflito("Já existe.").para_dict(), {"erro": "Já existe."})
        self.assertEqual(
            ErroDeValidacao("Confira.", {"nome": "Obrigatório"}).para_dict(),
            {"erro": "Confira.", "campos": {"nome": "Obrigatório"}},
        )


class TesteDatas(unittest.TestCase):
    def test_iso_em_utc_com_milissegundos(self):
        momento = datetime(2026, 3, 1, 12, 30, tzinfo=timezone(timedelta(hours=-3)))
        self.assertEqual(para_iso(momento), "2026-03-01T15:30:00.000Z")
        self.assertEqual(ler_data("2026-03-01T15:30:00.000Z"), momento)

    def test_dia_em_sao_paulo(self):
        self.assertEqual(str(dia_em_sao_paulo(ler_data("2026-03-02T01:00:00.000Z"))), "2026-03-01")


class TesteConfiguracao(unittest.TestCase):
    def test_le_arquivo_de_ambiente(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, ".env")
            with open(caminho, "w", encoding="utf-8") as arquivo:
                arquivo.write('# comentário\nMONGODB_BANCO="teste"\nOLHO_PORTA = 8000\nlinha sem igual\n')
            self.assertEqual(ler_arquivo_de_ambiente(caminho), {"MONGODB_BANCO": "teste", "OLHO_PORTA": "8000"})

    def test_arquivo_que_nao_existe_vira_vazio(self):
        self.assertEqual(ler_arquivo_de_ambiente("nao-existe.env"), {})


class TesteSeed(unittest.TestCase):
    def test_desloca_so_as_datas(self):
        dados = {"abertoEm": "2026-01-01T10:00:00.000Z", "linhaDoTempo": [{"em": "2026-01-01T10:00:00Z"}], "protocolo": "2026", "g": 1}
        deslocado = deslocar_datas(dados, timedelta(days=1))
        self.assertEqual(deslocado["abertoEm"], "2026-01-02T10:00:00.000Z")
        self.assertEqual(deslocado["linhaDoTempo"][0]["em"], "2026-01-02T10:00:00.000Z")
        self.assertEqual((deslocado["protocolo"], deslocado["g"]), ("2026", 1))


if __name__ == "__main__":
    unittest.main()
