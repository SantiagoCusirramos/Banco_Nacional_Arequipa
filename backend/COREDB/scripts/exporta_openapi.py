"""Escribe backend/COREDB/openapi.json. Uso, desde backend/: python -m COREDB.scripts.exporta_openapi"""

import json
from pathlib import Path

from COREDB.main import app

ARCHIVO = Path(__file__).resolve().parents[1] / "openapi.json"


def especificacion() -> str:
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    ARCHIVO.write_text(especificacion(), encoding="utf-8")
