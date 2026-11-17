"""Fase 2 del Bus: CAPTACION llega a COREDB a través del Bus y presenta su credencial (X-Bus-Token)."""
import httpx

from CAPTACION.config import Settings
from CAPTACION.core_client import CoreDb

TOKEN = "t" * 40


def _core(recibidas, **kw):
    def manejador(peticion):
        recibidas.append(peticion)
        if peticion.url.path.endswith("/coredb/auth/login"):
            return httpx.Response(200, json={"access_token": "tok-servicio", "expires_in": 1800})
        return httpx.Response(200, json={"ok": True, "estado": "ok"})
    return CoreDb(base_url="http://bus.test/bus/coredb", transport=httpx.MockTransport(manejador), **kw)


def test_presenta_la_credencial_del_bus_en_cada_llamada():
    recibidas = []
    core = _core(recibidas, bus_token=TOKEN)
    core.persona("GET", "/coredb/x", "persona", "corr-1")
    core.servicio("GET", "/coredb/y", None)
    core.salud()
    assert recibidas and all(p.headers.get("x-bus-token") == TOKEN for p in recibidas)
    primera = next(p for p in recibidas if p.url.path.endswith("/coredb/x"))
    assert primera.headers["authorization"] == "Bearer persona"
    assert primera.headers["x-correlation-id"] == "corr-1"


def test_sin_credencial_configurada_no_envia_la_cabecera():
    recibidas = []
    _core(recibidas, bus_token="").persona("GET", "/coredb/x", "persona", None)
    assert "x-bus-token" not in recibidas[0].headers


def test_la_credencial_sale_de_bus_token(monkeypatch):
    monkeypatch.setenv("BUS_TOKEN", TOKEN)
    assert Settings().bus_token == TOKEN


def test_por_omision_apunta_al_bus(monkeypatch):
    monkeypatch.delenv("CORE_BASE_URL", raising=False)
    assert Settings().core_base_url.endswith(":8018/bus/coredb")
