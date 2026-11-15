"""Quién entra a qué: personal con el token de COREDB, Desembolso con su usuario de servicio y SOL con el suyo."""
import httpx
import pytest
from fastapi.testclient import TestClient

from EVALUACION.main import crear_app
from EVALUACION.tests.ayudas import TOKEN_SOL, aprobada, cabeceras, construir_contexto


@pytest.fixture
def casos(api):
    """Una evaluación aprobada; devuelve (id_evaluacion, id_aprobacion)."""
    d = aprobada(api)
    return d["idEvaluacion"], d["aprobacion"]["idAprobacion"]


def test_sin_token_o_con_uno_invalido(api):
    sin_token = api.get("/eva/v1/evaluaciones")
    assert sin_token.status_code == 401 and sin_token.json()["error"]["code"] == "TOKEN_REQUERIDO"
    invalido = api.get("/eva/v1/evaluaciones", headers=cabeceras("token-que-coredb-no-conoce"))
    assert invalido.status_code == 401 and invalido.json()["error"]["code"] == "SESION_INVALIDA"
    # El token de SOL no es una sesión de COREDB.
    assert api.get("/eva/v1/evaluaciones", headers=cabeceras(TOKEN_SOL)).status_code == 401


@pytest.mark.parametrize(("token", "lee", "evalua", "decide", "audita"), [
    ("tok-analista", True, True, True, False),
    ("tok-auditor", True, False, False, True),
    ("tok-admin", True, True, True, True),
    ("tok-operador", False, False, False, False),
    ("tok-desembolso", False, False, False, False),
])
def test_permisos_del_personal(api, casos, token, lee, evalua, decide, audita):
    id_evaluacion, id_aprobacion = casos
    esperado = lambda permitido: 200 if permitido else 403  # noqa: E731
    assert api.get("/eva/v1/evaluaciones", headers=cabeceras(token)).status_code == esperado(lee)
    assert api.get(f"/eva/v1/evaluaciones/{id_evaluacion}", headers=cabeceras(token)).status_code == esperado(lee)
    assert api.get("/eva/v1/historial", headers=cabeceras(token)).status_code == esperado(audita or decide)
    # Ya tiene situación registrada: quien puede evaluar recibe 409, quien no, 403.
    situacion = api.post(f"/eva/v1/evaluaciones/{id_evaluacion}/situacion-financiera", headers=cabeceras(token),
                         json={"ingresoMensual": "5000.00", "deudaMensual": "0.00", "riesgo": "BUENO",
                               "verificada": True, "version": 1})
    assert situacion.status_code == (409 if evalua else 403)
    revocar = api.post(f"/eva/v1/aprobaciones/{id_aprobacion}/revocacion", headers=cabeceras(token),
                       json={"motivo": "Prueba de permisos del rol.", "version": 99})
    assert revocar.status_code == (409 if decide else 403)


def test_cr_int_04_es_de_desembolso(api, casos):
    _, id_aprobacion = casos
    ruta = f"/eva/v1/aprobaciones/{id_aprobacion}"
    assert api.get(ruta, headers=cabeceras("tok-desembolso")).status_code == 200
    assert api.get(ruta, headers=cabeceras("tok-analista")).status_code == 200
    assert api.get(ruta, headers=cabeceras("tok-cobranza")).status_code == 403
    assert api.get(ruta, headers=cabeceras("tok-operador")).status_code == 403
    cuerpo = {"version": 1, "codigoOrden": "DES-2026-000001", "fechaDesembolso": "2026-01-01T10:00:00-05:00"}
    for token in ("tok-analista", "tok-admin", "tok-cobranza"):
        assert api.post(f"{ruta}/desembolso", json=cuerpo, headers=cabeceras(token)).status_code == 403


def test_si_coredb_no_responde(base_de_datos, root, sol):
    def caido(peticion: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("COREDB apagado", request=peticion)

    contexto = construir_contexto(base_de_datos, sol, coredb=caido)
    with TestClient(crear_app(contexto=contexto)) as api:
        r = api.get("/eva/v1/evaluaciones", headers=cabeceras("tok-analista"))
        assert r.status_code == 503 and r.json()["error"]["code"] == "COREDB_NO_DISPONIBLE"
        assert api.get("/salud").status_code == 200    # la salud no depende de COREDB


def test_la_correlacion_vuelve_en_la_respuesta(api):
    r = api.get("/eva/v1/evaluaciones", headers={**cabeceras("tok-analista"), "X-Correlation-ID": "traza-123"})
    assert r.headers["X-Correlation-ID"] == "traza-123"
    invalida = api.get("/salud", headers={"X-Correlation-ID": "con espacios no vale"})
    assert invalida.headers["X-Correlation-ID"] != "con espacios no vale"
