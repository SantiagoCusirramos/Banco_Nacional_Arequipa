"""Un valor que MySQL rechaza (ENUM, clave foránea, CHECK) responde 422, no 500 (issue #66)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, OperationalError

from CORE.api import montar_en

VALOR = "valor-que-no-debe-volver"


def cliente(error):
    app = FastAPI()
    montar_en(app)

    @app.get("/falla")
    def falla():
        raise error

    return TestClient(app, raise_server_exceptions=False)


def de_mysql(clase, codigo):
    return clase("INSERT ...", {"v": VALOR}, Exception(codigo, f"rechazado: '{VALOR}'"))


@pytest.mark.parametrize("codigo", [1265, 1452, 3819, 1048, 1406])
def test_error_de_datos_responde_422_sin_el_valor(codigo):
    r = cliente(de_mysql(IntegrityError, codigo)).get("/falla", headers={"x-correlation-id": "c-1"})
    assert r.status_code == 422
    assert r.json() == {
        "error": {"code": "DATOS_INVALIDOS", "message": "Los datos no cumplen las reglas de la base.",
                  "details": {}},
        "correlation_id": "c-1",
    }
    assert VALOR not in r.text


def test_otro_error_de_la_base_sigue_siendo_500():
    r = cliente(de_mysql(OperationalError, 2003)).get("/falla")
    assert r.status_code == 500
    assert VALOR not in r.text
