"""Punto de entrada: python main.py"""
import argparse
import threading
import webbrowser
from pathlib import Path

from gastos.db import Base
from gastos.servicio import Servicio
from gastos.servidor import crear_servidor


def main():
    p = argparse.ArgumentParser(description="Control de Gastos: tu dinero, claro y sin complicaciones.")
    p.add_argument("--puerto", type=int, default=8000, help="Puerto local (por defecto 8000)")
    p.add_argument("--db", default=str(Path(__file__).parent / "gastos.db"),
                   help="Archivo donde se guardan los datos")
    p.add_argument("--no-abrir", action="store_true", help="No abrir el navegador automáticamente")
    a = p.parse_args()

    try:
        servidor = crear_servidor(Servicio(Base(a.db)), puerto=a.puerto)
    except OSError:
        raise SystemExit(f"El puerto {a.puerto} está ocupado. Prueba con: python main.py --puerto {a.puerto + 1}")

    url = f"http://127.0.0.1:{a.puerto}"
    print(f"Control de Gastos listo en {url}\nPresiona Ctrl+C para cerrar.")
    if not a.no_abrir:
        threading.Timer(0.6, webbrowser.open, args=(url,)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nHasta pronto.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
