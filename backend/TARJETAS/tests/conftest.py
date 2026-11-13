import json
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from TARJETAS.core_client import CoreClient  # noqa: E402
from TARJETAS.dependencies import get_core_client  # noqa: E402
from TARJETAS.main import app  # noqa: E402


class CoreFalso:
    """Registra lo que Tarjetas le manda a COREDB y responde lo que se le configure."""

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
        if isinstance(self.respuesta, list):
            return self.respuesta.pop(0)
        return self.respuesta


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
