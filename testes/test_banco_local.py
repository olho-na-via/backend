import os
import tempfile
import unittest

from banco_local import BancoLocal


class TestBancoLocal(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        self.banco = BancoLocal(self.pasta)
        self.banco.chamados.insert_many([
            {"_id": "1", "status": "validado", "bairro": "Butantã", "seguidores": 1, "tags": ["a"], "linhaDoTempo": []},
            {"_id": "2", "status": "descartado", "bairro": "Lapa", "seguidores": 0, "tags": [], "linhaDoTempo": []},
            {"_id": "3", "status": "validado", "bairro": "Lapa", "seguidores": 2, "tags": ["b"], "linhaDoTempo": []},
        ])

    def ids(self, filtro, projecao=None):
        return [documento["_id"] for documento in self.banco.chamados.find(filtro, projecao)]

    def test_filtros(self):
        self.assertEqual(self.ids({"status": {"$ne": "descartado"}}), ["1", "3"])
        self.assertEqual(self.ids({"_id": {"$in": ["2", "3"]}}), ["2", "3"])
        self.assertEqual(self.ids({"seguidores": {"$gt": 0}}), ["1", "3"])
        self.assertEqual(self.ids({"tags": "b"}), ["3"])
        self.assertEqual(self.ids({"$or": [{"bairro": {"$regex": "butan", "$options": "i"}}, {"_id": "2"}]}), ["1", "2"])

    def test_projecao_e_ordem(self):
        documento = self.banco.chamados.find_one({"_id": "1"}, {"linhaDoTempo": 0})
        self.assertNotIn("linhaDoTempo", documento)
        self.assertEqual(self.banco.chamados.find_one({"_id": "1"}, {"status": 1}), {"_id": "1", "status": "validado"})
        ordem = [documento["_id"] for documento in self.banco.chamados.find().sort("seguidores", -1)]
        self.assertEqual(ordem, ["3", "1", "2"])

    def test_atualizacoes(self):
        self.banco.chamados.update_one({"_id": "1"}, {
            "$set": {"status": "despachado", "fotos.depois": "x"},
            "$inc": {"seguidores": 1},
            "$push": {"linhaDoTempo": {"tipo": "despachado"}},
            "$addToSet": {"tags": "a"},
        })
        documento = self.banco.chamados.find_one({"_id": "1"})
        self.assertEqual(documento["status"], "despachado")
        self.assertEqual(documento["fotos"], {"depois": "x"})
        self.assertEqual(documento["seguidores"], 2)
        self.assertEqual(documento["linhaDoTempo"], [{"tipo": "despachado"}])
        self.assertEqual(documento["tags"], ["a"])
        self.banco.chamados.update_one({"_id": "1"}, {"$pull": {"tags": "a"}})
        self.assertEqual(self.banco.chamados.find_one({"_id": "1"})["tags"], [])
        self.assertEqual(self.banco.chamados.update_many({"bairro": "Lapa"}, {"$set": {"lida": True}}).modified_count, 2)

    def test_remocao_e_contagem(self):
        self.assertEqual(self.banco.chamados.delete_many({"bairro": "Lapa"}).deleted_count, 2)
        self.assertEqual(self.banco.chamados.count_documents({}), 1)
        self.banco.chamados.drop()
        self.assertEqual(self.banco.chamados.count_documents({}), 0)

    def test_agregacao(self):
        etapas = [
            {"$match": {"bairro": "Lapa"}},
            {"$group": {"_id": {"status": "$status"}, "total": {"$sum": 1}}},
        ]
        grupos = sorted(self.banco.chamados.aggregate(etapas), key=lambda grupo: grupo["_id"]["status"])
        self.assertEqual(grupos, [{"_id": {"status": "descartado"}, "total": 1}, {"_id": {"status": "validado"}, "total": 1}])

    def test_grava_em_json_e_le_em_outro_processo(self):
        self.banco.chamados.update_one({"_id": "2"}, {"$set": {"status": "reaberto"}})
        self.assertTrue(os.path.exists(os.path.join(self.pasta, "chamados.json")))
        outro = BancoLocal(self.pasta)
        self.assertEqual(outro.chamados.find_one({"_id": "2"})["status"], "reaberto")

    def test_operador_desconhecido_avisa(self):
        with self.assertRaises(ValueError):
            self.ids({"seguidores": {"$lt": 1}})


if __name__ == "__main__":
    unittest.main()
