"""Escribe backend/COBRANZA/openapi.json (RNF-23: toda interfaz publica su especificación OpenAPI).
Uso, desde backend/: python -m COBRANZA.scripts.exporta_openapi"""

import json
from pathlib import Path

from COBRANZA.main import app

ARCHIVO = Path(__file__).resolve().parents[1] / "openapi.json"


def especificacion() -> str:
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    ARCHIVO.write_text(especificacion(), encoding="utf-8")
