import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from gastos.db import Base
from gastos.servicio import Servicio
from gastos.servidor import crear_servidor


class PruebasApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.srv = crear_servidor(Servicio(Base(os.path.join(cls.tmp.name, "t.db"))), puerto=0)
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.tmp.cleanup()

    def pedir(self, ruta, metodo="GET", datos=None):
        req = urllib.request.Request(self.url + ruta, method=metodo,
                                     data=json.dumps(datos).encode() if datos is not None else None,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_pagina_principal(self):
        codigo, cuerpo = self.pedir("/")
        self.assertEqual(codigo, 200)
        self.assertIn(b"Control de", cuerpo)

    def test_flujo_completo(self):
        c, b = self.pedir("/api/gastos", "POST",
                          {"fecha": "2026-11-05", "monto": "25000", "categoria": "Comida", "descripcion": "Cena"})
        self.assertEqual(c, 201)
        id_ = json.loads(b)["id"]
        c, b = self.pedir("/api/resumen?mes=2026-11")
        self.assertEqual(json.loads(b)["total"], 25000)
        c, b = self.pedir("/api/exportar?mes=2026-11")
        self.assertIn("Cena", b.decode("utf-8-sig"))
        self.assertEqual(self.pedir(f"/api/gastos/{id_}", "DELETE")[0], 200)
        self.assertEqual(self.pedir(f"/api/gastos/{id_}", "DELETE")[0], 404)

    def test_errores_claros(self):
        c, b = self.pedir("/api/gastos", "POST", {"fecha": "2026-11-05", "monto": "abc", "categoria": "Comida"})
        self.assertEqual(c, 400)
        self.assertIn("monto", json.loads(b)["error"])
        self.assertEqual(self.pedir("/api/gastos?mes=xx")[0], 400)
        self.assertEqual(self.pedir("/api/nada")[0], 404)


if __name__ == "__main__":
    unittest.main()
