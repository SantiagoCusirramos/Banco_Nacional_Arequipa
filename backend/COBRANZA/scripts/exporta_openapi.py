"""Escribe COBRANZA/openapi.json, la especificación publicada. Desde backend/:

    python -m COBRANZA.scripts.exporta_openapi
"""
import json
from pathlib import Path

from COBRANZA.main import crear_app

if __name__ == "__main__":
    destino = Path(__file__).resolve().parents[1] / "openapi.json"
    destino.write_text(json.dumps(crear_app().openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Escrito {destino}")
