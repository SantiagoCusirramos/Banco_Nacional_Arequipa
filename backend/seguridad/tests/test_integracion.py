"""Seguridad contra COREDB y la base integrada reales, a través del Bus, como en el producto.

Las corre scripts/pruebas_integracion.sh, que levanta la base (con sus datos de desarrollo),
COREDB y el Bus en contenedores nuevos y crea el administrador y svc-seguridad con los scripts
de arranque de COREDB. Sin SEGURIDAD_TEST_COREDB se omiten.
"""
import os
import secrets
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

from seguridad.app import Contexto, crear_app
from seguridad.config import Config

COREDB = os.environ.get("SEGURIDAD_TEST_COREDB", "").strip()
BUS_TOKEN = os.environ.get("SEGURIDAD_TEST_BUS_TOKEN", "").strip()
BUS_TOKEN_PRUEBAS = os.environ.get("SEGURIDAD_TEST_BUS_TOKEN_PRUEBAS", "").strip()
ADMIN_PASSWORD = os.environ.get("SEGURIDAD_TEST_ADMIN_PASSWORD", "")
SERVICIO_SECRETO = os.environ.get("SEGURIDAD_TEST_SERVICIO_SECRETO", "")

pytestmark = pytest.mark.skipif(not COREDB, reason="Requiere scripts/pruebas_integracion.sh.")


def _coredb(metodo, ruta, token=None, **opciones):
    cabeceras = {"X-Bus-Token": BUS_TOKEN_PRUEBAS, **({"Authorization": f"Bearer {token}"} if token else {})}
    respuesta = httpx.request(metodo, COREDB + ruta, headers=cabeceras, timeout=10, **opciones)
    assert respuesta.is_success, f"{metodo} {ruta}: {respuesta.status_code} {respuesta.text}"
    return respuesta.json()


@pytest.fixture(scope="module")
def admin():
    return _coredb("POST", "/coredb/auth/login", json={"username": "admin", "password": ADMIN_PASSWORD})["access_token"]


@pytest.fixture(scope="module")
def persona(admin):
    def _persona(rol):
        username, clave = "u" + uuid.uuid4().hex[:12], "clave-de-una-persona-1"
        _coredb("POST", "/coredb/usuarios", admin, json={"username": username, "nombre": "N", "password": clave,
                                                         "rol": rol})
        return _coredb("POST", "/coredb/auth/login", json={"username": username, "password": clave})["access_token"]
    return _persona


@pytest.fixture
def cuenta(admin):
    sufijo = uuid.uuid4().int % 10**16
    return _coredb("POST", "/coredb/cuentas", admin, json={
        "num_cuenta": f"CTA-{sufijo:016d}", "cci": f"{sufijo:020d}", "moneda": "PEN", "regimen": "INDIVIDUAL",
        "id_agencia": "AQP01", "titulares": ["DEV001"]})["num_cuenta"]


@pytest.fixture
def api():
    config = Config(clave=secrets.token_hex(32), servicio_secreto=SERVICIO_SECRETO, coredb_url=COREDB,
                    bus_token=BUS_TOKEN, sellado_seg=0, sellado_antiguedad_seg=0)
    with TestClient(crear_app(contexto=Contexto.desde_config(config))) as cliente:
        yield cliente


def _h(token):
    return {"Authorization": f"Bearer {token}", "X-Correlation-ID": str(uuid.uuid4())}


def test_evaluacion_con_desafio(api, persona, cuenta):
    operador = persona("OPERADOR")
    operacion = {"uuid_operacion": str(uuid.uuid4()), "num_cuenta": cuenta, "canal": "ATM", "monto": "1300.00"}
    primera = api.post("/seguridad/operaciones/evaluar", json=operacion, headers=_h(operador))
    assert primera.status_code == 200, primera.text
    cuerpo = primera.json()
    assert (cuerpo["decision"], cuerpo["tope"], cuerpo["consumido"]) == ("DESAFIO_REQUERIDO", "1500.00", "0.00")
    con_codigo = {**operacion, "id_desafio": cuerpo["id_desafio"], "codigo": cuerpo["codigo_demo"]}
    otro = "000000" if cuerpo["codigo_demo"] != "000000" else "111111"
    mal = api.post("/seguridad/operaciones/evaluar", json={**con_codigo, "codigo": otro}, headers=_h(operador))
    assert mal.json()["decision"] == "DESAFIO_RECHAZADO"
    bien = api.post("/seguridad/operaciones/evaluar", json=con_codigo, headers=_h(operador)).json()
    assert bien["decision"] == "AUTORIZADA" and bien["repetida"] is False
    otra_vez = api.post("/seguridad/operaciones/evaluar", json=operacion, headers=_h(operador)).json()
    assert otra_vez["decision"] == "AUTORIZADA" and otra_vez["repetida"] is True
    tope = api.post("/seguridad/operaciones/evaluar", headers=_h(operador),
                    json={**operacion, "uuid_operacion": str(uuid.uuid4()), "monto": "1500.01"}).json()
    assert (tope["decision"], tope["motivo"]) == ("RECHAZADA", "TOPE")


def test_incidente_y_bitacora_sellada(api, persona):
    operador, auditor = persona("OPERADOR"), persona("AUDITOR")
    creado = api.post("/seguridad/incidentes", headers=_h(operador),
                      json={"prioridad": "P2", "titulo": "Intentos de acceso repetidos"})
    assert creado.status_code == 201, creado.text
    id_incidente = creado.json()["id_incidente"]
    for estado, extra in (("EN_PROGRESO", {}), ("RESUELTO", {"resolucion": "Se bloqueó el origen"}),
                          ("CERRADO", {})):
        r = api.patch(f"/seguridad/incidentes/{id_incidente}", headers=_h(operador), json={"estado": estado, **extra})
        assert r.status_code == 200, r.text
    assert r.json()["resolucion"] == "Se bloqueó el origen"
    assert id_incidente in [i["id_incidente"] for i in api.get("/seguridad/incidentes", headers=_h(auditor)).json()]

    eventos = api.get("/seguridad/auditoria", headers=_h(auditor)).json()
    assert any(e["id_entidad"] == id_incidente and e["accion"] == "INCIDENTE_CERRADO" for e in eventos)
    sellado = api.post("/seguridad/auditoria/sellos", headers=_h(auditor))
    assert sellado.status_code == 200 and sellado.json()["sellado"] is True, sellado.text
    verificacion = api.get("/seguridad/auditoria/verificar", headers=_h(auditor)).json()
    assert verificacion["valida"] is True and verificacion["sellos_verificados"] >= 1, verificacion


def test_desbloqueo_de_una_tarjeta(api, admin, persona, cuenta):
    tarjeta = _coredb("POST", "/coredb/tarjetas", admin, json={
        "pan_token": uuid.uuid4().hex, "bin": "004499", "ultimos4": "1234", "fecha_emision": "2026-01-01",
        "fecha_vencimiento": "2030-01-01", "cod_cliente": "DEV001", "num_cuenta": cuenta})["id_tarjeta"]
    for estado in ("ACTIVA", "BLOQUEADA"):
        _coredb("POST", f"/coredb/tarjetas/{tarjeta}/estado", admin, json={"estado": estado})
    asesor = persona("ASESOR")
    assert api.post(f"/seguridad/tarjetas/{tarjeta}/desbloqueo", headers=_h(asesor),
                    json={"motivo": "Sin permiso"}).status_code == 403
    operador = persona("OPERADOR")
    r = api.post(f"/seguridad/tarjetas/{tarjeta}/desbloqueo", headers=_h(operador),
                 json={"motivo": "El cliente confirmó su identidad"})
    assert r.status_code == 200, r.text
    assert r.json()["estado_tarjeta"] == "ACTIVA"
