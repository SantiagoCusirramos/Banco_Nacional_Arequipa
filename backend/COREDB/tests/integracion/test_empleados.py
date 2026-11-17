"""Empleados: un administrador los registra y los liga a un usuario, contra la base real."""

import uuid

import pytest
from creditos_apoyo import BASE
from fastapi.testclient import TestClient

from COREDB.main import app

RUTA = "/coredb/empleados"
NOMBRE = "Lucía Analista de Pruebas"


@pytest.fixture
def api():
    return TestClient(app, raise_server_exceptions=False)


def codigo():
    return "E" + uuid.uuid4().hex[:10].upper()


def alta(api, encabezados, **datos):
    cuerpo = {"codigo_empleado": codigo(), "nombre_completo": NOMBRE, "cargo": "ANALISTA", **datos}
    return api.post(RUTA, json=cuerpo, headers=encabezados)


def test_registra_un_empleado_ligado_a_un_usuario_y_lo_audita(api, autorizacion, sesion_de, consulta):
    _, usuario = sesion_de("ANALISTA")
    propio = codigo().lower()
    respuesta = alta(api, autorizacion, codigo_empleado=f" {propio} ", id_agencia="AQP01",
                     id_usuario=usuario["id_usuario"], cargo="analista")
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo == {"id_empleado": cuerpo["id_empleado"], "codigo_empleado": propio, "cargo": "ANALISTA",
                      "id_agencia": "AQP01", "id_usuario": usuario["id_usuario"], "activo": True}
    assert NOMBRE not in respuesta.text
    ligado = api.get(f"/coredb/usuarios/{usuario['id_usuario']}", headers=autorizacion).json()
    assert ligado["id_empleado"] == cuerpo["id_empleado"]
    eventos = consulta("SELECT actor, detalle FROM core.evento_auditoria WHERE accion = 'REGISTRAR_EMPLEADO' "
                       "AND id_entidad = %s", cuerpo["id_empleado"])
    assert len(eventos) == 1 and eventos[0]["actor"] == "pruebas"
    assert "Lucía" not in eventos[0]["detalle"]


def test_sin_usuario_y_sin_agencia(api, autorizacion, consulta):
    respuesta = alta(api, autorizacion)
    assert respuesta.status_code == 201, respuesta.text
    assert (respuesta.json()["id_usuario"], respuesta.json()["id_agencia"]) == (None, None)
    fila = consulta("SELECT nombre_completo, activo FROM core.empleado WHERE id_empleado = UUID_TO_BIN(%s)",
                    respuesta.json()["id_empleado"])
    assert fila == [{"nombre_completo": NOMBRE, "activo": 1}]


def test_el_empleado_registrado_queda_disponible_como_analista(api, autorizacion, sesion_de):
    """Lo que antes necesitaba al administrador de la base: empleado, usuario ligado, analista."""
    encabezados, usuario = sesion_de("ANALISTA")
    id_empleado = alta(api, autorizacion, id_usuario=usuario["id_usuario"]).json()["id_empleado"]
    registrado = api.post(f"{BASE}/analistas", json={"idEmpleado": id_empleado}, headers=autorizacion)
    assert registrado.status_code == 201, registrado.text
    assert registrado.json()["idAnalista"].startswith("AN")


def test_codigo_repetido(api, autorizacion):
    primero = alta(api, autorizacion)
    repetido = alta(api, autorizacion, codigo_empleado=primero.json()["codigo_empleado"])
    assert repetido.status_code == 409
    assert repetido.json()["error"]["code"] == "EMPLEADO_DUPLICADO"
    assert primero.json()["codigo_empleado"] not in repetido.text


def test_usuario_ya_ligado_o_de_servicio(api, autorizacion, sesion_de):
    _, usuario = sesion_de("ANALISTA")
    assert alta(api, autorizacion, id_usuario=usuario["id_usuario"]).status_code == 201
    otra = alta(api, autorizacion, id_usuario=usuario["id_usuario"])
    assert otra.status_code == 409
    assert otra.json()["error"]["code"] == "USUARIO_NO_ADMITIDO"
    servicio = api.post("/coredb/usuarios/servicios", headers=autorizacion, json={
        "modulo": "CLIENTES", "username": "s" + uuid.uuid4().hex[:12], "nombre": "Servicio"})
    assert servicio.status_code == 201, servicio.text
    de_servicio = alta(api, autorizacion, id_usuario=servicio.json()["usuario"]["id_usuario"])
    assert de_servicio.status_code == 409
    assert de_servicio.json()["error"]["code"] == "USUARIO_NO_ADMITIDO"


def test_usuario_o_agencia_inexistentes(api, autorizacion):
    sin_usuario = alta(api, autorizacion, id_usuario=str(uuid.uuid4()))
    assert sin_usuario.status_code == 404
    assert sin_usuario.json()["error"]["code"] == "USUARIO_NO_ENCONTRADO"
    sin_agencia = alta(api, autorizacion, id_agencia="NOEXISTE")
    assert sin_agencia.status_code == 422
    assert sin_agencia.json()["error"]["code"] == "AGENCIA_NO_ENCONTRADA"
    assert "NOEXISTE" not in sin_agencia.text


@pytest.mark.parametrize("cambio", [
    {"nombre_completo": "   "}, {"codigo_empleado": ""}, {"cargo": "x" * 31}, {"codigo_empleado": "x" * 21},
    {"otro": 1},
])
def test_datos_invalidos(api, autorizacion, cambio):
    respuesta = alta(api, autorizacion, **cambio)
    assert respuesta.status_code == 422, respuesta.text


@pytest.mark.parametrize("rol", ["ANALISTA", "ASESOR", "AUDITOR", "OPERADOR"])
def test_solo_el_administrador_registra_empleados(api, sesion_de, rol):
    encabezados, _ = sesion_de(rol)
    respuesta = alta(api, encabezados)
    assert respuesta.status_code == 403
    assert respuesta.json()["error"]["code"] == "PERMISO_DENEGADO"


def test_sin_token(api):
    assert alta(api, {}).status_code == 401


def test_reintenta_un_deadlock(api, autorizacion, fallar_una_vez):
    from COREDB.services import empleados

    intentos = fallar_una_vez(empleados, 1213)
    assert alta(api, autorizacion).status_code == 201
    assert intentos == ["core.registrar_empleado", "core.registrar_empleado"]
