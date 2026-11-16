"""CR-INT-01 con el adaptador real de Solicitud de Crédito.

SOL ya tiene el cliente HTTP que consulta a Captación (backend/SOL/integrations.py). Aquí
ese mismo código, sin cambios, le pide a CAPTACION la búsqueda y la referencia y aplica sus
propias reglas: campos, fechas, ACTIVO + HABILITADO y vigencia según la hora de Lima. Solo
la imagen de SOL tiene sus dependencias: en las demás estas pruebas se omiten.
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
from CAPTACION.tests.conftest import ASESOR, BASE, TOKEN_SOL  # noqa: E402


def _sol(token=TOKEN_SOL):
    """Las mismas rutas que SOL configuraría en SOL_CAP_*_PATH, contra CAPTACION."""
    ajustes = SimpleNamespace(
        mode="REAL", bus_base_url="http://captacion:8017", bus_token=token,
        cap_search_path="/cap/references", cap_reference_path="/cap/references/{idCliente}",
        http_timeout=0.6, max_retries=2, request_budget=2.4,
    )
    # El transporte de TestClient lleva las peticiones de SOL a la app de CAPTACION.
    return Integrations(ajustes, transport=TestClient(app)._transport)


def _habilitar(client, flujo, numero):
    id_caso = flujo.hasta_aprobado(numero)
    r = client.post(f"{BASE}/casos/{id_caso}/habilitar", headers=ASESOR)
    assert r.status_code == 200, r.text
    return id_caso, r.json()["data"]["cod_cliente"]


def test_sol_acepta_la_referencia_de_un_cliente_habilitado(client, flujo):
    id_caso, cod = _habilitar(client, flujo, "45679101")
    sol = _sol()
    referencia = sol.reference(cod, str(uuid4()))  # aplica validate_reference de SOL
    assert referencia["id_cliente"] == cod and referencia["id_caso"] == id_caso
    assert referencia["estado_habilitante"] == "HABILITADO"
    assert "celular" not in referencia  # SOL descarta todo lo que no está en CLIENT_FIELDS

    encontrados = sol.clients("45679101", str(uuid4()))
    assert [r["id_cliente"] for r in encontrados] == [cod]


def test_sol_rechaza_una_habilitacion_revocada(client, flujo):
    id_caso, cod = _habilitar(client, flujo, "45679102")
    client.post(f"{BASE}/casos/{id_caso}/estado", headers=ASESOR,
                json={"accion": "REVOCAR", "motivo": "Prueba de revocación"})
    with pytest.raises(HTTPException) as error:
        _sol().reference(cod, str(uuid4()))
    assert error.value.status_code == 422


def test_sol_trata_un_cliente_inexistente_como_rechazo_funcional(client):
    with pytest.raises(HTTPException) as error:
        _sol().reference("CLI000000999", str(uuid4()))
    assert error.value.status_code == 422


def test_con_otro_token_sol_ve_la_dependencia_caida(client, flujo):
    _, cod = _habilitar(client, flujo, "45679103")
    with pytest.raises(HTTPException) as error:
        _sol(token="x" * 40).reference(cod, str(uuid4()))
    assert error.value.status_code == 503
