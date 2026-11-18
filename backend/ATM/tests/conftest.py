import json
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from ATM.core_client import CoreClient  # noqa: E402
from ATM.dependencies import get_core_client  # noqa: E402
from ATM.main import app  # noqa: E402


class CoreFalso:
    """Registra lo que ATM le manda a TARJETAS/CUENTAS por el Bus y responde lo que se le configure."""

    def __init__(self):
        self.llamadas = []
        self.respuesta = httpx.Response(200, json={})
        self.excepcion = None

    def __call__(self, request: httpx.Request) -> httpx.Response:
        cuerpo = json.loads(request.content) if request.content else None
        self.llamadas.append({
            "metodo": request.method,
            "ruta": request.url.path,
            "query": dict(request.url.params),
            "headers": dict(request.headers),
            "json": cuerpo,
        })
        if self.excepcion:
            raise self.excepcion
        # Una lista da una respuesta por llamada, en orden.
        respuesta = self.respuesta.pop(0) if isinstance(self.respuesta, list) else self.respuesta
        return self.con_sobre(respuesta)

    @staticmethod
    def con_sobre(respuesta: httpx.Response) -> httpx.Response:
        """TARJETAS y CUENTAS envuelven cada respuesta correcta en {success, data, metadata}."""
        if respuesta.status_code >= 400 or not respuesta.content:
            return respuesta
        datos = respuesta.json()
        if isinstance(datos, dict) and "success" in datos:
            return respuesta
        return httpx.Response(respuesta.status_code, json={
            "success": True, "status_code": respuesta.status_code, "message": "ok",
            "data": datos, "metadata": {"modulo_emisor": "PRUEBA"},
        })


@pytest.fixture
def core():
    falso = CoreFalso()
    app.dependency_overrides[get_core_client] = lambda: CoreClient(
        base_url="http://core.test", transport=httpx.MockTransport(falso)
    )
    yield falso
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)

ID_TARJETA_PRUEBA = "7e570001-0000-4000-8000-000000000001"
UUID_AUT_PRUEBA = "5a1f0c3e-0000-4000-8000-000000000001"


@pytest.fixture
def sesion(client, core):
    """Cabecera X-ATM-Sesion de una tarjeta con el PIN ya validado (K-3: sin PIN no hay retiro)."""
    core.respuesta = httpx.Response(200, json={"resultado": "EXITOSO", "intentos_restantes": 3})
    r = client.post("/api/validar-pin", json={"id_tarjeta": ID_TARJETA_PRUEBA, "pin": "4821",
                                              "id_terminal": "ATM-AQP-001"},
                    headers={"Authorization": "Bearer token-de-prueba"})
    assert r.status_code == 200, r.text
    core.llamadas.clear()
    return {"X-ATM-Sesion": r.json()["data"]["token_sesion"]}


@pytest.fixture
def autorizada(client, core, sesion):
    """Sesión que ya autorizó UUID_AUT_PRUEBA: solo ella puede confirmarla o extornarla."""
    core.respuesta = httpx.Response(201, json={
        "uuid_autorizacion": UUID_AUT_PRUEBA, "id_tarjeta": ID_TARJETA_PRUEBA, "num_cuenta": "10100000000001",
        "id_canal": None, "id_terminal": "ATM-AQP-001", "tipo_operacion": "RETIRO", "monto": "150.00",
        "estado_autorizacion": "AUTORIZADA", "codigo_respuesta": "00", "motivo_rechazo": None})
    r = client.post("/api/autorizar", json={
        "id_tarjeta": ID_TARJETA_PRUEBA, "num_cuenta": "10100000000001", "moneda": "PEN", "monto": "150.00",
        "id_terminal": "ATM-AQP-001", "uuid_transaccion": "5a1f0c3e-0000-4000-8000-0000000000ff"},
        headers={"Authorization": "Bearer token-de-prueba", "X-Idempotency-Key": "550e8400-e29b-41d4-a716-4466554400ff",
                 **sesion})
    assert r.status_code == 201, r.text
    core.llamadas.clear()
    return sesion
