import os
import tempfile
import unittest

from gastos.db import Base
from gastos.servicio import ErrorValidacion, NoEncontrado, Servicio, a_centavos


class PruebasServicio(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.s = Servicio(Base(os.path.join(self.tmp.name, "t.db")))

    def tearDown(self):
        self.tmp.cleanup()

    def test_montos_sin_errores_de_redondeo(self):
        self.assertEqual(a_centavos("0.10") + a_centavos("0.20"), a_centavos("0.30"))
        self.assertEqual(a_centavos("12,50"), 1250)

    def test_rechaza_montos_invalidos(self):
        for malo in ("abc", "", "-5", "0", "nan", "inf", None):
            with self.assertRaises(ErrorValidacion):
                a_centavos(malo)

    def test_agregar_y_listar_por_mes(self):
        self.s.agregar_gasto("2026-11-05", "15000", "Comida", "Almuerzo")
        self.s.agregar_gasto("2026-10-30", "9000", "Ocio")
        self.assertEqual(len(self.s.listar_gastos("2026-11")), 1)
        self.assertEqual(self.s.listar_gastos("2026-10")[0]["monto"], 9000)

    def test_validaciones_de_gasto(self):
        with self.assertRaises(ErrorValidacion):
            self.s.agregar_gasto("2026-13-40", "100", "Comida")
        with self.assertRaises(ErrorValidacion):
            self.s.agregar_gasto("2026-11-05", "100", "Inventada")
        with self.assertRaises(ErrorValidacion):
            self.s.agregar_gasto("2026-11-05", "100", "Comida", "x" * 121)

    def test_eliminar(self):
        g = self.s.agregar_gasto("2026-11-05", "100", "Comida")
        self.s.eliminar_gasto(g["id"])
        with self.assertRaises(NoEncontrado):
            self.s.eliminar_gasto(g["id"])

    def test_resumen_y_estados_de_presupuesto(self):
        self.s.fijar_presupuesto("Comida", "100000")
        self.s.agregar_gasto("2026-11-01", "50000", "Comida")
        r = self.s.resumen("2026-11")
        c = next(x for x in r["categorias"] if x["categoria"] == "Comida")
        self.assertEqual((c["porcentaje"], c["estado"]), (50, "ok"))
        self.s.agregar_gasto("2026-11-02", "35000", "Comida")
        self.assertEqual(self.s.resumen("2026-11")["categorias"][0]["estado"], "cerca")
        self.s.agregar_gasto("2026-11-03", "20000", "Comida")
        self.assertEqual(self.s.resumen("2026-11")["categorias"][0]["estado"], "excedido")
        self.assertEqual(self.s.resumen("2026-11")["total"], 105000)

    def test_quitar_presupuesto_con_cero(self):
        self.s.fijar_presupuesto("Hogar", "500")
        self.s.fijar_presupuesto("Hogar", "0")
        hogar = next(x for x in self.s.resumen("2026-11")["categorias"] if x["categoria"] == "Hogar")
        self.assertIsNone(hogar["limite"])

    def test_csv_evita_inyeccion_de_formulas(self):
        self.s.agregar_gasto("2026-11-05", "100", "Otros", "=HYPERLINK(\"x\")")
        self.assertIn("'=HYPERLINK", self.s.exportar_csv("2026-11"))

    def test_mes_invalido(self):
        with self.assertRaises(ErrorValidacion):
            self.s.listar_gastos("noviembre")


if __name__ == "__main__":
    unittest.main()
