import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# Antes de importar CAPTACION: su configuración se lee al importarla.
os.environ.update({
    "CAP_DB_URL": "sqlite://",
    "CAP_OTP_CLAVE": "clave-otp-de-prueba",
    "CAP_OTP_SIMULADO": "true",
    "CAP_SOL_TOKEN": "token-de-sol-para-pruebas-0123456789abcdef",
    "CAP_CORE_SECRETO": "secreto-de-prueba",
    "CAP_CORE_USUARIO": "svc-captacion",
    "CORE_BASE_URL": "http://coredb.prueba",
})

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from CAPTACION import database  # noqa: E402
from CAPTACION.core_client import CoreDb  # noqa: E402
from CAPTACION.dependencies import get_core  # noqa: E402
from CAPTACION.main import app  # noqa: E402
from CAPTACION.tests.coredb_falso import CoreDbFalso  # noqa: E402

TOKEN_SOL = os.environ["CAP_SOL_TOKEN"]
ASESOR = {"Authorization": "Bearer tok-asesor"}
AUDITOR = {"Authorization": "Bearer tok-auditor"}
SOL = {"Authorization": f"Bearer {TOKEN_SOL}"}
BASE = "/api/v1/captacion"


@pytest.fixture
def coredb_falso():
    return CoreDbFalso()


@pytest.fixture
def client(coredb_falso):
    # SQLite en memoria; CAP_TEST_DB_URL=mysql+pymysql://... corre lo mismo contra MySQL.
    engine = database.configurar(os.environ.get("CAP_TEST_DB_URL", "sqlite://"))
    database.Base.metadata.drop_all(engine)
    database.crear_tablas()
    core = CoreDb(base_url="http://coredb.prueba", transport=httpx.MockTransport(coredb_falso))
    app.dependency_overrides[get_core] = lambda: core
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    core.close()


class Flujo:
    """Atajos para llevar un caso hasta cierto paso."""

    def __init__(self, client):
        self.c = client

    def solicitante(self, numero="45678901", tipo="DNI", correo=None, celular="958111222", materno="Ccori"):
        r = self.c.post(f"{BASE}/solicitantes", headers=ASESOR, json={
            "tipo_documento": tipo, "numero_documento": numero, "nombres": "Rosa",
            "apellido_paterno": "Huamán", "apellido_materno": materno, "celular": celular,
            "correo": correo or f"rosa.{numero.lower()}@example.com"})
        assert r.status_code in (200, 201), r.text
        return r.json()["data"]["solicitante"]

    def caso(self, sol):
        r = self.c.post(f"{BASE}/casos", headers=ASESOR, json={
            "id_solicitante": sol["id_solicitante"], "canal": "AGENCIA", "id_agencia": "AQP01",
            "producto_interes": "Crédito personal"})
        assert r.status_code == 201, r.text
        return r.json()["data"]["id_caso"]

    def consentir(self, id_caso, biometria=False):
        tipos = ["TRATAMIENTO_DATOS", "CONSULTA_BUROS", "TERMINOS"] + (["BIOMETRIA"] if biometria else [])
        r = self.c.post(f"{BASE}/casos/{id_caso}/consentimientos", headers=ASESOR,
                        json={"consentimientos": [{"tipo": t, "aceptado": True} for t in tipos]})
        assert r.status_code == 201, r.text

    def otp(self, id_caso, canal="SMS"):
        r = self.c.post(f"{BASE}/casos/{id_caso}/otp", headers=ASESOR, json={"canal": canal})
        assert r.status_code == 201, r.text
        codigo = r.json()["data"]["codigo_simulado"]
        r = self.c.post(f"{BASE}/casos/{id_caso}/otp/verificar", headers=ASESOR,
                        json={"canal": canal, "codigo": codigo})
        assert r.json()["data"]["verificado"] is True, r.text

    def validar(self, id_caso, tipos=("RENIEC", "LISTAS_NEGRAS", "PEP")):
        r = self.c.post(f"{BASE}/casos/{id_caso}/validaciones", headers=ASESOR, json={"tipos": list(tipos)})
        assert r.status_code == 201, r.text
        return r.json()["data"]

    def riesgo(self, id_caso):
        r = self.c.post(f"{BASE}/casos/{id_caso}/consultas-riesgo", headers=ASESOR, json={"central": "SBS"})
        assert r.status_code == 201, r.text
        r = self.c.post(f"{BASE}/casos/{id_caso}/perfil", headers=ASESOR)
        assert r.status_code == 201, r.text
        return r.json()["data"]

    def hasta_aprobado(self, numero="45678901", **kwargs):
        sol = self.solicitante(numero, **kwargs)
        id_caso = self.caso(sol)
        self.consentir(id_caso)
        self.otp(id_caso)
        self.validar(id_caso)
        self.riesgo(id_caso)
        return id_caso

    def ver(self, id_caso):
        r = self.c.get(f"{BASE}/casos/{id_caso}", headers=ASESOR)
        assert r.status_code == 200, r.text
        return r.json()["data"]


@pytest.fixture
def flujo(client):
    return Flujo(client)
