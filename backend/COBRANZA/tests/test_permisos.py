"""Quién entra a Cobranza: COREDB valida el token y Cobranza lo reenvía.

OPERADOR consulta y cobra; ADMINISTRADOR además registra mora, ejecuta vencimientos y concilia;
AUDITOR consulta y concilia; ANALISTA y ASESOR solo consultan. `svc-cobranza` no entra por las
rutas del personal: sus tareas diarias van directo a COREDB con su propio token.
"""
import uuid

import pytest

from COBRANZA.tests.ayudas import SERVICIO_SECRETO, SERVICIO_USUARIO, cabeceras, login, persona

RUTAS_LECTURA = ["/api/v1/sesion", "/api/v1/creditos?codCliente=C001", "/api/v1/creditos/CRE-1",
                 "/api/v1/creditos/CRE-1/pagos", "/api/v1/creditos/CRE-1/cuotas/1/mora",
                 "/api/v1/pagos/REF-1", "/api/v1/conciliacion", "/clientes/C001/creditos",
                 "/creditos/CRE-1/monto-a-pagar", "/pagos/REF-1/comprobante"]
CUERPO_PAGO = {"numCuenta": "CTA-1", "monto": "400.00", "referencia": "REF-1", "canal": "VEN"}
CUERPO_LEGACY = {"codCliente": "C001", "codCredito": "CRE-1", "montoPago": "400.00", "cuentaOrigen": "CTA-1",
                 "referenciaTransaccion": "REF-1", "idCanal": "HB"}
CUERPO_MORA = {"montoCalculado": "12.50"}


def test_sin_token_o_con_token_invalido(api):
    for ruta in RUTAS_LECTURA:
        r = api.get(ruta)
        assert r.status_code == 401 and r.json()["error"]["code"] == "TOKEN_REQUERIDO", ruta
    r = api.get("/api/v1/sesion", headers=cabeceras("token-que-no-firmo-coredb"))
    assert r.status_code == 401 and r.json()["error"]["code"] == "SESION_INVALIDA"


def test_el_usuario_de_servicio_no_entra_a_las_rutas_del_personal(api):
    token = login(SERVICIO_USUARIO, SERVICIO_SECRETO)
    for ruta in RUTAS_LECTURA:
        r = api.get(ruta, headers=cabeceras(token))
        assert r.status_code == 403 and r.json()["error"]["code"] == "PERMISO_DENEGADO", ruta
    operaciones = [
        api.post("/api/v1/creditos/CRE-1/pagos", headers=cabeceras(token), json=CUERPO_PAGO),
        api.post("/api/v1/creditos/CRE-1/cuotas/1/mora", headers=cabeceras(token), json=CUERPO_MORA),
        api.post("/api/v1/vencimientos", headers=cabeceras(token), json={}),
        api.post("/cr-int-08/pagos", headers=cabeceras(token), json=CUERPO_LEGACY),
    ]
    for r in operaciones:
        assert r.status_code == 403 and r.json()["error"]["code"] == "PERMISO_DENEGADO", r.text


@pytest.mark.parametrize(("rol", "perfil", "cobra", "mora", "concilia"), [
    ("OPERADOR", "OPERADOR", True, False, False),
    ("ADMINISTRADOR", "SUPERVISOR", True, True, True),
    ("AUDITOR", "AUDITOR", False, False, True),
    ("ANALISTA", "CONSULTA", False, False, False),
    ("ASESOR", "CONSULTA", False, False, False),
])
def test_perfil_de_cada_rol(api, admin, rol, perfil, cobra, mora, concilia):
    token, username = persona(admin, rol)
    r = api.get("/api/v1/sesion", headers=cabeceras(token))
    assert r.status_code == 200, r.text
    sesion = r.json()
    assert (sesion["usuario"], sesion["rol"], sesion["perfil"]) == (username, rol, perfil)
    assert (sesion["puedeCobrar"], sesion["puedeMora"], sesion["puedeConciliar"]) == (cobra, mora, concilia)


def test_el_asesor_consulta_pero_no_cobra(api, admin, credito):
    asesor, _ = persona(admin, "ASESOR")
    token = asesor
    assert api.get("/api/v1/creditos", params={"codCliente": credito["codCliente"]},
                   headers=cabeceras(token)).status_code == 200
    assert api.get(f"/api/v1/creditos/{credito['codCredito']}", headers=cabeceras(token)).status_code == 200
    for r in (api.post(f"/api/v1/creditos/{credito['codCredito']}/pagos", headers=cabeceras(token),
                       json={**CUERPO_PAGO, "numCuenta": credito["numCuenta"]}),
              api.post(f"/api/v1/creditos/{credito['codCredito']}/cuotas/1/mora", headers=cabeceras(token),
                       json=CUERPO_MORA),
              api.post("/api/v1/vencimientos", headers=cabeceras(token), json={}),
              api.get("/api/v1/conciliacion", headers=cabeceras(token))):
        assert r.status_code == 403 and r.json()["error"]["code"] == "PERMISO_DENEGADO", r.text


def test_el_auditor_consulta_y_concilia_pero_no_cobra(api, auditor, credito):
    token = auditor[0]
    assert api.get(f"/api/v1/creditos/{credito['codCredito']}", headers=cabeceras(token)).status_code == 200
    assert api.get("/api/v1/conciliacion", headers=cabeceras(token)).status_code == 200
    for r in (api.post(f"/api/v1/creditos/{credito['codCredito']}/pagos", headers=cabeceras(token),
                       json={**CUERPO_PAGO, "numCuenta": credito["numCuenta"], "referencia": str(uuid.uuid4())}),
              api.post(f"/api/v1/creditos/{credito['codCredito']}/cuotas/1/mora", headers=cabeceras(token),
                       json=CUERPO_MORA),
              api.post("/api/v1/vencimientos", headers=cabeceras(token), json={})):
        assert r.status_code == 403 and r.json()["error"]["code"] == "PERMISO_DENEGADO", r.text


def test_cuerpos_estrictos_y_referencia_valida(api, operador):
    token = operador[0]
    extra = api.post("/cr-int-08/pagos", headers=cabeceras(token), json={**CUERPO_LEGACY, "extra": 1})
    assert extra.status_code == 422
    incompleto = api.post("/cr-int-08/pagos", headers=cabeceras(token),
                          json={k: v for k, v in CUERPO_LEGACY.items() if k != "codCliente"})
    assert incompleto.status_code == 422
    nuevo_extra = api.post("/api/v1/creditos/CRE-1/pagos", headers=cabeceras(token),
                           json={**CUERPO_PAGO, "extra": 1})
    assert nuevo_extra.status_code == 422
    for referencia in ("con espacios", "", "x" * 41, "-empieza-mal"):
        r = api.post("/api/v1/creditos/CRE-1/pagos", headers=cabeceras(token),
                     json={**CUERPO_PAGO, "referencia": referencia})
        assert r.status_code == 422, referencia
