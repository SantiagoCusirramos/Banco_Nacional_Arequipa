"""Sin COREDB ni base: configuración, cliente de COREDB, elegibilidad de cuentas y salud."""
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from DESEMBOLSO.comun import ErrorDes
from DESEMBOLSO.config import Config
from DESEMBOLSO.coredb import ClienteCoreDb
from DESEMBOLSO.main import Contexto, crear_app, elegibilidad, perfil_de

SECRETO = "s" * 40
RAIZ = Path(__file__).resolve().parents[1]


def test_la_configuracion_exige_el_secreto_del_servicio_y_no_tiene_base():
    with pytest.raises(RuntimeError, match="DESEMBOLSO_COREDB_SECRETO"):
        Config(servicio_secreto="corto").validar()
    Config(servicio_secreto=SECRETO).validar()
    assert not any("database" in campo or "cobranza" in campo or "evaluacion" in campo
                   for campo in Config.__dataclass_fields__)


def test_sin_base_propia_ni_llamadas_a_otros_modulos():
    """Desembolso solo habla con COREDB: no queda su base, ni Evaluación, CUENTAS o Cobranza."""
    for sobrante in ("sql", "persistencia", "integraciones", "servicios", "esquema.py", "scripts/preparar_base.py",
                     "scripts/preparar_servicio.py"):
        assert not (RAIZ / sobrante).exists(), sobrante
    codigo = "\n".join(p.read_text(encoding="utf-8") for p in RAIZ.glob("*.py"))
    for otro in ("/eva/", "/api/v1/cuentas", "cr-int-06", "sqlalchemy", "X-API-Key"):
        assert otro not in codigo, otro


def test_perfiles_por_rol():
    assert perfil_de("OPERADOR") == "OPERADOR"
    assert perfil_de("ADMINISTRADOR") == "SUPERVISOR"   # T6: el supervisor es ADMINISTRADOR
    assert perfil_de("AUDITOR") == "AUDITOR"
    assert perfil_de("ANALISTA") == "CONSULTA"


def _cuenta(**cambios):
    datos = {"num_cuenta": "CTA-1", "moneda": "PEN", "regimen": "INDIVIDUAL", "estado_cuenta": "ACTIVA",
             "titulares": ["C001"]}
    return {**datos, **cambios}


def test_elegibilidad_de_las_cuentas():
    assert elegibilidad(_cuenta(), "C001", "PEN") == (True, None)
    assert elegibilidad(_cuenta(regimen="MANCOMUNADA_INDISTINTA", titulares=["C001", "C002"]), "C001", "PEN") == (
        False, "CUENTA_MANCOMUNADA")
    assert elegibilidad(_cuenta(estado_cuenta="BLOQUEADA"), "C001", "PEN") == (False, "CUENTA_NO_ACTIVA")
    assert elegibilidad(_cuenta(moneda="USD"), "C001", "PEN") == (False, "MONEDA_DISTINTA")
    assert elegibilidad(_cuenta(moneda="USD"), "C001", None) == (True, None)
    assert elegibilidad(_cuenta(titulares=["C002"]), "C001", "PEN") == (False, "TITULAR_DISTINTO")


def _coredb_falso(registro, *, login=200, ruta=200):
    def manejar(peticion):
        registro.append(peticion)
        if peticion.url.path == "/coredb/auth/login":
            if login != 200:
                return httpx.Response(login, json={"error": {"code": "CREDENCIALES_INVALIDAS", "message": "x"}})
            return httpx.Response(200, json={"access_token": f"tok-{len(registro)}", "expires_in": 1800})
        if ruta == 401:
            return httpx.Response(401, json={"error": {"code": "TOKEN_EXPIRADO", "message": "x"}})
        if ruta == 404:
            return httpx.Response(404, json={"error": {"code": "ORDEN_NO_ENCONTRADA", "message": "No existe."}})
        if ruta == 500:
            return httpx.Response(500, text="falla")
        if ruta == 422:
            return httpx.Response(422, json={"detail": [{"loc": ["body", "x"], "msg": "x"}]})
        return httpx.Response(ruta, json={"ok": True})
    return manejar


def test_el_token_del_servicio_se_recuerda_y_se_renueva_si_coredb_lo_rechaza():
    registro = []
    cliente = ClienteCoreDb("http://coredb", "svc-desembolso", SECRETO,
                            transporte=httpx.MockTransport(_coredb_falso(registro)))
    assert cliente.como_servicio("GET", "/coredb/x") == (200, {"ok": True})
    assert cliente.como_servicio("GET", "/coredb/x") == (200, {"ok": True})
    assert [p.url.path for p in registro].count("/coredb/auth/login") == 1
    assert json.loads(registro[0].content) == {"username": "svc-desembolso", "password": SECRETO}
    registro.clear()
    cliente = ClienteCoreDb("http://coredb", "svc", SECRETO,
                            transporte=httpx.MockTransport(_coredb_falso(registro, ruta=401)))
    with pytest.raises(ErrorDes) as e:
        cliente.como_servicio("GET", "/coredb/x")
    assert e.value.estado == 401
    assert [p.url.path for p in registro] == ["/coredb/auth/login", "/coredb/x", "/coredb/auth/login", "/coredb/x"]


def test_errores_de_coredb():
    def cliente(**kw):
        return ClienteCoreDb("http://coredb", "svc", SECRETO, transporte=httpx.MockTransport(_coredb_falso([], **kw)))
    with pytest.raises(ErrorDes) as e:
        cliente(ruta=404).como_persona("tok", "GET", "/coredb/x")
    assert (e.value.estado, e.value.codigo, e.value.mensaje) == (404, "ORDEN_NO_ENCONTRADA", "No existe.")
    with pytest.raises(ErrorDes) as e:
        cliente(ruta=500).como_persona("tok", "GET", "/coredb/x")
    assert (e.value.estado, e.value.codigo) == (503, "COREDB_NO_DISPONIBLE")
    with pytest.raises(ErrorDes) as e:
        cliente(ruta=422).como_persona("tok", "GET", "/coredb/x")
    assert (e.value.estado, e.value.codigo) == (422, "DATOS_RECHAZADOS_POR_COREDB")
    with pytest.raises(ErrorDes) as e:
        cliente(login=401).token_servicio()
    assert e.value.codigo == "SERVICIO_SIN_SESION" and SECRETO not in e.value.mensaje

    def caido(peticion):
        raise httpx.ConnectError("caído", request=peticion)
    sin_red = ClienteCoreDb("http://coredb", "svc", SECRETO, transporte=httpx.MockTransport(caido))
    with pytest.raises(ErrorDes) as e:
        sin_red.como_persona("tok", "GET", "/coredb/x")
    assert e.value.codigo == "COREDB_NO_DISPONIBLE"


def test_salud_falla_si_el_servicio_no_inicia_sesion():
    def coredb(peticion):
        if peticion.url.path == "/coredb/salud":
            return httpx.Response(200, json={"estado": "ok"})
        return httpx.Response(401, json={"error": {"code": "CREDENCIALES_INVALIDAS", "message": "x"}})
    ctx = Contexto(Config(servicio_secreto=SECRETO), transporte_coredb=httpx.MockTransport(coredb))
    with TestClient(crear_app(contexto=ctx)) as api:
        r = api.get("/salud")
        assert r.status_code == 503 and r.json()["error"]["code"] == "SERVICIO_SIN_SESION"


def test_spec_publicada_al_dia():
    publicada = json.loads((RAIZ / "openapi.json").read_text(encoding="utf-8"))
    assert publicada == crear_app().openapi(), "Regenerar con: python -m DESEMBOLSO.scripts.exporta_openapi"
