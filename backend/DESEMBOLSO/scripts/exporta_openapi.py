"""Escribe DESEMBOLSO/openapi.json, la especificación publicada. Desde backend/:

    python -m DESEMBOLSO.scripts.exporta_openapi
"""
import json
from pathlib import Path

from DESEMBOLSO.config import Config
from DESEMBOLSO.main import crear_app

if __name__ == "__main__":
    destino = Path(__file__).resolve().parents[1] / "openapi.json"
    aplicacion = crear_app(Config(_env_file=None, trabajos_habilitados=False))
    destino.write_text(json.dumps(aplicacion.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Escrito {destino}")
