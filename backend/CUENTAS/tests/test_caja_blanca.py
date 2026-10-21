import json
from datetime import timezone

import httpx
import pytest
from pydantic import ValidationError

from CUENTAS import dependencies as dep
from CUENTAS.core_client import CoreClient
from CUENTAS.errores import MAPA_CORE, traducir
from CUENTAS.exceptions import CuentasError
from CUENTAS.respuestas import ahora_iso, error, exito
from CUENTAS.schemas.cuentas import AbrirCuentaIn, OperacionIn, TransferenciaIn
from CUENTAS.services import cuentas as svc


class Req:
    """Request minimo para probar respuestas.py sin levantar la app."""

    def __init__(self, **estado):
        self.state = type("E", (), estado)()


# errores.traducir

@pytest.mark.parametrize("codigo", list(MAPA_CORE))
def test_traducir_codigos_conocidos(codigo):
    assert traducir(codigo, 400) == MAPA_CORE[codigo]


def test_traducir_codigo_err_pasa_igual():
    assert traducir("ERR-CTA-X", 409) == (409, "ERR-CTA-X")


def test_traducir_422_pasa_a_400():
    assert traducir("ERR-CTA-X", 422) == (400, "ERR-CTA-X")


def test_traducir_codigo_desconocido_se_prefija():
    assert traducir("ALGO_NUEVO", 500) == (500, "ERR-COR-ALGO-NUEVO")


def test_traducir_desconocido_422_pasa_a_400():
    assert traducir("OTRO", 422) == (400, "ERR-COR-OTRO")


# exceptions

def test_cuentas_error_valores_por_defecto():
    e = CuentasError("ERR-X", "msg")
    assert (e.code, e.message, e.status_code, e.details) == ("ERR-X", "msg", 400, {})
    assert str(e) == "msg"


# respuestas

def test_exito_sin_t0_no_incluye_tiempo():
    cuerpo = json.loads(exito(Req(), {"a": 1}).body)
    assert "tiempo_ejecucion_ms" not in cuerpo["metadata"]
    assert cuerpo["metadata"]["uuid_transaccion"]


def test_exito_con_uuid_en_estado():
    cuerpo = json.loads(exito(Req(uuid_transaccion="abc", t0=0.0), None, 201, "listo").body)
    assert cuerpo["metadata"]["uuid_transaccion"] == "abc"
    assert cuerpo["status_code"] == 201
    assert cuerpo["message"] == "listo"
    assert "tiempo_ejecucion_ms" in cuerpo["metadata"]


def test_error_guarda_codigo_y_details_vacio():
    req = Req()
    resp = error(req, 400, "ERR-X", "mal")
    assert req.state.error_code == "ERR-X"
    assert json.loads(resp.body)["details"] == {}
    assert resp.status_code == 400


def test_ahora_iso_formato():
    valor = ahora_iso()
    assert valor.endswith("Z") and len(valor) == 24


# dependencies

KEY_V4 = "550e8400-e29b-41d4-a716-446655440000"
KEY_V1 = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"


def test_idempotency_key_valida():
    assert dep.idempotency_key(KEY_V4) == KEY_V4


@pytest.mark.parametrize("valor,codigo", [
    (None, "ERR-CTA-HEADER-REQUERIDO"),
    ("", "ERR-CTA-HEADER-REQUERIDO"),
    ("no-es-uuid", "ERR-CTA-HEADER-INVALIDO"),
    (KEY_V1, "ERR-CTA-HEADER-INVALIDO"),
])
def test_idempotency_key_invalida(valor, codigo):
    with pytest.raises(CuentasError) as exc:
        dep.idempotency_key(valor)
    assert exc.value.code == codigo
    assert exc.value.status_code == 400


def test_canal_valido_y_en_minuscula():
    assert dep.canal("WEB") == "HB"
    assert dep.canal("mob") == "BD"


def test_canal_faltante_y_desconocido():
    with pytest.raises(CuentasError) as faltante:
        dep.canal(None)
    assert faltante.value.code == "ERR-CTA-HEADER-REQUERIDO"
    with pytest.raises(CuentasError) as raro:
        dep.canal("XXX")
    assert raro.value.code == "ERR-CTA-HEADER-INVALIDO"


def test_timestamp_con_z_y_con_offset():
    assert dep.request_timestamp("2026-10-20T21:00:00Z").tzinfo == timezone.utc
    assert dep.request_timestamp("2026-10-20T21:00:00+00:00").year == 2026


def test_timestamp_faltante_e_invalido():
    with pytest.raises(CuentasError):
        dep.request_timestamp(None)
    with pytest.raises(CuentasError):
        dep.request_timestamp("ayer")


def test_get_core_client_se_cierra():
    gen = dep.get_core_client()
    cliente = next(gen)
    assert isinstance(cliente, CoreClient)
    with pytest.raises(StopIteration):
        next(gen)
    assert cliente._http.is_closed


# core_client

def _core(respuesta=None, excepcion=None):
    def manejador(request):
        if excepcion:
            raise excepcion
        return respuesta
    return CoreClient(base_url="http://core.test", transport=httpx.MockTransport(manejador))


def test_error_de_core_cuerpo_no_json():
    err = CoreClient._error_de_core(httpx.Response(500, text="<html>caido</html>"))
    assert (err.code, err.status_code) == ("ERR-COR-RESPUESTA-INVALIDA", 502)


def test_error_de_core_con_error_sin_codigo():
    err = CoreClient._error_de_core(httpx.Response(400, json={"error": {}}))
    assert err.code == "DESCONOCIDO"
    assert err.status_code == 400


def test_error_de_core_422_con_detail():
    err = CoreClient._error_de_core(httpx.Response(422, json={"detail": [{"loc": ["body"]}]}))
    assert err.code == "ERR-COR-VALIDACION-ESQUEMA"
    assert err.details["detail"] == [{"loc": ["body"]}]


def test_error_de_core_422_con_cuerpo_lista():
    err = CoreClient._error_de_core(httpx.Response(422, json=[1, 2]))
    assert err.code == "ERR-COR-VALIDACION-ESQUEMA"
    assert err.details == {"detail": None}


def test_error_de_core_cuerpo_inesperado():
    err = CoreClient._error_de_core(httpx.Response(400, json={"otra": "cosa"}))
    assert (err.code, err.status_code) == ("ERR-COR-RESPUESTA-INVALIDA", 502)


def test_core_client_close():
    c = _core(httpx.Response(200, json={}))
    c.close()
    assert c._http.is_closed


def test_core_client_sin_headers_opcionales():
    visto = {}

    def manejador(request):
        visto.update(request.headers)
        return httpx.Response(200, json={})

    c = CoreClient(base_url="http://core.test", transport=httpx.MockTransport(manejador))
    c.ver_cuenta("1")
    assert "x-correlation-id" not in visto
    assert "x-idempotency-key" not in visto


def test_core_client_error_http_de_core_se_propaga():
    c = _core(httpx.Response(404, json={"error": {"code": "CUENTA_NO_ENCONTRADA", "message": "x"}}))
    with pytest.raises(CuentasError) as exc:
        c.ver_cuenta("1")
    assert exc.value.status_code == 404
    assert exc.value.code == "CUENTA_NO_ENCONTRADA"


# services

def test_abrir_cuenta_sin_titulares_no_valida_mancomunada():
    c = _core(httpx.Response(201, json={"ok": 1}))
    datos = AbrirCuentaIn(id_cliente="C", id_producto_ahorro="P", id_agencia="A")
    assert svc.abrir_cuenta(c, datos, "cid") == {"ok": 1}


def test_abrir_cuenta_mancomunada_con_dos_titulares_pasa():
    c = _core(httpx.Response(201, json={"ok": 1}))
    datos = AbrirCuentaIn(
        id_cliente="C", id_producto_ahorro="P", id_agencia="A",
        titulares=[{"id_cliente": "C", "rol_titular": "MANCOMUNADO"},
                   {"id_cliente": "D", "rol_titular": "MANCOMUNADO"}],
    )
    assert svc.abrir_cuenta(c, datos, "cid") == {"ok": 1}


def test_abrir_cuenta_titulares_sin_mancomunado_pasa():
    c = _core(httpx.Response(201, json={"ok": 1}))
    datos = AbrirCuentaIn(
        id_cliente="C", id_producto_ahorro="P", id_agencia="A",
        titulares=[{"id_cliente": "C"}],
    )
    assert svc.abrir_cuenta(c, datos, "cid") == {"ok": 1}


def test_transferir_misma_cuenta_no_llama_a_core():
    llamadas = []

    def manejador(request):
        llamadas.append(request)
        return httpx.Response(201, json={})

    c = CoreClient(base_url="http://core.test", transport=httpx.MockTransport(manejador))
    datos = TransferenciaIn(num_cuenta_origen="1", num_cuenta_destino="1", monto="5")
    with pytest.raises(CuentasError) as exc:
        svc.transferir(c, datos, "HB", KEY_V4, "cid")
    assert exc.value.code == "ERR-CTA-CUENTAS-IGUALES"
    assert llamadas == []


# schemas

@pytest.mark.parametrize("monto", ["0", "-1", "10.123", "1" + "0" * 15])
def test_monto_invalido(monto):
    with pytest.raises(ValidationError):
        OperacionIn(num_cuenta="1", monto=monto)


@pytest.mark.parametrize("monto", ["0.01", "10", "99.99", "1234567890123.45"])
def test_monto_valido(monto):
    assert OperacionIn(num_cuenta="1", monto=monto).monto > 0


def test_moneda_solo_pen_o_usd():
    assert OperacionIn(num_cuenta="1", monto="1", moneda="USD").moneda == "USD"
    with pytest.raises(ValidationError):
        OperacionIn(num_cuenta="1", monto="1", moneda="EUR")


def test_num_cuenta_maximo_20():
    with pytest.raises(ValidationError):
        OperacionIn(num_cuenta="1" * 21, monto="1")


def test_regimen_invalido():
    with pytest.raises(ValidationError):
        AbrirCuentaIn(id_cliente="C", id_producto_ahorro="P", id_agencia="A", regimen="OTRO")
