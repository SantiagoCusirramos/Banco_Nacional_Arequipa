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