"""Reglas de negocio: validación, cálculos y exportación.

El dinero se guarda en centavos (enteros) para evitar errores de redondeo.
"""
import csv
import io
import re
from datetime import date
from decimal import Decimal, InvalidOperation

CATEGORIAS = ["Comida", "Transporte", "Hogar", "Salud", "Ocio", "Educación", "Otros"]
MAX_CENTAVOS = 10**13
_PATRON_MES = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class ErrorValidacion(ValueError):
    """Dato inválido enviado por la persona usuaria."""


class NoEncontrado(LookupError):
    """El registro pedido no existe."""


def a_centavos(valor, permitir_cero=False):
    mensaje = "Escribe un monto válido, por ejemplo 15000 o 12.50."
    try:
        monto = Decimal(str(valor).strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        raise ErrorValidacion(mensaje)
    if not monto.is_finite():
        raise ErrorValidacion(mensaje)
    centavos = int((monto * 100).to_integral_value())
    if centavos < 0 or (centavos == 0 and not permitir_cero):
        raise ErrorValidacion("El monto debe ser mayor que cero.")
    if centavos >= MAX_CENTAVOS:
        raise ErrorValidacion("El monto es demasiado grande.")
    return centavos


def validar_mes(mes):
    if mes is None:
        return date.today().strftime("%Y-%m")
    if not _PATRON_MES.match(str(mes)):
        raise ErrorValidacion("El mes debe tener el formato AAAA-MM, por ejemplo 2026-11.")
    return mes


def _validar_categoria(categoria):
    if categoria not in CATEGORIAS:
        raise ErrorValidacion("Elige una categoría de la lista.")
    return categoria


def _fila_gasto(f):
    return {"id": f["id"], "fecha": f["fecha"], "monto": f["centavos"] / 100,
            "categoria": f["categoria"], "descripcion": f["descripcion"]}


class Servicio:
    def __init__(self, base):
        self.base = base

    def agregar_gasto(self, fecha, monto, categoria, descripcion=""):
        try:
            fecha = date.fromisoformat(str(fecha)).isoformat()
        except ValueError:
            raise ErrorValidacion("Escribe una fecha válida con el formato AAAA-MM-DD.")
        centavos = a_centavos(monto)
        _validar_categoria(categoria)
        descripcion = str(descripcion or "").strip()
        if len(descripcion) > 120:
            raise ErrorValidacion("La descripción puede tener máximo 120 caracteres.")
        with self.base.conexion() as con:
            cur = con.execute(
                "INSERT INTO gastos (fecha, centavos, categoria, descripcion) VALUES (?,?,?,?)",
                (fecha, centavos, categoria, descripcion))
            return {"id": cur.lastrowid, "fecha": fecha, "monto": centavos / 100,
                    "categoria": categoria, "descripcion": descripcion}

    def listar_gastos(self, mes=None):
        mes = validar_mes(mes)
        with self.base.conexion() as con:
            filas = con.execute(
                "SELECT * FROM gastos WHERE substr(fecha,1,7)=? ORDER BY fecha DESC, id DESC",
                (mes,)).fetchall()
        return [_fila_gasto(f) for f in filas]

    def eliminar_gasto(self, id_gasto):
        with self.base.conexion() as con:
            if con.execute("DELETE FROM gastos WHERE id=?", (id_gasto,)).rowcount == 0:
                raise NoEncontrado("Ese gasto ya no existe.")

    def fijar_presupuesto(self, categoria, monto):
        _validar_categoria(categoria)
        centavos = a_centavos(monto, permitir_cero=True)
        with self.base.conexion() as con:
            if centavos == 0:  # un monto de 0 quita el presupuesto
                con.execute("DELETE FROM presupuestos WHERE categoria=?", (categoria,))
            else:
                con.execute(
                    "INSERT INTO presupuestos (categoria, centavos) VALUES (?,?) "
                    "ON CONFLICT(categoria) DO UPDATE SET centavos=excluded.centavos",
                    (categoria, centavos))
        return {"categoria": categoria, "limite": centavos / 100 if centavos else None}

    def resumen(self, mes=None):
        mes = validar_mes(mes)
        with self.base.conexion() as con:
            gastado = {f["categoria"]: f["total"] for f in con.execute(
                "SELECT categoria, SUM(centavos) AS total FROM gastos "
                "WHERE substr(fecha,1,7)=? GROUP BY categoria", (mes,))}
            limites = {f["categoria"]: f["centavos"] for f in con.execute(
                "SELECT categoria, centavos FROM presupuestos")}
        categorias, total = [], 0
        for cat in CATEGORIAS:
            g, lim = gastado.get(cat, 0), limites.get(cat)
            total += g
            pct = round(g / lim * 100) if lim else None
            estado = None if lim is None else ("excedido" if g > lim else "cerca" if pct >= 80 else "ok")
            categorias.append({"categoria": cat, "gastado": g / 100,
                               "limite": lim / 100 if lim else None,
                               "porcentaje": pct, "estado": estado})
        return {"mes": mes, "total": total / 100, "categorias": categorias}

    def exportar_csv(self, mes=None):
        salida = io.StringIO()
        escritor = csv.writer(salida)
        escritor.writerow(["fecha", "categoria", "monto", "descripcion"])
        for g in self.listar_gastos(mes):
            desc = g["descripcion"]
            if desc[:1] in ("=", "+", "-", "@"):  # evita fórmulas maliciosas en Excel
                desc = "'" + desc
            escritor.writerow([g["fecha"], g["categoria"], f"{g['monto']:.2f}", desc])
        return salida.getvalue()
