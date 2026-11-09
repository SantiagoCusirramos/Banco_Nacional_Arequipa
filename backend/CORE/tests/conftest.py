import os
import sys
from pathlib import Path

# backend/.env no se versiona: las pruebas no deben depender de que exista.
os.environ.setdefault("SECRET_KEY", "clave-de-las-pruebas-unitarias-de-core")

# Asegura que `CORE` sea importable desde backend/
BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
