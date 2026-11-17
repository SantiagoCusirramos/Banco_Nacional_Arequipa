
from fastapi.testclient import TestClient

from app.main import app

from app.config import BUS_TOKEN, BUS_CORE_TOKEN
from app import integration
import httpx

client = TestClient(app)


def test_estado_del_bus():
    respuesta = client.get("/health")

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "operativo"


def test_rechaza_solicitud_sin_clave():
    respuesta = client.get("/api/billetera/salud")

    assert respuesta.status_code == 401


def test_rechaza_modulo_desconocido():
    respuesta = client.get(
        "/api/modulo-inexistente/123",
        headers={
            "X-API-Key": "bna-clave-local-cambiar"
        },
    )

    assert respuesta.status_code == 404

def test_clientes_rechaza_solicitud_sin_token():
    respuesta = client.post("/bus/clientes/registrar")

    assert respuesta.status_code == 401


def test_core_rechaza_solicitud_sin_token():
    respuesta = client.get("/bus/core/solicitudes-registro")

    assert respuesta.status_code == 401


def test_core_rechaza_bus_token():
    respuesta = client.get(
        "/bus/core/solicitudes-registro",
        headers={"X-Service-Token": BUS_TOKEN},
    )

    assert respuesta.status_code == 401


def test_core_acepta_bus_core_token(monkeypatch):
    class ClienteFalso:
        async def request(self, **kwargs):
            return httpx.Response(
                200,
                json={"correcto": True},
            )

    monkeypatch.setattr(
        integration,
        "cliente_http",
        ClienteFalso(),
    )

    respuesta = client.get(
        "/bus/core/solicitudes-registro",
        headers={"X-Service-Token": BUS_CORE_TOKEN},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["correcto"] is True


def test_cuentas_rechaza_solicitud_sin_token():
    respuesta = client.post("/bus/cuentas/apertura")
    assert respuesta.status_code == 401


def test_cuentas_reenvia_encabezados_bancarios(monkeypatch):
    class ClienteFalso:
        async def request(self, **kwargs):
            self.kwargs = kwargs
            return httpx.Response(
                201,
                json={"correcto": True},
            )

    falso = ClienteFalso()
    monkeypatch.setattr(integration, "cliente_http", falso)

    respuesta = client.post(
        "/bus/cuentas/deposito",
        headers={
            "X-Service-Token": BUS_TOKEN,
            "Authorization": "Bearer jwt-de-prueba",
            "X-Idempotency-Key": "123e4567-e89b-42d3-a456-426614174000",
            "X-Channel-ID": "WEB",
            "X-Request-Timestamp": "2026-11-16T01:30:00-05:00",
            "X-Correlation-ID": "prueba-cuentas-001",
        },
        json={"importe": 100},
    )

    assert respuesta.status_code == 201
    assert falso.kwargs["url"].endswith("/api/v1/cuentas/deposito")

    cabeceras = falso.kwargs["headers"]
    assert cabeceras["Authorization"] == "Bearer jwt-de-prueba"
    assert cabeceras["X-Idempotency-Key"] == "123e4567-e89b-42d3-a456-426614174000"
    assert cabeceras["X-Channel-ID"] == "WEB"
    assert cabeceras["X-Request-Timestamp"] == "2026-11-16T01:30:00-05:00"
    assert cabeceras["X-Correlation-ID"] == "prueba-cuentas-001"
