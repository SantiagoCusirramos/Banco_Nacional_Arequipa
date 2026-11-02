"""Configuración de las pruebas de extremo a extremo (sistema levantado + datos de prueba cargados).

Ejecutar:  pytest tests/e2e -m "e2e and not reniec_caido"
Variables opcionales: RENIEC_URL_HOST, CLIENTES_URL_HOST (por defecto http://localhost:8002 y :8001).
Credenciales: se leen de .env (o de las variables RENIEC_ADMIN_*, CLIENTES_PANEL_*).
"""
import os
from pathlib import Path

import httpx
import pytest

RAIZ = Path(__file__).resolve().parents[2]


def _env() -> dict:
    valores = {}
    archivo = RAIZ / ".env"
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            if linea.strip() and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                valores[k.strip()] = v.strip()
    for k in list(valores) + ["RENIEC_ADMIN_USER", "RENIEC_ADMIN_PASSWORD", "CLIENTES_PANEL_USER", "CLIENTES_PANEL_PASSWORD"]:
        if k in os.environ:
            valores[k] = os.environ[k]
    return valores


ENV = _env()
CLIENTES = os.getenv("CLIENTES_URL_HOST", f"http://localhost:{ENV.get('PUERTO_CLIENTES', '8001')}")
RENIEC = os.getenv("RENIEC_URL_HOST", f"http://localhost:{ENV.get('PUERTO_RENIEC', '8002')}")


class Sistema:
    def __init__(self):
        self.reniec = httpx.Client(base_url=RENIEC, auth=(ENV["RENIEC_ADMIN_USER"], ENV["RENIEC_ADMIN_PASSWORD"]), timeout=180)
        self.panel = httpx.Client(base_url=CLIENTES, auth=(ENV["CLIENTES_PANEL_USER"], ENV["CLIENTES_PANEL_PASSWORD"]), timeout=180)
        self.publico = httpx.Client(base_url=CLIENTES, timeout=30)  # sin credenciales

    def lab(self, operacion: str, cuerpo: dict) -> tuple[int, dict]:
        """Envía una operación ENTRANDO por el Bus (como otro módulo) y devuelve (http, respuesta)."""
        r = self.panel.post(f"/panel/api/lab/{operacion}", json=cuerpo)
        assert r.status_code == 200, r.text
        d = r.json()
        return d["http"], d["respuesta"]

    def plantilla(self, tipo: str, ruta: Path) -> dict:
        """Imagen -> plantilla con la herramienta auxiliar del laboratorio."""
        with open(ruta, "rb") as f:
            r = self.panel.post("/panel/api/lab/extraer-plantilla", data={"tipo": tipo}, files={"archivo": (ruta.name, f)})
        assert r.status_code == 200, r.text
        return r.json()


@pytest.fixture(scope="session")
def sis():
    s = Sistema()
    try:
        assert s.panel.get("/panel/api/estado").json()["core"] == "ok", "El Core no responde: ¿está levantado el sistema?"
    except (httpx.HTTPError, KeyError) as e:
        pytest.exit(f"No se pudo contactar al sistema ({e}). Levante docker compose y cargue los datos de prueba.", returncode=2)
    return s


HUELLAS = RAIZ / "datos_prueba" / "huellas"
