import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import os

# Clave de las pruebas unitarias; pruebas_integracion.sh define una aleatoria.
os.environ.setdefault("CORE_DB_JWT_CLAVE", "clave-de-las-pruebas-unitarias-de-coredb-0123456789")
