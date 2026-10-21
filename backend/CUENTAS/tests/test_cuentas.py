import json
import logging

import httpx
import pytest

BASE = "/api/v1/cuentas"
KEY = "550e8400-e29b-41d4-a716-446655440000"
NUM = "20261020123456"

CUENTA_CORE = {
    "num_cuenta": NUM, "moneda": "PEN", "regimen": "LIBRE", "estado_cuenta": "ACTIVA",
    "saldo_contable": "0.00", "saldo_disponible": "0.00", "saldo_retenido": "0.00",
    "fecha_apertura": "2026-10-20T10:00:00", "id_agencia": "AG-01", "id_producto_ahorro": "PROD-01",
    "titulares": [{"id_cliente": "CLI-1", "rol_titular": "TITULAR"}],
}

MOV_CORE = {
    "id_transaccion": "t1", "uuid_transaccion": "u1", "num_cuenta": NUM,
    "tipo_operacion": "DEPOSITO", "tipo_movimiento": "DEPOSITO", "monto": "500.00",
    "moneda": "PEN", "monto_moneda_base": "500.00", "saldo_posterior": "500.00",
    "id_asiento": "a1", "idempotency_key": KEY, "replay": False,
}

APERTURA = {"id_cliente": "CLI-1", "id_producto_ahorro": "PROD-01", "id_agencia": "AG-01"}
HEADERS_OP = {"X-Idempotency-Key": KEY, "X-Channel-ID": "WEB", "X-Request-Timestamp": "2026-10-20T21:00:00Z"}


def error_core(status, code, details=None):
    return httpx.Response(status, json={
        "error": {"code": code, "message": "mensaje de core", "details": details or {}},
        "correlation_id": None,
    })


def test_health(client):
    assert client.get("/health").json()["status"] == "healthy"


def test_apertura_formato_de_exito(client, core):
    core.respuesta = httpx.Response(201, json=CUENTA_CORE)
    r = client.post(f"{BASE}/apertura", json=APERTURA, headers={"X-Correlation-ID": "corr-1"})
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["success"] is True
    assert cuerpo["status_code"] == 201
    assert cuerpo["data"]["num_cuenta"] == NUM
    assert cuerpo["data"]["saldo_disponible"] == "0.00"
    meta = cuerpo["metadata"]
    assert meta["modulo_emisor"] == "CUENTAS"
    assert meta["uuid_transaccion"] == "corr-1"
    assert meta["timestamp"].endswith("Z")
    assert "tiempo_ejecucion_ms" in meta
    llamada = core.llamadas[0]
    assert llamada["ruta"] == "/core/cuentas"
    assert llamada["json"]["actor"] == "cuentas"
    assert llamada["headers"]["x-correlation-id"] == "corr-1"


def test_mancomunada_con_un_titular(client, core):
    datos = {**APERTURA, "titulares": [{"id_cliente": "CLI-1", "rol_titular": "MANCOMUNADO"}]}
    r = client.post(f"{BASE}/apertura", json=datos)
    assert r.status_code == 400
    assert r.json()["error_code"] == "ERR-CTA-MANCOMUNADA-SIN-COTITULARES"
    assert r.json()["success"] is False
    assert core.llamadas == []


def test_ver_cuenta(client, core):
    core.respuesta = httpx.Response(200, json=CUENTA_CORE)
    r = client.get(f"{BASE}/{NUM}")
    assert r.status_code == 200
    assert core.llamadas[0]["ruta"] == f"/core/cuentas/{NUM}"


def test_consolidada_devuelve_lista(client, core):
    core.respuesta = httpx.Response(200, json=[CUENTA_CORE, CUENTA_CORE])
    r = client.get(f"{BASE}/consolidada/CLI-1")
    assert r.status_code == 200
    assert len(r.json()["data"]) == 2
    assert core.llamadas[0]["ruta"] == "/core/cuentas/cliente/CLI-1"


def test_cuenta_inexistente(client, core):
    core.respuesta = error_core(404, "CUENTA_NO_ENCONTRADA")
    r = client.get(f"{BASE}/999")
    assert r.status_code == 404
    assert r.json()["error_code"] == "ERR-CTA-NO-ENCONTRADA"


def test_deposito_traduce_cabeceras_a_core(client, core):
    core.respuesta = httpx.Response(201, json=MOV_CORE)
    r = client.post(f"{BASE}/deposito", json={"num_cuenta": NUM, "monto": "500.00"}, headers=HEADERS_OP)
    assert r.status_code == 201
    assert r.json()["data"]["saldo_posterior"] == "500.00"
    llamada = core.llamadas[0]
    assert llamada["ruta"] == "/core/movimientos"
    assert llamada["headers"]["x-idempotency-key"] == KEY
    assert llamada["json"]["tipo_operacion"] == "DEPOSITO"
    assert llamada["json"]["id_canal"] == "HB"  # WEB -> HB
    assert llamada["json"]["monto"] == "500.00"
    assert llamada["json"]["idempotency_key"] == KEY


@pytest.mark.parametrize("canal,esperado", [("ATM", "ATM"), ("AGE", "AGE"), ("VEN", "VEN"), ("MOB", "BD"), ("web", "HB")])
def test_mapeo_de_canales(client, core, canal, esperado):
    core.respuesta = httpx.Response(201, json=MOV_CORE)
    client.post(f"{BASE}/retiro", json={"num_cuenta": NUM, "monto": "10"},
                headers={**HEADERS_OP, "X-Channel-ID": canal})
    assert core.llamadas[0]["json"]["id_canal"] == esperado


@pytest.mark.parametrize("quitar", ["X-Idempotency-Key", "X-Channel-ID", "X-Request-Timestamp"])
def test_header_obligatorio_faltante(client, core, quitar):
    headers = {k: v for k, v in HEADERS_OP.items() if k != quitar}
    r = client.post(f"{BASE}/retiro", json={"num_cuenta": NUM, "monto": "10"}, headers=headers)
    assert r.status_code == 400
    assert r.json()["error_code"] == "ERR-CTA-HEADER-REQUERIDO"
    assert r.json()["details"]["header"] == quitar
    assert core.llamadas == []


def test_idempotency_key_debe_ser_uuid_v4(client, core):
    r = client.post(f"{BASE}/retiro", json={"num_cuenta": NUM, "monto": "10"},
                    headers={**HEADERS_OP, "X-Idempotency-Key": "k-1"})
    assert r.status_code == 400
    assert r.json()["error_code"] == "ERR-CTA-HEADER-INVALIDO"


def test_canal_desconocido(client, core):
    r = client.post(f"{BASE}/retiro", json={"num_cuenta": NUM, "monto": "10"},
                    headers={**HEADERS_OP, "X-Channel-ID": "XXX"})
    assert r.status_code == 400
    assert "ATM" in r.json()["details"]["permitidos"]


def test_timestamp_invalido(client, core):
    r = client.post(f"{BASE}/retiro", json={"num_cuenta": NUM, "monto": "10"},
                    headers={**HEADERS_OP, "X-Request-Timestamp": "ayer"})
    assert r.status_code == 400
    assert r.json()["error_code"] == "ERR-CTA-HEADER-INVALIDO"


def test_monto_con_tres_decimales_es_400_y_no_422(client, core):
    r = client.post(f"{BASE}/retiro", json={"num_cuenta": NUM, "monto": "10.555"}, headers=HEADERS_OP)
    assert r.status_code == 400
    assert r.json()["error_code"] == "ERR-VALIDACION-ESQUEMA"
    assert r.json()["details"][0]["loc"][-1] == "monto"
    assert core.llamadas == []


def test_fondos_insuficientes(client, core):
    core.respuesta = error_core(422, "SALDO_INSUFICIENTE", {"saldo_disponible": "0.00"})
    r = client.post(f"{BASE}/retiro", json={"num_cuenta": NUM, "monto": "100"}, headers=HEADERS_OP)
    assert r.status_code == 400
    assert r.json()["error_code"] == "ERR-CTA-FONDOS-INSUFICIENTES"
    assert r.json()["details"]["saldo_disponible"] == "0.00"


def test_tope_excedido(client, core):
    core.respuesta = error_core(422, "TOPE_DIARIO_EXCEDIDO")
    r = client.post(f"{BASE}/retiro", json={"num_cuenta": NUM, "monto": "100"}, headers=HEADERS_OP)
    assert r.status_code == 400
    assert r.json()["error_code"] == "ERR-CTA-TOPE-EXCEDIDO"


def test_cuenta_bloqueada_es_403(client, core):
    core.respuesta = error_core(422, "CUENTA_NO_OPERATIVA")
    r = client.post(f"{BASE}/retiro", json={"num_cuenta": NUM, "monto": "100"}, headers=HEADERS_OP)
    assert r.status_code == 403
    assert r.json()["error_code"] == "ERR-CTA-BLOQUEADA"


def test_codigo_de_core_desconocido_se_prefija(client, core):
    core.respuesta = error_core(409, "CONFLICTO_UNICIDAD")
    r = client.post(f"{BASE}/apertura", json=APERTURA)
    assert r.status_code == 409
    assert r.json()["error_code"] == "ERR-COR-CONFLICTO-UNICIDAD"


def test_core_responde_422_de_pydantic(client, core):
    core.respuesta = httpx.Response(422, json={"detail": [{"loc": ["body"], "msg": "x"}]})
    r = client.post(f"{BASE}/apertura", json=APERTURA)
    assert r.status_code == 400
    assert r.json()["error_code"] == "ERR-COR-VALIDACION-ESQUEMA"


def test_transferencia_misma_cuenta(client, core):
    r = client.post(f"{BASE}/transferencia", headers=HEADERS_OP,
                    json={"num_cuenta_origen": "111", "num_cuenta_destino": "111", "monto": "10"})
    assert r.status_code == 400
    assert r.json()["error_code"] == "ERR-CTA-CUENTAS-IGUALES"
    assert core.llamadas == []


def test_transferencia_ok(client, core):
    core.respuesta = httpx.Response(201, json={
        "origen": {**MOV_CORE, "num_cuenta": "111", "tipo_operacion": "RETIRO"},
        "destino": {**MOV_CORE, "num_cuenta": "222", "idempotency_key": KEY + "#C"},
        "id_asiento": "a9", "replay": False,
    })
    r = client.post(f"{BASE}/transferencia", headers=HEADERS_OP,
                    json={"num_cuenta_origen": "111", "num_cuenta_destino": "222", "monto": "25.50"})
    assert r.status_code == 201
    enviado = core.llamadas[0]
    assert enviado["ruta"] == "/core/movimientos/transferencias"
    assert enviado["json"]["num_cuenta_origen"] == "111"
    assert enviado["json"]["id_canal"] == "HB"


def test_replay_se_informa_en_el_mensaje(client, core):
    core.respuesta = httpx.Response(201, json={**MOV_CORE, "replay": True})
    r = client.post(f"{BASE}/deposito", json={"num_cuenta": NUM, "monto": "5"}, headers=HEADERS_OP)
    assert r.json()["data"]["replay"] is True
    assert "idempotencia" in r.json()["message"]


def test_core_caido(client, core):
    core.excepcion = httpx.ConnectError("sin conexion")
    r = client.get(f"{BASE}/111")
    assert r.status_code == 503
    assert r.json()["error_code"] == "ERR-COR-NO-DISPONIBLE"


def test_timeout_en_movimiento_queda_no_confirmado(client, core):
    core.excepcion = httpx.ReadTimeout("lento")
    r = client.post(f"{BASE}/retiro", json={"num_cuenta": NUM, "monto": "10"}, headers=HEADERS_OP)
    assert r.status_code == 504
    assert r.json()["error_code"] == "ERR-CTA-OPERACION-NO-CONFIRMADA"


def test_timeout_en_consulta(client, core):
    core.excepcion = httpx.ReadTimeout("lento")
    r = client.get(f"{BASE}/111")
    assert r.status_code == 504
    assert r.json()["error_code"] == "ERR-CTA-TIMEOUT-CORE"


def test_ruta_inexistente_usa_el_mismo_formato(client):
    r = client.get("/api/v1/no-existe")
    assert r.status_code == 404
    assert r.json()["success"] is False
    assert r.json()["error_code"] == "ERR-HTTP-404"


def test_error_no_controlado_es_500_sin_filtrar_detalle(client, core):
    core.excepcion = RuntimeError("clave secreta interna")
    r = client.get(f"{BASE}/111")
    assert r.status_code == 500
    assert r.json()["error_code"] == "ERR-INTERNO-SERVIDOR"
    assert "secreta" not in r.text


def test_log_json_con_campos_obligatorios(client, core, caplog):
    core.respuesta = httpx.Response(201, json=MOV_CORE)
    with caplog.at_level(logging.INFO, logger="BNA_SERVICE_LOGGER"):
        client.post(f"{BASE}/deposito", json={"num_cuenta": NUM, "monto": "5"}, headers=HEADERS_OP)
    registro = json.loads(caplog.records[-1].getMessage())
    for campo in ["timestamp", "level", "uuid_transaccion", "modulo", "endpoint",
                  "status_code", "tiempo_ms", "client_ip", "mensaje"]:
        assert campo in registro
    assert registro["level"] == "INFO"
    assert registro["modulo"] == "CUENTAS"
    assert registro["endpoint"] == f"POST {BASE}/deposito"
    assert registro["uuid_transaccion"] == KEY
    assert registro["datos_contexto"]["canal"] == "WEB"


def test_log_de_error_incluye_error_code(client, core, caplog):
    core.respuesta = error_core(422, "SALDO_INSUFICIENTE")
    with caplog.at_level(logging.INFO, logger="BNA_SERVICE_LOGGER"):
        client.post(f"{BASE}/retiro", json={"num_cuenta": NUM, "monto": "5"}, headers=HEADERS_OP)
    registro = json.loads(caplog.records[-1].getMessage())
    assert registro["level"] == "WARNING"
    assert registro["status_code"] == 400
    assert registro["datos_contexto"]["error_code"] == "ERR-CTA-FONDOS-INSUFICIENTES"


def test_respuesta_trae_cabeceras_de_trazabilidad(client, core):
    core.respuesta = httpx.Response(200, json=CUENTA_CORE)
    r = client.get(f"{BASE}/{NUM}")
    assert "x-response-time-ms" in r.headers
    assert r.headers["x-idempotency-key"]
