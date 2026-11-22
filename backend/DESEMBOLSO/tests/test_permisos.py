"""Quién entra a Desembolso: COREDB valida el token y Desembolso lo reenvía.

OPERADOR verifica el documento, prepara, valida y confirma; ADMINISTRADOR hace de supervisor
(decisión del equipo pendiente, T6) y además concilia; AUDITOR consulta y concilia.
"""
import uuid

import pytest

from DESEMBOLSO.tests.ayudas import (SERVICIO_SECRETO, SERVICIO_USUARIO, cabeceras, confirmar, login, orden_preparada,
                                     persona, preparar, verificar)

RUTAS_LECTURA = ["/api/v1/sesion", "/api/v1/ordenes", "/api/v1/conciliacion",
                 "/api/v1/aprobaciones?codCliente=C001", "/api/v1/clientes/C001/cuentas"]


def test_sin_token_o_con_token_invalido(api):
    for ruta in RUTAS_LECTURA:
        r = api.get(ruta)
        assert r.status_code == 401 and r.json()["error"]["code"] == "TOKEN_REQUERIDO", ruta
    r = api.get("/api/v1/ordenes", headers=cabeceras("token-que-no-firmo-coredb"))
    assert r.status_code == 401 and r.json()["error"]["code"] == "SESION_INVALIDA"


def test_el_usuario_de_servicio_no_entra_a_las_rutas_del_personal(api):
    token = login(SERVICIO_USUARIO, SERVICIO_SECRETO)
    for ruta in RUTAS_LECTURA:
        r = api.get(ruta, headers=cabeceras(token))
        assert r.status_code == 403 and r.json()["error"]["code"] == "PERMISO_DENEGADO", ruta


@pytest.mark.parametrize(("rol", "perfil", "opera", "concilia"), [
    ("OPERADOR", "OPERADOR", True, False),
    # El administrador no tiene VALIDAR_IDENTIDAD (la identidad la verifica un operador en ventanilla):
    # no puede completar un desembolso, así que la pantalla no le ofrece operar (prueba «solo mouse», B7).
    ("ADMINISTRADOR", "SUPERVISOR", False, True),
    ("AUDITOR", "AUDITOR", False, True),
])
def test_perfil_de_cada_rol(api, admin, rol, perfil, opera, concilia):
    token, username = persona(admin, rol)
    r = api.get("/api/v1/sesion", headers=cabeceras(token))
    assert r.status_code == 200, r.text
    sesion = r.json()
    assert (sesion["usuario"], sesion["rol"], sesion["perfil"]) == (username, rol, perfil)
    assert (sesion["puedeOperar"], sesion["puedeConciliar"]) == (opera, concilia)


def test_el_auditor_consulta_pero_no_opera(api, admin, operador):
    datos = orden_preparada(api, admin, operador[0])
    auditor, _ = persona(admin, "AUDITOR")
    id_orden = datos["orden"]["idOrden"]
    assert api.get(f"/api/v1/ordenes/{id_orden}", headers=cabeceras(auditor)).status_code == 200
    assert api.get("/api/v1/conciliacion", headers=cabeceras(auditor)).status_code == 200
    for r in (preparar(api, auditor, datos["idEvaluacion"], datos["numCuenta"]),
              confirmar(api, auditor, id_orden),
              verificar(api, auditor, datos["documento"]),
              api.get(f"/api/v1/clientes/{datos['codCliente']}/cuentas", headers=cabeceras(auditor)),
              api.post(f"/api/v1/ordenes/{id_orden}/rechazo", headers=cabeceras(auditor), json={"motivo": "No."})):
        assert r.status_code == 403 and r.json()["error"]["code"] == "PERMISO_DENEGADO", r.text


def test_un_rol_sin_creditos_no_entra(api, admin):
    """ASESOR ve créditos en COREDB, pero no desembolsa: ve la sesión sin poder operar."""
    token, _ = persona(admin, "ASESOR")
    sesion = api.get("/api/v1/sesion", headers=cabeceras(token)).json()
    assert sesion["puedeOperar"] is False and sesion["puedeConciliar"] is False
    r = api.post("/api/v1/ordenes", headers=cabeceras(token, **{"X-Idempotency-Key": str(uuid.uuid4())}),
                 json={"idEvaluacion": str(uuid.uuid4()), "numCuenta": "CTA-1"})
    assert r.status_code == 403


def test_cuerpos_estrictos_y_llave_obligatoria(api, operador):
    token = operador[0]
    cuerpo = {"idEvaluacion": str(uuid.uuid4()), "numCuenta": "CTA-1"}
    sin_llave = api.post("/api/v1/ordenes", headers=cabeceras(token), json=cuerpo)
    assert sin_llave.status_code == 422
    mala = api.post("/api/v1/ordenes", headers=cabeceras(token, **{"X-Idempotency-Key": "no-es-uuid"}), json=cuerpo)
    assert mala.status_code == 422
    extra = preparar(api, token, cuerpo["idEvaluacion"], "CTA-1", importe="99999.00")
    assert extra.status_code == 422
    r = api.post("/api/v1/identidad", headers=cabeceras(token),
                 json={"tipoDocumento": "DNI", "numeroDocumento": "12345678", "identidadVerificada": True, "x": 1})
    assert r.status_code == 422 and "12345678" not in r.text
