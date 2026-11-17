"""Fase 2 del Bus: DESEMBOLSO llega a COREDB a través del Bus y presenta su credencial (X-Bus-Token)."""
import httpx
from fastapi.testclient import TestClient

from DESEMBOLSO.config import Config
from DESEMBOLSO.main import Contexto, crear_app

SECRETO = "s" * 40
TOKEN = "t" * 40


def _coredb(recibidas):
    def manejar(peticion):
        recibidas.append(peticion)
        ruta = peticion.url.path
        if ruta.endswith("/coredb/auth/login"):
            return httpx.Response(200, json={"access_token": "tok-servicio", "expires_in": 1800})
        if ruta.endswith("/coredb/auth/me"):
            return httpx.Response(200, json={"id_usuario": 1, "username": "u", "rol": "ADMINISTRADOR",
                                             "id_empleado": None, "permisos": []})
        return httpx.Response(200, json={"estado": "ok"})
    return manejar


def test_presenta_la_credencial_del_bus_en_cada_llamada():
    recibidas = []
    ctx = Contexto(Config(servicio_secreto=SECRETO, coredb_url="http://bus.test/bus/coredb", bus_token=TOKEN,
                          **({"envio_intervalo_seg": 0} if "DESEMBOLSO" == "EVALUACION" else {})),
                   transporte_coredb=httpx.MockTransport(_coredb(recibidas)))
    with TestClient(crear_app(contexto=ctx)) as api:
        api.get("/salud")
        ctx.coredb.como_persona("tok-persona", "GET", "/coredb/x")
        try:
            ctx.verificador.perfil("tok-persona")
        except Exception:  # noqa: BLE001 - solo interesa lo que salió hacia COREDB
            pass
    rutas = {p.url.path for p in recibidas}
    assert {"/bus/coredb/coredb/auth/login", "/bus/coredb/coredb/x", "/bus/coredb/coredb/auth/me"} <= rutas
    assert all(p.headers.get("x-bus-token") == TOKEN for p in recibidas)
    persona = next(p for p in recibidas if p.url.path.endswith("/coredb/x"))
    assert persona.headers["authorization"] == "Bearer tok-persona"


def test_sin_credencial_configurada_no_envia_la_cabecera():
    recibidas = []
    ctx = Contexto(Config(servicio_secreto=SECRETO, coredb_url="http://bus.test/bus/coredb",
                          **({"envio_intervalo_seg": 0} if "DESEMBOLSO" == "EVALUACION" else {})),
                   transporte_coredb=httpx.MockTransport(_coredb(recibidas)))
    ctx.coredb.como_persona("tok-persona", "GET", "/coredb/x")
    assert recibidas and "x-bus-token" not in recibidas[0].headers


def test_la_credencial_y_la_direccion_salen_del_entorno(monkeypatch):
    monkeypatch.setenv("DESEMBOLSO_COREDB_SECRETO", SECRETO)
    monkeypatch.setenv("BUS_TOKEN", TOKEN)
    monkeypatch.delenv("COREDB_URL", raising=False)
    config = Config.desde_entorno()
    assert config.bus_token == TOKEN
    assert config.coredb_url.endswith(":8018/bus/coredb")
