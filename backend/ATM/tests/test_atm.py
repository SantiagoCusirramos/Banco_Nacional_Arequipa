"""Pruebas del módulo ATM: retiro, consultas, idempotencia y extorno.

Usa transporte simulado para TARJETAS y CUENTAS (CoreFalso).
"""

import httpx
import pytest

BASE = "/api"
ID_TARJETA = "7e570001-0000-4000-8000-000000000001"
AUTH = {"Authorization": "Bearer token-de-prueba"}
KEY = "550e8400-e29b-41d4-a716-446655440000"
HEADERS = {"X-Idempotency-Key": KEY, **AUTH}
CORR = {"X-Correlation-ID": "corr-test-001"}

# Respuestas simuladas de TARJETAS
def pin_ok():
    return {"resultado": "EXITOSO", "intentos_restantes": 3}

def pin_fallido(intentos=2):
    return {"resultado": "FALLIDO", "intentos_restantes": intentos}

def autorizacion_ok(uuid_aut="5a1f0c3e-0000-4000-8000-000000000001", estado="AUTORIZADA", codigo="00"):
    return {
        "uuid_autorizacion": uuid_aut,
        "id_tarjeta": ID_TARJETA,
        "num_cuenta": "10100000000001",
        "id_canal": "ATM",
        "id_terminal": None,
        "tipo_operacion": "RETIRO",
        "monto": "150.00",
        "estado_autorizacion": estado,
        "codigo_respuesta": codigo,
        "motivo_rechazo": None,
    }

def autorizacion_dispensada(uuid_aut="5a1f0c3e-0000-4000-8000-000000000001"):
    return {
        **autorizacion_ok(uuid_aut, "DISPENSADA", "00"),
        "uuid_transaccion": "9e8d7c6b-0000-4000-8000-000000000001",
    }

def extorno_ok(uuid_aut="5a1f0c3e-0000-4000-8000-000000000001"):
    return {
        **autorizacion_ok(uuid_aut, "EXTORNADA", "EXT"),
        "id_contra_asiento": "CA-000001",
        "saldo_disponible": "100.00",
    }

def saldo_cuentas():
    return {
        "lista_cuentas": [
            {"id_cuenta": "10100000000001", "num_cuenta_enmascarado": "****0001", "moneda": "PEN", "saldo_disponible": "500.00"},
            {"id_cuenta": "10100000000002", "num_cuenta_enmascarado": "****0002", "moneda": "USD", "saldo_disponible": "100.00"},
        ],
        "uuid_consulta": "corr-test-001",
        "simulado": False,
    }

def movimientos_cuenta():
    return [
        {"uuid_transaccion": "txn-1", "tipo_operacion": "RETIRO", "naturaleza": "D", "monto": "150.00", "fecha_hora": "2026-11-15T10:00:00Z"},
        {"uuid_transaccion": "txn-2", "tipo_operacion": "DEPOSITO", "naturaleza": "C", "monto": "500.00", "fecha_hora": "2026-11-14T10:00:00Z"},
    ]

def error_core(status, code, message="mensaje de core"):
    return httpx.Response(status, json={"error": {"code": code, "message": message}})


# ── Health / Ready ────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"
    assert r.json()["modulo"] == "atm"


def test_ready_ok(client, core):
    core.respuesta = httpx.Response(200, json={"status": "healthy"})
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


def test_ready_tarjetas_caido(client, core):
    core.respuesta = httpx.Response(503)
    r = client.get("/ready")
    assert r.status_code == 503
    assert r.json()["status"] == "not_ready"


# ── Validar PIN ───────────────────────────────────────────────────────────

def test_validar_pin_exitoso(client, core):
    core.respuesta = httpx.Response(200, json=pin_ok())
    r = client.post(f"{BASE}/validar-pin", json={"id_tarjeta": ID_TARJETA, "pin": "4821", "id_terminal": "ATM-AQP-001"}, headers={**HEADERS, **CORR})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["resultado"] == "EXITOSO"
    assert data["intentos_restantes"] == 3
    # Verifica que llamó a TARJETAS por el Bus
    assert core.llamadas[0]["ruta"] == "/bus/tarjetas/api/v1/tarjetas/7e570001-0000-4000-8000-000000000001/credenciales/PIN_ATM/validacion"
    # correlation_id va en cabecera X-Correlation-ID, no en el body
    assert core.llamadas[0]["json"] == {"valor": "4821", "id_terminal": "ATM-AQP-001"}
    assert core.llamadas[0]["headers"]["x-correlation-id"] == "corr-test-001"


def test_validar_pin_incorrecto(client, core):
    core.respuesta = httpx.Response(200, json=pin_fallido(2))
    r = client.post(f"{BASE}/validar-pin", json={"id_tarjeta": ID_TARJETA, "pin": "0000", "id_terminal": "ATM-AQP-001"}, headers={**HEADERS, **CORR})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["resultado"] == "FALLIDO"
    assert data["intentos_restantes"] == 2


def test_validar_pin_tarjeta_bloqueada(client, core):
    core.respuesta = error_core(400, "ERR-TAR-003", "la tarjeta no es operativa (estado BLOQUEADA)")
    r = client.post(f"{BASE}/validar-pin", json={"id_tarjeta": ID_TARJETA, "pin": "0000", "id_terminal": "ATM-AQP-001"}, headers={**HEADERS, **CORR})
    assert r.status_code == 400
    # El ATM traduce el código de TARJETAS
    assert r.json()["error_code"] == "ERR-ATM-TARJETA-NO-OPERATIVA"


# PIN validation no requiere X-Idempotency-Key (a diferencia de autorizar/confirmar)
# Estas pruebas verifican que la validación de PIN funciona sin llave de idempotencia
def test_validar_pin_sin_llave_ok(client, core):
    core.respuesta = httpx.Response(200, json=pin_ok())
    r = client.post(f"{BASE}/validar-pin", json={"id_tarjeta": ID_TARJETA, "pin": "4821", "id_terminal": "ATM-AQP-001"}, headers={**AUTH, **CORR})
    assert r.status_code == 200
    assert r.json()["data"]["resultado"] == "EXITOSO"
    assert core.llamadas[0]["ruta"] == "/bus/tarjetas/api/v1/tarjetas/7e570001-0000-4000-8000-000000000001/credenciales/PIN_ATM/validacion"


def test_validar_pin_con_llave_tambien_ok(client, core):
    core.respuesta = httpx.Response(200, json=pin_ok())
    r = client.post(f"{BASE}/validar-pin", json={"id_tarjeta": ID_TARJETA, "pin": "4821", "id_terminal": "ATM-AQP-001"}, headers={**HEADERS, **CORR})
    assert r.status_code == 200
    assert r.json()["data"]["resultado"] == "EXITOSO"


# ── Autorizar Retiro ──────────────────────────────────────────────────────

def test_autorizar_retiro_ok(client, core):
    core.respuesta = httpx.Response(201, json=autorizacion_ok())
    r = client.post(f"{BASE}/autorizar", json={
        "id_tarjeta": ID_TARJETA,
        "num_cuenta": "10100000000001",
        "moneda": "PEN",
        "monto": "150.00",
        "id_terminal": "ATM-AQP-001",
        "uuid_transaccion": "5a1f0c3e-0000-4000-8000-000000000001",
    }, headers={**HEADERS, **CORR})
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["aprobada"] is True
    assert data["codigo_respuesta"] == "00"
    assert data["estado_autorizacion"] == "AUTORIZADA"
    # Verifica llamada a TARJETAS
    assert core.llamadas[0]["ruta"] == "/bus/tarjetas/api/v1/tarjetas/7e570001-0000-4000-8000-000000000001/autorizaciones"
    assert core.llamadas[0]["json"]["tipo_operacion"] == "RETIRO"
    assert core.llamadas[0]["json"]["monto"] == "150.00"


def test_autorizar_retiro_rechazado_sin_fondos(client, core):
    core.respuesta = httpx.Response(201, json=autorizacion_ok(estado="RECHAZADA", codigo="51"))
    r = client.post(f"{BASE}/autorizar", json={
        "id_tarjeta": ID_TARJETA,
        "num_cuenta": "10100000000001",
        "moneda": "PEN",
        "monto": "150.00",
        "id_terminal": "ATM-AQP-001",
        "uuid_transaccion": "5a1f0c3e-0000-4000-8000-000000000001",
    }, headers={**HEADERS, **CORR})
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["aprobada"] is False
    assert data["codigo_respuesta"] == "51"


def test_autorizar_retiro_tope_excedido(client, core):
    core.respuesta = httpx.Response(201, json=autorizacion_ok(estado="RECHAZADA", codigo="61"))
    r = client.post(f"{BASE}/autorizar", json={
        "id_tarjeta": ID_TARJETA,
        "num_cuenta": "10100000000001",
        "moneda": "PEN",
        "monto": "2000.00",
        "id_terminal": "ATM-AQP-001",
        "uuid_transaccion": "5a1f0c3e-0000-4000-8000-000000000001",
    }, headers={**HEADERS, **CORR})
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["aprobada"] is False
    assert data["codigo_respuesta"] == "61"


def test_autorizar_idempotencia_misma_llave(client, core):
    """La misma llave de idempotencia devuelve la autorización ya registrada."""
    core.respuesta = httpx.Response(201, json=autorizacion_ok())
    # Primera llamada
    r1 = client.post(f"{BASE}/autorizar", json={
        "id_tarjeta": ID_TARJETA,
        "num_cuenta": "10100000000001",
        "moneda": "PEN",
        "monto": "150.00",
        "id_terminal": "ATM-AQP-001",
        "uuid_transaccion": "5a1f0c3e-0000-4000-8000-000000000001",
    }, headers={**HEADERS, **CORR})
    assert r1.status_code == 201
    # Segunda llamada con misma llave
    core.respuesta = httpx.Response(201, json=autorizacion_ok())
    r2 = client.post(f"{BASE}/autorizar", json={
        "id_tarjeta": ID_TARJETA,
        "num_cuenta": "10100000000001",
        "moneda": "PEN",
        "monto": "150.00",
        "id_terminal": "ATM-AQP-001",
        "uuid_transaccion": "5a1f0c3e-0000-4000-8000-000000000001",
    }, headers={**HEADERS, **CORR})
    assert r2.status_code == 201
    assert r2.json()["data"]["uuid_autorizacion"] == r1.json()["data"]["uuid_autorizacion"]


def test_autorizar_misma_llave_otros_datos_409(client, core):
    core.respuesta = error_core(409, "ERR-TAR-IDEMPOTENCIA")
    r = client.post(f"{BASE}/autorizar", json={
        "id_tarjeta": ID_TARJETA,
        "num_cuenta": "10100000000002",  # otra cuenta
        "moneda": "PEN",
        "monto": "150.00",
        "id_terminal": "ATM-AQP-001",
        "uuid_transaccion": "5a1f0c3e-0000-4000-8000-000000000001",
    }, headers={**HEADERS, **CORR})
    assert r.status_code == 409
    # El ATM traduce el código de TARJETAS
    assert r.json()["error_code"] == "ERR-ATM-IDEMPOTENCIA"


def test_autorizar_sin_llave_400(client, core):
    r = client.post(f"{BASE}/autorizar", json={
        "id_tarjeta": ID_TARJETA,
        "num_cuenta": "10100000000001",
        "moneda": "PEN",
        "monto": "150.00",
        "id_terminal": "ATM-AQP-001",
        "uuid_transaccion": "5a1f0c3e-0000-4000-8000-000000000001",
    }, headers={**AUTH, **CORR})
    assert r.status_code == 400
    assert r.json()["error_code"] == "ERR-ATM-HEADER-REQUERIDO"
    assert core.llamadas == []


def test_autorizar_cuenta_invalida_400(client, core):
    core.respuesta = error_core(400, "ERR-TAR-CUENTA-INVALIDA")
    r = client.post(f"{BASE}/autorizar", json={
        "id_tarjeta": ID_TARJETA,
        "num_cuenta": "99999999999999",
        "moneda": "PEN",
        "monto": "150.00",
        "id_terminal": "ATM-AQP-001",
        "uuid_transaccion": "5a1f0c3e-0000-4000-8000-000000000001",
    }, headers={**HEADERS, **CORR})
    assert r.status_code == 400
    # El ATM traduce el código de TARJETAS
    assert r.json()["error_code"] == "ERR-ATM-CUENTA-INVALIDA"


# ── Confirmar Dispensación ────────────────────────────────────────────────

def test_confirmar_dispensacion_ok(client, core):
    uuid_aut = "5a1f0c3e-0000-4000-8000-000000000001"
    core.respuesta = httpx.Response(200, json=autorizacion_dispensada(uuid_aut))
    r = client.post(f"{BASE}/confirmar", json={
        "uuid_autorizacion": uuid_aut,
        "id_terminal": "ATM-AQP-001",
        "resultado": "DISPENSADO",
    }, headers={**HEADERS, **CORR})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["estado_autorizacion"] == "DISPENSADA"
    assert "uuid_transaccion" in data
    # Verifica llamada a TARJETAS
    assert core.llamadas[0]["ruta"] == f"/bus/tarjetas/api/v1/tarjetas/autorizaciones/{uuid_aut}/confirmacion"
    assert core.llamadas[0]["json"] == {"id_terminal": "ATM-AQP-001", "resultado": "DISPENSADO"}


def test_confirmar_idempotencia_misma_llave_sin_segundo_debito(client, core):
    """Repetir la confirmación con la misma llave no debita dos veces."""
    uuid_aut = "5a1f0c3e-0000-4000-8000-000000000001"
    core.respuesta = httpx.Response(200, json=autorizacion_dispensada(uuid_aut))
    r1 = client.post(f"{BASE}/confirmar", json={
        "uuid_autorizacion": uuid_aut,
        "id_terminal": "ATM-AQP-001",
        "resultado": "DISPENSADO",
    }, headers={**HEADERS, **CORR})
    assert r1.status_code == 200
    uuid_txn_1 = r1.json()["data"]["uuid_transaccion"]

    # Segunda confirmación con misma llave
    core.respuesta = httpx.Response(200, json=autorizacion_dispensada(uuid_aut))
    r2 = client.post(f"{BASE}/confirmar", json={
        "uuid_autorizacion": uuid_aut,
        "id_terminal": "ATM-AQP-001",
        "resultado": "DISPENSADO",
    }, headers={**HEADERS, **CORR})
    assert r2.status_code == 200
    assert r2.json()["data"]["uuid_transaccion"] == uuid_txn_1


# ── Extorno ───────────────────────────────────────────────────────────────

def test_extornar_ok(client, core):
    uuid_aut = "5a1f0c3e-0000-4000-8000-000000000001"
    core.respuesta = httpx.Response(200, json=extorno_ok(uuid_aut))
    r = client.post(f"{BASE}/extornar", json={
        "uuid_autorizacion": uuid_aut,
        "motivo": "FALLA_DISPENSADOR",
    }, headers={**AUTH, **CORR})  # extorno no exige X-Idempotency-Key
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["estado_autorizacion"] == "EXTORNADA"
    assert data["codigo_respuesta"] == "EXT"
    assert data["id_contra_asiento"] == "CA-000001"
    assert core.llamadas[0]["ruta"] == f"/bus/tarjetas/api/v1/tarjetas/autorizaciones/{uuid_aut}/extorno"
    assert core.llamadas[0]["json"] == {"motivo": "FALLA_DISPENSADOR"}


def test_extornar_ya_contabilizada_409(client, core):
    uuid_aut = "5a1f0c3e-0000-4000-8000-000000000001"
    core.respuesta = error_core(409, "ERR-TAR-EXTORNO-NO-PERMITIDO")
    r = client.post(f"{BASE}/extornar", json={
        "uuid_autorizacion": uuid_aut,
        "motivo": "FALLA_DISPENSADOR",
    }, headers={**AUTH, **CORR})
    assert r.status_code == 409
    # El ATM traduce el código de TARJETAS
    assert r.json()["error_code"] == "ERR-ATM-EXTORNO-NO-PERMITIDO"


def test_extornar_no_existe_404(client, core):
    uuid_aut = "5a1f0c3e-0000-4000-8000-000000000001"
    core.respuesta = error_core(404, "ERR-TAR-AUTORIZACION-NO-ENCONTRADA")
    r = client.post(f"{BASE}/extornar", json={
        "uuid_autorizacion": uuid_aut,
        "motivo": "FALLA_DISPENSADOR",
    }, headers={**AUTH, **CORR})
    assert r.status_code == 404
    # El ATM traduce el código de TARJETAS
    assert r.json()["error_code"] == "ERR-ATM-AUTORIZACION-NO-ENCONTRADA"


# ── Consultar Saldo ───────────────────────────────────────────────────────

def test_consultar_saldo_ok(client, core):
    # El servicio hace dos llamadas: 1) TARJETAS para obtener tarjeta (cod_cliente), 2) CUENTAS para saldo consolidado
    core.respuesta = [
        httpx.Response(200, json={"id_tarjeta": ID_TARJETA, "cod_cliente": "CLI001", "estado_tarjeta": "ACTIVA"}),
        httpx.Response(200, json=saldo_cuentas()),
    ]
    r = client.get(f"{BASE}/saldo", params={"id_tarjeta": ID_TARJETA}, headers={**AUTH, **CORR})
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data["lista_cuentas"]) == 2
    assert data["lista_cuentas"][0]["moneda"] == "PEN"
    assert data["lista_cuentas"][0]["saldo_disponible"] == "500.00"
    # Verifica que llamó a TARJETAS y luego a CUENTAS por el Bus
    assert len(core.llamadas) == 2
    assert "tarjetas" in core.llamadas[0]["ruta"]
    assert "cuentas" in core.llamadas[1]["ruta"]


def test_consultar_saldo_sin_cuentas(client, core):
    core.respuesta = [
        httpx.Response(200, json={"id_tarjeta": ID_TARJETA, "cod_cliente": "CLI001", "estado_tarjeta": "ACTIVA"}),
        httpx.Response(200, json={"lista_cuentas": [], "uuid_consulta": "corr-test", "simulado": False}),
    ]
    r = client.get(f"{BASE}/saldo", params={"id_tarjeta": ID_TARJETA}, headers={**AUTH, **CORR})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["lista_cuentas"] == []


def test_consultar_saldo_sesion_invalida_401(client, core):
    core.respuesta = error_core(401, "ERR-COR-TOKEN-EXPIRADO")
    r = client.get(f"{BASE}/saldo", params={"id_tarjeta": ID_TARJETA}, headers={**AUTH, **CORR})
    assert r.status_code == 401


# ── Consultar Movimientos ─────────────────────────────────────────────────

def test_consultar_movimientos_ok(client, core):
    core.respuesta = httpx.Response(200, json=movimientos_cuenta())
    r = client.get(f"{BASE}/movimientos", params={"num_cuenta": "10100000000001"}, headers={**AUTH, **CORR})
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data) == 2
    assert data[0]["tipo_operacion"] == "RETIRO"
    assert data[0]["monto"] == "150.00"


# ── Estado del Cajero ─────────────────────────────────────────────────────

def test_estado_cajero(client, core):
    # El estado del cajero es local, no llama a core
    r = client.get(f"{BASE}/estado")
    assert r.status_code == 200
    data = r.json()["data"]
    assert "bandejas" in data
    assert "pendientes" in data
    assert data["terminal"] == "ATM-AQP-001"


def test_config_cajero(client):
    r = client.get(f"{BASE}/config")
    assert r.status_code == 200
    data = r.json()["data"]
    assert "id_cajero" in data
    assert "pruebas" in data


# ── Flujo Completo de Retiro (Integración) ────────────────────────────────

def test_flujo_retiro_completo_feliz(client, core):
    """PIN OK → Autorizar → Confirmar → Saldo actualizado."""
    # 1. Validar PIN
    core.respuesta = httpx.Response(200, json=pin_ok())
    r = client.post(f"{BASE}/validar-pin", json={"id_tarjeta": ID_TARJETA, "pin": "4821", "id_terminal": "ATM-AQP-001"}, headers={**HEADERS, **CORR})
    assert r.status_code == 200
    assert r.json()["data"]["resultado"] == "EXITOSO"

    # 2. Autorizar retención
    core.respuesta = httpx.Response(201, json=autorizacion_ok())
    r = client.post(f"{BASE}/autorizar", json={
        "id_tarjeta": ID_TARJETA,
        "num_cuenta": "10100000000001",
        "moneda": "PEN",
        "monto": "150.00",
        "id_terminal": "ATM-AQP-001",
        "uuid_transaccion": "5a1f0c3e-0000-4000-8000-000000000001",
    }, headers={**HEADERS, **CORR})
    assert r.status_code == 201
    uuid_aut = r.json()["data"]["uuid_autorizacion"]
    assert r.json()["data"]["aprobada"] is True

    # 3. Confirmar dispensación
    core.respuesta = httpx.Response(200, json=autorizacion_dispensada(uuid_aut))
    r = client.post(f"{BASE}/confirmar", json={
        "uuid_autorizacion": uuid_aut,
        "id_terminal": "ATM-AQP-001",
        "resultado": "DISPENSADO",
    }, headers={**HEADERS, **CORR})
    assert r.status_code == 200
    assert r.json()["data"]["estado_autorizacion"] == "DISPENSADA"


def test_flujo_retiro_falla_dispensador_extorno(client, core):
    """PIN OK → Autorizar → Fallo dispensador → Extorno → Saldo liberado."""
    # 1. Validar PIN
    core.respuesta = httpx.Response(200, json=pin_ok())
    r = client.post(f"{BASE}/validar-pin", json={"id_tarjeta": ID_TARJETA, "pin": "4821", "id_terminal": "ATM-AQP-001"}, headers={**HEADERS, **CORR})
    assert r.status_code == 200

    # 2. Autorizar retención
    core.respuesta = httpx.Response(201, json=autorizacion_ok())
    r = client.post(f"{BASE}/autorizar", json={
        "id_tarjeta": ID_TARJETA,
        "num_cuenta": "10100000000001",
        "moneda": "PEN",
        "monto": "150.00",
        "id_terminal": "ATM-AQP-001",
        "uuid_transaccion": "5a1f0c3e-0000-4000-8000-000000000001",
    }, headers={**HEADERS, **CORR})
    assert r.status_code == 201
    uuid_aut = r.json()["data"]["uuid_autorizacion"]

    # 3. Fallo al dispensar → Extorno
    core.respuesta = httpx.Response(200, json=extorno_ok(uuid_aut))
    r = client.post(f"{BASE}/extornar", json={
        "uuid_autorizacion": uuid_aut,
        "motivo": "FALLA_DISPENSADOR",
    }, headers={**AUTH, **CORR})
    assert r.status_code == 200
    assert r.json()["data"]["estado_autorizacion"] == "EXTORNADA"
    assert r.json()["data"]["codigo_respuesta"] == "EXT"
    assert "id_contra_asiento" in r.json()["data"]


# ── Validaciones de Entrada ───────────────────────────────────────────────

def test_autorizar_monto_invalido_400(client, core):
    r = client.post(f"{BASE}/autorizar", json={
        "id_tarjeta": ID_TARJETA,
        "num_cuenta": "10100000000001",
        "moneda": "PEN",
        "monto": "15.50",  # no múltiplo de 10
        "id_terminal": "ATM-AQP-001",
        "uuid_transaccion": "5a1f0c3e-0000-4000-8000-000000000001",
    }, headers={**HEADERS, **CORR})
    assert r.status_code == 400
    # La validación de Pydantic devuelve ERR-ATM-VALIDACION-ESQUEMA
    assert r.json()["error_code"] == "ERR-ATM-VALIDACION-ESQUEMA"
    assert core.llamadas == []


def test_autorizar_moneda_invalida_400(client, core):
    r = client.post(f"{BASE}/autorizar", json={
        "id_tarjeta": ID_TARJETA,
        "num_cuenta": "10100000000001",
        "moneda": "EUR",  # no soportada
        "monto": "150.00",
        "id_terminal": "ATM-AQP-001",
        "uuid_transaccion": "5a1f0c3e-0000-4000-8000-000000000001",
    }, headers={**HEADERS, **CORR})
    assert r.status_code == 400
    # La validación de Pydantic devuelve ERR-ATM-VALIDACION-ESQUEMA
    assert r.json()["error_code"] == "ERR-ATM-VALIDACION-ESQUEMA"
    assert core.llamadas == []


def test_confirmar_resultado_invalido_400(client, core):
    r = client.post(f"{BASE}/confirmar", json={
        "uuid_autorizacion": "5a1f0c3e-0000-4000-8000-000000000001",
        "id_terminal": "ATM-AQP-001",
        "resultado": "INVALIDO",
    }, headers={**HEADERS, **CORR})
    assert r.status_code == 400
    # La validación de Pydantic devuelve ERR-ATM-VALIDACION-ESQUEMA
    assert r.json()["error_code"] == "ERR-ATM-VALIDACION-ESQUEMA"