import httpx

CUENTA_CORE = {
    "num_cuenta": "20261020123456",
    "moneda": "PEN",
    "regimen": "LIBRE",
    "estado_cuenta": "ACTIVA",
    "saldo_contable": "0.00",
    "saldo_disponible": "0.00",
    "saldo_retenido": "0.00",
    "fecha_apertura": "2026-10-20T10:00:00",
    "id_agencia": "AG-01",
    "id_producto_ahorro": "PROD-01",
    "titulares": [{"id_cliente": "CLI-1", "rol_titular": "TITULAR"}],
}

MOV_CORE = {
    "id_transaccion": "t1",
    "uuid_transaccion": "u1",
    "num_cuenta": "20261020123456",
    "tipo_operacion": "DEPOSITO",
    "tipo_movimiento": "DEPOSITO",
    "monto": "500.00",
    "moneda": "PEN",
    "monto_moneda_base": "500.00",
    "saldo_posterior": "500.00",
    "id_asiento": "a1",
    "idempotency_key": "k-1",
    "replay": False,
}

APERTURA = {"id_cliente": "CLI-1", "id_producto_ahorro": "PROD-01", "id_agencia": "AG-01"}
HEADERS_OP = {"X-Idempotency-Key": "k-1", "X-Correlation-ID": "corr-1"}


def test_health(client):
    assert client.get("/health").json()["status"] == "healthy"


def test_abrir_cuenta_reenvia_a_core(client, core):
    core.respuesta = httpx.Response(201, json=CUENTA_CORE)
    r = client.post("/cuentas", json=APERTURA, headers={"X-Correlation-ID": "corr-1"})
    assert r.status_code == 201
    assert r.json()["num_cuenta"] == "20261020123456"
    llamada = core.llamadas[0]
    assert llamada["ruta"] == "/core/cuentas"
    assert llamada["json"]["id_cliente"] == "CLI-1"
    assert llamada["json"]["actor"] == "cuentas"
    assert llamada["headers"]["x-correlation-id"] == "corr-1"


def test_mancomunada_con_un_titular_no_llega_a_core(client, core):
    datos = {**APERTURA, "titulares": [{"id_cliente": "CLI-1", "rol_titular": "MANCOMUNADO"}]}
    r = client.post("/cuentas", json=datos)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "MANCOMUNADA_REQUIERE_COTITULARES"
    assert core.llamadas == []


def test_ver_cuenta_inexistente_pasa_el_error_de_core(client, core):
    core.respuesta = httpx.Response(404, json={
        "error": {"code": "CUENTA_NO_ENCONTRADA", "message": "no existe", "details": {}},
        "correlation_id": None,
    })
    r = client.get("/cuentas/999")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "CUENTA_NO_ENCONTRADA"


def test_deposito_envia_llave_de_idempotencia_y_monto_como_texto(client, core):
    core.respuesta = httpx.Response(201, json=MOV_CORE)
    r = client.post("/cuentas/20261020123456/depositos",
                    json={"monto": "500.00", "id_canal": "VEN"}, headers=HEADERS_OP)
    assert r.status_code == 201
    llamada = core.llamadas[0]
    assert llamada["ruta"] == "/core/movimientos"
    assert llamada["headers"]["x-idempotency-key"] == "k-1"
    assert llamada["json"]["tipo_operacion"] == "DEPOSITO"
    assert llamada["json"]["monto"] == "500.00"
    assert llamada["json"]["idempotency_key"] == "k-1"


def test_deposito_sin_llave_de_idempotencia(client, core):
    r = client.post("/cuentas/20261020123456/depositos", json={"monto": "10", "id_canal": "VEN"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUERIDA"
    assert core.llamadas == []


def test_monto_con_mas_de_dos_decimales_se_rechaza(client, core):
    r = client.post("/cuentas/20261020123456/retiros",
                    json={"monto": "10.555", "id_canal": "ATM"}, headers=HEADERS_OP)
    assert r.status_code == 422
    assert core.llamadas == []


def test_canal_invalido(client, core):
    r = client.post("/cuentas/20261020123456/retiros",
                    json={"monto": "10", "id_canal": "XXX"}, headers=HEADERS_OP)
    assert r.status_code == 422


def test_retiro_saldo_insuficiente_viene_de_core(client, core):
    core.respuesta = httpx.Response(422, json={
        "error": {"code": "SALDO_INSUFICIENTE", "message": "excede el saldo",
                  "details": {"saldo_disponible": "0.00"}},
        "correlation_id": "corr-1",
    })
    r = client.post("/cuentas/20261020123456/retiros",
                    json={"monto": "100", "id_canal": "ATM"}, headers=HEADERS_OP)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "SALDO_INSUFICIENTE"
    assert r.json()["error"]["details"]["saldo_disponible"] == "0.00"


def test_transferencia_a_la_misma_cuenta(client, core):
    r = client.post("/cuentas/111/transferencias",
                    json={"monto": "10", "id_canal": "HB", "num_cuenta_destino": "111"},
                    headers=HEADERS_OP)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "CUENTAS_IGUALES"
    assert core.llamadas == []


def test_transferencia_ok(client, core):
    mov_destino = {**MOV_CORE, "num_cuenta": "222", "idempotency_key": "k-1#C"}
    core.respuesta = httpx.Response(201, json={
        "origen": {**MOV_CORE, "num_cuenta": "111", "tipo_operacion": "RETIRO"},
        "destino": mov_destino, "id_asiento": "a9", "replay": False,
    })
    r = client.post("/cuentas/111/transferencias",
                    json={"monto": "25.50", "id_canal": "HB", "num_cuenta_destino": "222"},
                    headers=HEADERS_OP)
    assert r.status_code == 201
    enviado = core.llamadas[0]
    assert enviado["ruta"] == "/core/movimientos/transferencias"
    assert enviado["json"]["num_cuenta_origen"] == "111"
    assert enviado["json"]["num_cuenta_destino"] == "222"


def test_core_caido(client, core):
    core.excepcion = httpx.ConnectError("sin conexion")
    r = client.get("/cuentas/111")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "CORE_NO_DISPONIBLE"


def test_timeout_en_movimiento_queda_no_confirmado(client, core):
    core.excepcion = httpx.ReadTimeout("lento")
    r = client.post("/cuentas/111/retiros",
                    json={"monto": "10", "id_canal": "ATM"}, headers=HEADERS_OP)
    assert r.status_code == 504
    assert r.json()["error"]["code"] == "OPERACION_NO_CONFIRMADA"


def test_timeout_en_consulta(client, core):
    core.excepcion = httpx.ReadTimeout("lento")
    r = client.get("/cuentas/111")
    assert r.status_code == 504
    assert r.json()["error"]["code"] == "CORE_TIMEOUT"
