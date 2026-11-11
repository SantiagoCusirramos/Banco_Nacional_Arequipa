import json
import logging

import httpx
import pytest

BASE = "/api/v1/cuentas"
KEY = "550e8400-e29b-41d4-a716-446655440000"
NUM = "20261020123456"

TOKEN = "Bearer token-de-prueba"
CUENTA_CORE = {
    "num_cuenta": NUM, "cci": "0" * 20, "moneda": "PEN", "regimen": "INDIVIDUAL",
    "estado_cuenta": "ACTIVA", "saldo_contable": "0.00", "saldo_disponible": "0.00",
    "id_agencia": "AG-01",
}

MOV_CORE = {"uuid_transaccion": "u1", "repetido": False}
TRANSF_CORE = {"uuid_debito": "d1", "uuid_abono": "a1", "repetido": False}

APERTURA = {"num_cuenta": NUM, "cci": "0" * 20, "id_cliente": "CLI-1", "id_agencia": "AG-01"}
AUTH = {"Authorization": TOKEN}
HEADERS_OP = {"X-Idempotency-Key": KEY, "X-Channel-ID": "WEB",
              "X-Request-Timestamp": "2026-10-20T21:00:00Z", **AUTH}


def error_core(status, code, details=None):
    return httpx.Response(status, json={
        "error": {"code": code, "message": "mensaje de core", "details": details or {}},
    })


def test_health(client):
    assert client.get("/health").json()["status"] == "healthy"


def test_apertura_formato_de_exito(client, core):
    core.respuesta = httpx.Response(201, json=CUENTA_CORE)
    r = client.post(f"{BASE}/apertura", json=APERTURA, headers={"X-Correlation-ID": "corr-1", **AUTH})
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
    assert llamada["ruta"] == "/coredb/cuentas"
    assert llamada["json"] == {"num_cuenta": NUM, "cci": "0" * 20, "moneda": "PEN",
                               "regimen": "INDIVIDUAL", "id_agencia": "AG-01", "titulares": ["CLI-1"]}
    assert llamada["headers"]["authorization"] == TOKEN
    assert llamada["headers"]["x-correlation-id"] == "corr-1"


def test_mancomunada_con_un_titular(client, core):
    datos = {**APERTURA, "regimen": "MANCOMUNADA_INDISTINTA", "titulares": [{"id_cliente": "CLI-1"}]}
    r = client.post(f"{BASE}/apertura", json=datos, headers=AUTH)
    assert r.status_code == 400
    assert r.json()["error_code"] == "ERR-CTA-MANCOMUNADA-SIN-COTITULARES"
    assert r.json()["success"] is False
    assert core.llamadas == []


def test_ver_cuenta(client, core):
    core.respuesta = httpx.Response(200, json=CUENTA_CORE)
    r = client.get(f"{BASE}/{NUM}", headers=AUTH)
    assert r.status_code == 200
    assert core.llamadas[0]["ruta"] == f"/coredb/cuentas/{NUM}"


def test_consolidada_aun_no_implementada(client, core):
    r = client.get(f"{BASE}/consolidada/CLI-1", headers=AUTH)
    assert r.status_code == 501
    assert r.json()["error_code"] == "ERR-CTA-NO-IMPLEMENTADO"
    assert core.llamadas == []


def test_cuenta_inexistente(client, core):
    core.respuesta = error_core(404, "CUENTA_NO_ENCONTRADA")
    r = client.get(f"{BASE}/999", headers=AUTH)
    assert r.status_code == 404
    assert r.json()["error_code"] == "ERR-CTA-NO-ENCONTRADA"


def test_deposito_traduce_cabeceras_a_core(client, core):
    core.respuesta = httpx.Response(201, json=MOV_CORE)
    r = client.post(f"{BASE}/deposito", json={"num_cuenta": NUM, "monto": "500.00"}, headers=HEADERS_OP)
    assert r.status_code == 201
    assert r.json()["data"] == {"uuid_transaccion": "u1", "replay": False}
    llamada = core.llamadas[0]
    assert llamada["ruta"] == "/coredb/movimientos"
    assert llamada["headers"]["x-idempotency-key"] == KEY
    assert llamada["headers"]["authorization"] == TOKEN
    assert llamada["json"]["tipo"] == "DEPOSITO"
    assert llamada["json"]["glosa"]
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
    core.respuesta = error_core(422, "BNA-SALDO", {"saldo_disponible": "0.00"})
    r = client.post(f"{BASE}/retiro", json={"num_cuenta": NUM, "monto": "100"}, headers=HEADERS_OP)
    assert r.status_code == 400
    assert r.json()["error_code"] == "ERR-CTA-FONDOS-INSUFICIENTES"
    assert r.json()["details"]["saldo_disponible"] == "0.00"


def test_tope_excedido(client, core):
    core.respuesta = error_core(422, "RN-TOP-001")
    r = client.post(f"{BASE}/retiro", json={"num_cuenta": NUM, "monto": "100"}, headers=HEADERS_OP)
    assert r.status_code == 400
    assert r.json()["error_code"] == "ERR-CTA-TOPE-EXCEDIDO"


def test_cuenta_bloqueada_es_403(client, core):
    core.respuesta = error_core(422, "BNA-ESTADO-CUENTA")
    r = client.post(f"{BASE}/retiro", json={"num_cuenta": NUM, "monto": "100"}, headers=HEADERS_OP)
    assert r.status_code == 403
    assert r.json()["error_code"] == "ERR-CTA-BLOQUEADA"


def test_codigo_de_core_desconocido_se_prefija(client, core):
    core.respuesta = error_core(409, "CONFLICTO_UNICIDAD")
    r = client.post(f"{BASE}/apertura", json=APERTURA, headers=AUTH)
    assert r.status_code == 409
    assert r.json()["error_code"] == "ERR-COR-CONFLICTO-UNICIDAD"


def test_core_responde_422_de_pydantic(client, core):
    core.respuesta = httpx.Response(422, json={"detail": [{"loc": ["body"], "msg": "x"}]})
    r = client.post(f"{BASE}/apertura", json=APERTURA, headers=AUTH)
    assert r.status_code == 400
    assert r.json()["error_code"] == "ERR-COR-VALIDACION-ESQUEMA"


def test_transferencia_misma_cuenta(client, core):
    r = client.post(f"{BASE}/transferencia", headers=HEADERS_OP,
                    json={"num_cuenta_origen": "111", "num_cuenta_destino": "111", "monto": "10"})
    assert r.status_code == 400
    assert r.json()["error_code"] == "ERR-CTA-CUENTAS-IGUALES"
    assert core.llamadas == []


def test_transferencia_ok(client, core):
    core.respuesta = httpx.Response(201, json=TRANSF_CORE)
    r = client.post(f"{BASE}/transferencia", headers=HEADERS_OP,
                    json={"num_cuenta_origen": "111", "num_cuenta_destino": "222", "monto": "25.50"})
    assert r.status_code == 201
    enviado = core.llamadas[0]
    assert enviado["ruta"] == "/coredb/movimientos/transferencias"
    assert enviado["json"]["origen"] == "111"
    assert enviado["json"]["destino"] == "222"
    assert r.json()["data"] == {"uuid_debito": "d1", "uuid_abono": "a1", "replay": False}
    assert enviado["json"]["id_canal"] == "HB"


def test_replay_se_informa_en_el_mensaje(client, core):
    core.respuesta = httpx.Response(201, json={**MOV_CORE, "repetido": True})
    r = client.post(f"{BASE}/deposito", json={"num_cuenta": NUM, "monto": "5"}, headers=HEADERS_OP)
    assert r.json()["data"]["replay"] is True
    assert "idempotencia" in r.json()["message"]


def test_core_caido(client, core):
    core.excepcion = httpx.ConnectError("sin conexion")
    r = client.get(f"{BASE}/111", headers=AUTH)
    assert r.status_code == 503
    assert r.json()["error_code"] == "ERR-COR-NO-DISPONIBLE"


def test_timeout_en_movimiento_queda_no_confirmado(client, core):
    core.excepcion = httpx.ReadTimeout("lento")
    r = client.post(f"{BASE}/retiro", json={"num_cuenta": NUM, "monto": "10"}, headers=HEADERS_OP)
    assert r.status_code == 504
    assert r.json()["error_code"] == "ERR-CTA-OPERACION-NO-CONFIRMADA"


def test_timeout_en_consulta(client, core):
    core.excepcion = httpx.ReadTimeout("lento")
    r = client.get(f"{BASE}/111", headers=AUTH)
    assert r.status_code == 504
    assert r.json()["error_code"] == "ERR-CTA-TIMEOUT-CORE"


def test_ruta_inexistente_usa_el_mismo_formato(client):
    r = client.get("/api/v1/no-existe")
    assert r.status_code == 404
    assert r.json()["success"] is False
    assert r.json()["error_code"] == "ERR-HTTP-404"


def test_error_no_controlado_es_500_sin_filtrar_detalle(client, core):
    core.excepcion = RuntimeError("clave secreta interna")
    r = client.get(f"{BASE}/111", headers=AUTH)
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
    core.respuesta = error_core(422, "BNA-SALDO")
    with caplog.at_level(logging.INFO, logger="BNA_SERVICE_LOGGER"):
        client.post(f"{BASE}/retiro", json={"num_cuenta": NUM, "monto": "5"}, headers=HEADERS_OP)
    registro = json.loads(caplog.records[-1].getMessage())
    assert registro["level"] == "WARNING"
    assert registro["status_code"] == 400
    assert registro["datos_contexto"]["error_code"] == "ERR-CTA-FONDOS-INSUFICIENTES"


def test_sin_token_es_401(client, core):
    r = client.get(f"{BASE}/{NUM}")
    assert r.status_code == 401
    assert r.json()["error_code"] == "ERR-CTA-TOKEN-REQUERIDO"
    assert core.llamadas == []


def test_token_sin_formato_bearer_es_401(client, core):
    r = client.get(f"{BASE}/{NUM}", headers={"Authorization": "abc"})
    assert r.status_code == 401
    assert r.json()["error_code"] == "ERR-CTA-TOKEN-INVALIDO"


def test_permiso_denegado_de_coredb_es_403(client, core):
    core.respuesta = error_core(403, "PERMISO_DENEGADO")
    r = client.post(f"{BASE}/apertura", json=APERTURA, headers=AUTH)
    assert r.status_code == 403
    assert r.json()["error_code"] == "ERR-CTA-PERMISO-DENEGADO"


def test_token_vencido_en_coredb_es_401(client, core):
    core.respuesta = error_core(401, "TOKEN_EXPIRADO")
    r = client.get(f"{BASE}/{NUM}", headers=AUTH)
    assert r.status_code == 401
    assert r.json()["error_code"] == "ERR-CTA-TOKEN-EXPIRADO"


def test_respuesta_trae_cabeceras_de_trazabilidad(client, core):
    core.respuesta = httpx.Response(200, json=CUENTA_CORE)
    r = client.get(f"{BASE}/{NUM}", headers=AUTH)
    assert "x-response-time-ms" in r.headers
    assert r.headers["x-idempotency-key"]
