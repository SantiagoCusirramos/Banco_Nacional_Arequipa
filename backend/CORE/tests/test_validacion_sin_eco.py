"""El 422 de validación no devuelve los valores recibidos."""

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from CORE.api import montar_en
from CORE.dependencies import db_session, usuario_actual

SECRETO = "clave-que-no-debe-volver"


@pytest.fixture
def client():
    app = FastAPI()
    montar_en(app)
    app.dependency_overrides[db_session] = lambda: None
    app.dependency_overrides[usuario_actual] = lambda: SimpleNamespace(rol="ADMINISTRADOR", username="admin")
    return TestClient(app, raise_server_exceptions=False)


def post_crudo(client, cuerpo):
    return client.post(
        "/core/usuarios", content=cuerpo, headers={"content-type": "application/json"}
    )


def test_campo_faltante_no_devuelve_el_cuerpo(client):
    r = client.post("/core/usuarios", json={"username": "ana", "password": SECRETO})
    assert r.status_code == 422
    assert SECRETO not in r.text
    assert {"loc": ["body", "nombre"], "type": "missing", "msg": "missing"} in r.json()["detail"]


def test_valor_invalido_no_se_devuelve(client):
    r = client.post(
        "/core/usuarios",
        json={"username": "ana", "nombre": "A", "password": [SECRETO], "rol": "ASESOR"},
    )
    assert r.status_code == 422
    assert SECRETO not in r.text


def test_solo_ubicacion_y_tipo(client):
    r = client.post("/core/usuarios", json={})
    for error in r.json()["detail"]:
        assert set(error) == {"loc", "type", "msg"}
        assert error["msg"] == error["type"]


def test_surrogate_aislado_responde_422(client):
    r = post_crudo(
        client,
        '{"username":"ana","nombre":"A","password":"clave\\ud800segura","rol":"ASESOR"}',
    )
    assert r.status_code == 422
    assert r.json()["detail"][0]["loc"] == ["body", "password"]


def test_json_invalido_responde_422(client):
    r = post_crudo(client, '{"username":')
    assert r.status_code == 422
    assert r.json()["detail"][0]["type"] == "json_invalid"
