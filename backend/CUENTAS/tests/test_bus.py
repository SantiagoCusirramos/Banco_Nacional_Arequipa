"""Fase 2 del Bus: CUENTAS llega a COREDB a través del Bus y presenta su credencial (X-Bus-Token)."""
import httpx

from CUENTAS.config import Settings, settings
from CUENTAS.core_client import CoreClient

TOKEN = "t" * 40


def _cliente(recibidas, **kw):
    def manejador(peticion):
        recibidas.append(peticion)
        return httpx.Response(200, json={"ok": True})
    return CoreClient(base_url="http://bus.test/bus/coredb", transport=httpx.MockTransport(manejador), **kw)


def test_presenta_la_credencial_del_bus_en_cada_llamada(monkeypatch):
    monkeypatch.setattr(settings, "bus_token", TOKEN)
    recibidas = []
    c = _cliente(recibidas)
    c._request("GET", "/coredb/x", authorization="Bearer persona", correlation_id="corr-1")
    c._request("POST", "/coredb/y", json={"a": 1})
    assert [p.headers.get("x-bus-token") for p in recibidas] == [TOKEN, TOKEN]
    # El resto llega igual que sin Bus: el token de la persona y la correlación.
    assert recibidas[0].headers["authorization"] == "Bearer persona"
    assert recibidas[0].headers["x-correlation-id"] == "corr-1"
    assert str(recibidas[0].url) == "http://bus.test/bus/coredb/coredb/x"


def test_sin_credencial_configurada_no_envia_la_cabecera(monkeypatch):
    monkeypatch.setattr(settings, "bus_token", "")
    recibidas = []
    _cliente(recibidas)._request("GET", "/coredb/x")
    assert "x-bus-token" not in recibidas[0].headers


def test_la_credencial_sale_de_bus_token(monkeypatch):
    monkeypatch.setenv("BUS_TOKEN", TOKEN)
    monkeypatch.setenv("CORE_BASE_URL", "http://bus:8018/bus/coredb")
    s = Settings(_env_file=None)
    assert (s.bus_token, s.core_base_url) == (TOKEN, "http://bus:8018/bus/coredb")


def test_por_omision_apunta_al_bus(monkeypatch):
    monkeypatch.delenv("CORE_BASE_URL", raising=False)
    assert Settings(_env_file=None).core_base_url.endswith(":8018/bus/coredb")
