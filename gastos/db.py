"""Acceso a la base de datos SQLite (sin dependencias externas)."""
import sqlite3
from contextlib import contextmanager

ESQUEMA = """
CREATE TABLE IF NOT EXISTS gastos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha       TEXT    NOT NULL,
    centavos    INTEGER NOT NULL CHECK (centavos > 0),
    categoria   TEXT    NOT NULL,
    descripcion TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_gastos_fecha ON gastos (fecha);
CREATE TABLE IF NOT EXISTS presupuestos (
    categoria TEXT PRIMARY KEY,
    centavos  INTEGER NOT NULL CHECK (centavos > 0)
);
"""


class Base:
    """Abre una conexión por operación y confirma o revierte los cambios solos."""

    def __init__(self, ruta):
        self.ruta = str(ruta)
        with self.conexion() as con:
            con.executescript(ESQUEMA)

    @contextmanager
    def conexion(self):
        con = sqlite3.connect(self.ruta)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
