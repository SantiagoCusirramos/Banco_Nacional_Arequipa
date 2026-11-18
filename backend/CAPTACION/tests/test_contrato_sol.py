"""CR-INT-01 con el adaptador real de Solicitud de Crédito.

SOL ya tiene el cliente HTTP que consulta a Captación (backend/SOL/integrations.py). Aquí
ese mismo código le pide a CAPTACION la búsqueda y la referencia y aplica sus
propias reglas: campos, fechas, ACTIVO + HABILITADO y vigencia según la hora de Lima. Solo
la imagen de SOL tiene sus dependencias: en las demás estas pruebas se omiten. CAPTACION
trabaja contra COREDB y la base integrada reales (scripts/pruebas_integracion.sh).
"""

from types import SimpleNamespace
from uuid import uuid4

import pytest

pytest.importorskip("SOL.integrations")
pytest.importorskip("tzdata")

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from SOL.integrations import Integrations  # noqa: E402

from CAPTACION.main import app  # noqa: E402
from CAPTACION.tests.conftest import BASE, TOKEN_SOL, dni  # noqa: E402


def _sol(token=TOKEN_SOL):
    """Las rutas de SOL (/cap/references/...) contra CAPTACION, sin el Bus en medio."""
    ajustes = SimpleNamespace(cap_url="http://captacion:8017", cap_token=token, bus_token="",
                              http_timeout=3.0, max_retries=1)
    # El transporte de TestClient lleva las peticiones de SOL a la app de CAPTACION.
    return Integrations(ajustes, transport=TestClient(app)._transport)


def _habilitar(flujo, numero):
    id_caso = flujo.hasta_aprobado(numero)
    return id_caso, flujo.habilitar(id_caso)["cod_cliente"]


def test_sol_acepta_la_referencia_de_un_cliente_habilitado(client, flujo):
    numero = dni()
    id_caso, cod = _habilitar(flujo, numero)
    sol = _sol()
    referencia = sol.reference(cod, str(uuid4()))  # aplica validate_reference de SOL
    assert referencia["id_cliente"] == cod and referencia["id_caso"] == id_caso
    assert referencia["estado_habilitante"] == "HABILITADO"
    assert "celular" not in referencia  # SOL descarta todo lo que no está en CLIENT_FIELDS

    encontrados = sol.clients(numero, str(uuid4()))
    assert [r["id_cliente"] for r in encontrados] == [cod]


def test_sol_rechaza_una_habilitacion_revocada(client, flujo, asesor):
    id_caso, cod = _habilitar(flujo, dni())
    client.post(f"{BASE}/casos/{id_caso}/estado", headers=asesor[0],
                json={"accion": "REVOCAR", "motivo": "Prueba de revocación"})
    with pytest.raises(HTTPException) as error:
        _sol().reference(cod, str(uuid4()))
    assert error.value.status_code == 422


def test_sol_trata_un_cliente_inexistente_como_rechazo_funcional(client):
    with pytest.raises(HTTPException) as error:
        _sol().reference("CLI000000999", str(uuid4()))
    assert error.value.status_code == 422


def test_con_otro_token_sol_ve_la_dependencia_caida(client, flujo):
    _, cod = _habilitar(flujo, dni())
    with pytest.raises(HTTPException) as error:
        _sol(token="x" * 40).reference(cod, str(uuid4()))
    assert error.value.status_code == 503
