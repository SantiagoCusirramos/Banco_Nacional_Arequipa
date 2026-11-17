"""Pruebas de CAPTACION. Las de integración usan COREDB y la base integrada reales
(scripts/pruebas_integracion.sh, que crea el administrador y el usuario de servicio
svc-captacion con los scripts de arranque de COREDB); sin CAPTACION_TEST_COREDB se omiten.
Las de lógica (test_logica.py) corren siempre."""

import os
import secrets
import sys
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

COREDB = os.environ.get("CAPTACION_TEST_COREDB", "").strip()
# COREDB está detrás del Bus (fase 2): CAPTACION presenta su credencial y las pruebas, la suya.
BUS_TOKEN_PRUEBAS = os.environ.get("CAPTACION_TEST_BUS_TOKEN_PRUEBAS", "").strip()
ADMIN_USUARIO = os.environ.get("CAPTACION_TEST_ADMIN_USUARIO", "admin")
ADMIN_PASSWORD = os.environ.get("CAPTACION_TEST_ADMIN_PASSWORD", "")
TOKEN_SOL = "token-de-sol-para-pruebas-" + secrets.token_hex(16)

# Antes de importar CAPTACION: su configuración se lee al importarla.
os.environ.update({
    "CAP_OTP_CLAVE": "clave-otp-de-prueba",
    "CAP_OTP_SIMULADO": "true",
    "CAP_SOL_TOKEN": TOKEN_SOL,
    "CAP_CORE_USUARIO": os.environ.get("CAPTACION_TEST_SERVICIO_USUARIO", "svc-captacion"),
    "CAP_CORE_SECRETO": os.environ.get("CAPTACION_TEST_SERVICIO_SECRETO", ""),
    "CORE_BASE_URL": COREDB or "http://coredb.prueba",
    "BUS_TOKEN": os.environ.get("CAPTACION_TEST_BUS_TOKEN", ""),
})

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from CAPTACION.core_client import CoreDb  # noqa: E402
from CAPTACION.dependencies import get_core  # noqa: E402
from CAPTACION.main import app  # noqa: E402

SOL = {"Authorization": f"Bearer {TOKEN_SOL}"}
BASE = "/api/v1/captacion"
CLAVE = "clave-de-una-persona-1"


def coredb(metodo: str, ruta: str, token: str | None = None, esperado: int | None = None, **opciones):
    """COREDB real, por HTTP."""
    cabeceras = {"Authorization": f"Bearer {token}"} if token else {}
    if BUS_TOKEN_PRUEBAS:
        cabeceras["X-Bus-Token"] = BUS_TOKEN_PRUEBAS
    r = httpx.request(metodo, COREDB + ruta, headers=cabeceras, timeout=15, **opciones)
    if esperado is not None:
        assert r.status_code == esperado, f"{metodo} {ruta}: {r.status_code} {r.text}"
    return r


def dni(ultimo: str = "1") -> str:
    """Un DNI nuevo; el último dígito fija la calificación del simulador de centrales."""
    return "4" + "".join(secrets.choice("0123456789") for _ in range(6)) + ultimo


@pytest.fixture(scope="session")
def admin():
    if not COREDB:
        pytest.skip("Requiere CAPTACION_TEST_COREDB (scripts/pruebas_integracion.sh).")
    return coredb("POST", "/coredb/auth/login", esperado=200,
                  json={"username": ADMIN_USUARIO, "password": ADMIN_PASSWORD}).json()["access_token"]


@pytest.fixture(scope="session")
def persona(admin):
    """Crea un usuario con `rol` e inicia su sesión: (encabezados, username)."""
    def _persona(rol):
        username = rol.lower()[:2] + uuid.uuid4().hex[:12]
        coredb("POST", "/coredb/usuarios", admin, 201,
               json={"username": username, "nombre": f"{rol} de pruebas", "password": CLAVE, "rol": rol})
        token = coredb("POST", "/coredb/auth/login", esperado=200,
                       json={"username": username, "password": CLAVE}).json()["access_token"]
        return {"Authorization": f"Bearer {token}"}, username
    return _persona


@pytest.fixture(scope="session")
def asesor(persona):
    return persona("ASESOR")


@pytest.fixture
def client(admin):
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class Flujo:
    """Atajos para llevar un caso hasta cierto paso, con el token de un asesor."""

    def __init__(self, client, encabezados):
        self.c = client
        self.h = encabezados

    def solicitante(self, numero=None, tipo="DNI", correo=None, celular=None, materno="Ccori"):
        numero = numero or dni()
        r = self.c.post(f"{BASE}/solicitantes", headers=self.h, json={
            "tipo_documento": tipo, "numero_documento": numero, "nombres": "Rosa",
            "apellido_paterno": "Huamán", "apellido_materno": materno,
            "celular": celular or "9" + "".join(secrets.choice("0123456789") for _ in range(8)),
            "correo": correo or f"rosa.{numero.lower()}.{uuid.uuid4().hex[:6]}@example.com"})
        assert r.status_code in (200, 201), r.text
        return r.json()["data"]["solicitante"]

    def caso(self, sol):
        r = self.c.post(f"{BASE}/casos", headers=self.h, json={
            "id_solicitante": sol["id_solicitante"], "canal": "AGENCIA", "id_agencia": "AQP01",
            "producto_interes": "Crédito personal"})
        assert r.status_code == 201, r.text
        return r.json()["data"]["id_caso"]

    def consentir(self, id_caso, biometria=False):
        tipos = ["TRATAMIENTO_DATOS", "CONSULTA_BUROS", "TERMINOS"] + (["BIOMETRIA"] if biometria else [])
        r = self.c.post(f"{BASE}/casos/{id_caso}/consentimientos", headers=self.h,
                        json={"consentimientos": [{"tipo": t, "aceptado": True} for t in tipos]})
        assert r.status_code == 201, r.text

    def otp(self, id_caso, canal="SMS"):
        r = self.c.post(f"{BASE}/casos/{id_caso}/otp", headers=self.h, json={"canal": canal})
        assert r.status_code == 201, r.text
        codigo = r.json()["data"]["codigo_simulado"]
        r = self.c.post(f"{BASE}/casos/{id_caso}/otp/verificar", headers=self.h,
                        json={"canal": canal, "codigo": codigo})
        assert r.json()["data"]["verificado"] is True, r.text

    def validar(self, id_caso, tipos=("RENIEC", "LISTAS_NEGRAS", "PEP")):
        r = self.c.post(f"{BASE}/casos/{id_caso}/validaciones", headers=self.h, json={"tipos": list(tipos)})
        assert r.status_code == 201, r.text
        return r.json()["data"]

    def riesgo(self, id_caso):
        r = self.c.post(f"{BASE}/casos/{id_caso}/consultas-riesgo", headers=self.h, json={"central": "SBS"})
        assert r.status_code == 201, r.text
        r = self.c.post(f"{BASE}/casos/{id_caso}/perfil", headers=self.h)
        assert r.status_code == 201, r.text
        return r.json()["data"]

    def hasta_aprobado(self, numero=None, **kwargs):
        sol = self.solicitante(numero, **kwargs)
        id_caso = self.caso(sol)
        self.consentir(id_caso)
        self.otp(id_caso)
        self.validar(id_caso)
        self.riesgo(id_caso)
        return id_caso

    def ver(self, id_caso):
        r = self.c.get(f"{BASE}/casos/{id_caso}", headers=self.h)
        assert r.status_code == 200, r.text
        return r.json()["data"]

    def habilitar(self, id_caso):
        r = self.c.post(f"{BASE}/casos/{id_caso}/habilitar", headers=self.h)
        assert r.status_code == 200, r.text
        return r.json()["data"]


@pytest.fixture
def flujo(client, asesor):
    return Flujo(client, asesor[0])


@pytest.fixture
def coredb_caido(client):
    """CAPTACION con un COREDB que no responde."""
    core = CoreDb(base_url="http://127.0.0.1:9", timeout=0.5)
    app.dependency_overrides[get_core] = lambda: core
    yield
    app.dependency_overrides.clear()
    core.close()
