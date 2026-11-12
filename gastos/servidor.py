"""Servidor web local: una API JSON pequeña y la página de la aplicación."""
import json
import logging
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .servicio import CATEGORIAS, ErrorValidacion, NoEncontrado

PAGINA = Path(__file__).parent / "static" / "index.html"
MAX_CUERPO = 10_000


def crear_servidor(servicio, host="127.0.0.1", puerto=8000):
    class Manejador(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _enviar(self, codigo, cuerpo, tipo, extra=None):
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(cuerpo)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(cuerpo)

        def _json(self, codigo, datos):
            cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
            self._enviar(codigo, cuerpo, "application/json; charset=utf-8")

        def _leer(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_CUERPO:
                raise ErrorValidacion("Los datos enviados son demasiado grandes.")
            try:
                datos = json.loads(self.rfile.read(n) or b"{}")
            except json.JSONDecodeError:
                raise ErrorValidacion("Los datos enviados no son válidos.")
            if not isinstance(datos, dict):
                raise ErrorValidacion("Los datos enviados no son válidos.")
            return datos

        def _atender(self, funcion):
            try:
                funcion()
            except ErrorValidacion as e:
                self._json(400, {"error": str(e)})
            except NoEncontrado as e:
                self._json(404, {"error": str(e)})
            except Exception:
                logging.exception("Error inesperado")
                self._json(500, {"error": "Algo salió mal. Intenta de nuevo."})

        def do_GET(self):
            self._atender(self._get)

        def do_POST(self):
            self._atender(self._post)

        def do_DELETE(self):
            self._atender(self._delete)

        def _get(self):
            url = urlparse(self.path)
            mes = parse_qs(url.query).get("mes", [None])[0]
            if url.path == "/":
                self._enviar(200, PAGINA.read_bytes(), "text/html; charset=utf-8")
            elif url.path == "/api/categorias":
                self._json(200, CATEGORIAS)
            elif url.path == "/api/gastos":
                self._json(200, servicio.listar_gastos(mes))
            elif url.path == "/api/resumen":
                self._json(200, servicio.resumen(mes))
            elif url.path == "/api/exportar":
                nombre = f"gastos-{servicio.resumen(mes)['mes']}.csv"
                self._enviar(200, servicio.exportar_csv(mes).encode("utf-8-sig"),
                             "text/csv; charset=utf-8",
                             {"Content-Disposition": f'attachment; filename="{nombre}"'})
            else:
                self._json(404, {"error": "Página no encontrada."})

        def _post(self):
            ruta, d = urlparse(self.path).path, self._leer()
            if ruta == "/api/gastos":
                self._json(201, servicio.agregar_gasto(
                    d.get("fecha"), d.get("monto"), d.get("categoria"), d.get("descripcion")))
            elif ruta == "/api/presupuestos":
                self._json(200, servicio.fijar_presupuesto(d.get("categoria"), d.get("monto")))
            else:
                self._json(404, {"error": "Página no encontrada."})

        def _delete(self):
            m = re.fullmatch(r"/api/gastos/(\d+)", urlparse(self.path).path)
            if not m:
                raise NoEncontrado("Página no encontrada.")
            servicio.eliminar_gasto(int(m.group(1)))
            self._json(200, {"ok": True})

    return ThreadingHTTPServer((host, puerto), Manejador)
