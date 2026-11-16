"""Créditos, área de cobranza (CONTRATO_CREDITOS.md §5) contra la base real."""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from creditos_apoyo import (
    BASE, empleado, hoy_lima, orden_validada, saldo, sesion_servicio, usuario_con_empleado,
)
from fastapi.testclient import TestClient

from COREDB.main import app

# El calendario de creditos_apoyo para 3000.00 en 3 cuotas: 1000.00 de capital cada una y 1 %
# de interés sobre el saldo.
CUOTAS = [Decimal("1030.00"), Decimal("1020.00"), Decimal("1010.00")]
DEUDA = sum(CUOTAS)


@pytest.fixture
def api():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def servicio(autorizacion, datos_base):
    return sesion_servicio(autorizacion, "EVALUACION")


@pytest.fixture(scope="module")
def cobranza(autorizacion, datos_base):
    """(encabezados, username) de svc-cobranza."""
    return sesion_servicio(autorizacion, "COBRANZA")


@pytest.fixture(scope="module")
def analista(autorizacion, admin, datos_base):
    id_empleado = empleado(admin)
    registrado = TestClient(app).post(f"{BASE}/analistas", json={"idEmpleado": str(id_empleado)},
                                      headers=autorizacion)
    assert registrado.status_code == 201, registrado.text
    return usuario_con_empleado(autorizacion, "ANALISTA", id_empleado)


@pytest.fixture(scope="module")
def operador(autorizacion, datos_base):
    api = TestClient(app)
    username, password = "u" + uuid.uuid4().hex[:12], "clave-de-un-usuario-1"
    creado = api.post("/coredb/usuarios", headers=autorizacion, json={
        "username": username, "nombre": "Operador", "password": password, "rol": "OPERADOR"})
    assert creado.status_code == 201, creado.text
    login = api.post("/coredb/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, username


@pytest.fixture
def credito(api, servicio, analista, operador, abrir_cuenta):
    """Un crédito de 3000.00 en 3 cuotas recién desembolsado: (codCredito, cuenta del abono)."""
    def _credito():
        _, orden, num_cuenta = orden_validada(api, servicio, analista, operador, abrir_cuenta, monto="3000.00",
                                              plazo=3)
        confirmada = api.post(f"{BASE}/ordenes/{orden['idOrden']}/confirmacion", headers=operador[0])
        assert confirmada.status_code == 201, confirmada.text
        return confirmada.json()["codCredito"], num_cuenta

    return _credito


def pagar(api, encabezados, cod_credito, num_cuenta, monto, referencia=None, **extra):
    cuerpo = {"numCuenta": num_cuenta, "monto": str(monto), "referencia": referencia or nueva_referencia(), **extra}
    return api.post(f"{BASE}/{cod_credito}/pagos", json=cuerpo, headers=encabezados)


def nueva_referencia():
    return "REF-" + uuid.uuid4().hex[:16].upper()


def depositar(api, autorizacion, num_cuenta, monto):
    respuesta = api.post("/coredb/movimientos", headers=autorizacion, json={
        "num_cuenta": num_cuenta, "tipo": "DEPOSITO", "monto": str(monto), "glosa": "g", "id_canal": "VEN"})
    assert respuesta.status_code == 201, respuesta.text


def debitos(consulta, num_cuenta):
    return list(consulta("SELECT BIN_TO_UUID(uuid_transaccion) AS uuid, monto FROM cuentas.movimiento "
                         "WHERE num_cuenta = %s AND tipo_operacion = 'DEBITO_CUOTA'", num_cuenta))


def detalle(api, encabezados, cod_credito):
    respuesta = api.get(f"{BASE}/{cod_credito}", headers=encabezados)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def vencer_cuota(consulta, cod_credito, numero_cuota, dias):
    """Adelanta el vencimiento de una cuota: los créditos de las pruebas nacen al día."""
    consulta("UPDATE creditos.cuota SET fecha_vencimiento = %s WHERE numero_cuota = %s AND id_calendario = "
             "(SELECT id_calendario FROM creditos.credito WHERE cod_credito = %s)",
             hoy_lima() - timedelta(days=dias), numero_cuota, cod_credito)


# ── Lecturas ────────────────────────────────────────────────────────────────


def test_el_credito_desembolsado_se_lee_con_sus_cuotas(api, operador, cobranza, credito):
    cod_credito, _ = credito()
    leido = detalle(api, operador[0], cod_credito)
    assert {k: leido[k] for k in ("codCredito", "estado", "codCliente", "moneda", "montoDesembolsado",
                                   "numeroCuotas", "cuotasPagadas", "cuotasVencidas", "saldoPendiente",
                                   "moraVigente")} == {
        "codCredito": cod_credito, "estado": "AL_DIA", "codCliente": "C001", "moneda": "PEN",
        "montoDesembolsado": "3000.00", "numeroCuotas": 3, "cuotasPagadas": 0, "cuotasVencidas": 0,
        "saldoPendiente": str(DEUDA), "moraVigente": "0.00"}
    assert leido["codigoOrden"].startswith("DES-")
    assert datetime.fromisoformat(leido["fechaDesembolso"]).tzinfo is not None
    assert [(c["numeroCuota"], Decimal(c["cuotaTotal"]), c["estado"], c["diasAtraso"]) for c in leido["cuotas"]] == [
        (n, total, "PENDIENTE", 0) for n, total in enumerate(CUOTAS, start=1)]
    assert leido["proximoVencimiento"] == leido["cuotas"][0]["fechaVencimiento"]
    lista = api.get(BASE, params={"codCliente": "C001", "estado": "AL_DIA"}, headers=cobranza[0])
    assert lista.status_code == 200, lista.text
    assert cod_credito in {c["codCredito"] for c in lista.json()}
    assert all(c["codCliente"] == "C001" and c["estado"] == "AL_DIA" for c in lista.json())
    assert api.get(BASE, params={"estado": "OTRO"}, headers=operador[0]).status_code == 422
    inexistente = api.get(f"{BASE}/CRE-1999-000001", headers=operador[0])
    assert inexistente.status_code == 404
    assert inexistente.json()["error"]["code"] == "CREDITO_NO_ENCONTRADO"


# ── Pagos ───────────────────────────────────────────────────────────────────


def test_un_pago_con_fondos_debita_la_cuenta_y_paga_la_cuota(
        api, autorizacion, operador, credito, consulta):
    cod_credito, num_cuenta = credito()
    antes = saldo(api, autorizacion, num_cuenta)
    correlacion, referencia = str(uuid.uuid4()), nueva_referencia()
    respuesta = api.post(f"{BASE}/{cod_credito}/pagos", json={
        "numCuenta": num_cuenta, "monto": "1030.00", "referencia": referencia},
        headers={**operador[0], "X-Correlation-ID": correlacion})
    assert respuesta.status_code == 201, respuesta.text
    pago = respuesta.json()
    assert {k: pago[k] for k in ("codCredito", "referencia", "estado", "motivo", "monto", "montoAplicado",
                                  "numCuenta", "canal", "aplicaciones", "estadoCredito", "saldoPendiente")} == {
        "codCredito": cod_credito, "referencia": referencia, "estado": "CONFIRMADO", "motivo": None,
        "monto": "1030.00", "montoAplicado": "1030.00", "numCuenta": num_cuenta, "canal": "VEN",
        "aplicaciones": [{"numeroCuota": 1, "montoAplicado": "1030.00"}], "estadoCredito": "AL_DIA",
        "saldoPendiente": str(DEUDA - CUOTAS[0])}
    assert antes - saldo(api, autorizacion, num_cuenta) == Decimal("1030.00")
    assert debitos(consulta, num_cuenta) == [{"uuid": pago["uuidTransaccion"], "monto": Decimal("1030.00")}]
    leido = detalle(api, operador[0], cod_credito)
    assert [c["estado"] for c in leido["cuotas"]] == ["PAGADA", "PENDIENTE", "PENDIENTE"]
    (evento,) = consulta(
        "SELECT actor, BIN_TO_UUID(correlation_id) AS correlacion, resultado, modulo_emisor "
        "FROM creditos.evento_auditoria WHERE id_entidad = %s AND accion = 'REGISTRAR_PAGO'", pago["idPago"])
    assert evento == {"actor": operador[1], "correlacion": correlacion, "resultado": "CONFIRMADO",
                      "modulo_emisor": 14}
    comprobante = api.get(f"{BASE}/pagos/{referencia}", headers=operador[0])
    assert comprobante.status_code == 200, comprobante.text
    assert comprobante.json()["idPago"] == pago["idPago"]
    assert [p["referencia"] for p in api.get(f"{BASE}/{cod_credito}/pagos", headers=operador[0]).json()] == [
        referencia]


def test_el_pago_se_aplica_de_la_cuota_mas_antigua_a_la_mas_reciente(api, operador, credito):
    cod_credito, num_cuenta = credito()
    parcial = pagar(api, operador[0], cod_credito, num_cuenta, "500.00").json()
    assert parcial["aplicaciones"] == [{"numeroCuota": 1, "montoAplicado": "500.00"}]
    assert [c["estado"] for c in detalle(api, operador[0], cod_credito)["cuotas"]] == [
        "PARCIAL", "PENDIENTE", "PENDIENTE"]
    dos = pagar(api, operador[0], cod_credito, num_cuenta, "1500.00", canal="HB").json()
    assert (dos["canal"], sorted((a["numeroCuota"], a["montoAplicado"]) for a in dos["aplicaciones"])) == (
        "HB", [(1, "530.00"), (2, "970.00")])


def test_un_pago_sin_fondos_queda_rechazado_sin_mover_dinero(
        api, autorizacion, operador, credito, abrir_cuenta, consulta):
    cod_credito, _ = credito()
    vacia, referencia = abrir_cuenta(), nueva_referencia()
    respuesta = pagar(api, operador[0], cod_credito, vacia, "1030.00", referencia)
    assert respuesta.status_code == 201, respuesta.text
    pago = respuesta.json()
    assert (pago["estado"], pago["motivo"], pago["montoAplicado"], pago["uuidTransaccion"], pago["aplicaciones"]) == (
        "RECHAZADO", "SALDO_INSUFICIENTE", "0.00", None, [])
    assert pago["saldoPendiente"] == str(DEUDA) and pago["estadoCredito"] == "AL_DIA"
    assert saldo(api, autorizacion, vacia) == 0 and debitos(consulta, vacia) == []
    assert [c["estado"] for c in detalle(api, operador[0], cod_credito)["cuotas"]] == ["PENDIENTE"] * 3
    assert api.get(f"{BASE}/pagos/{referencia}", headers=operador[0]).json()["estado"] == "RECHAZADO"
    # Repetir la referencia de un pago rechazado devuelve el rechazo, aunque la cuenta ya tenga
    # fondos: cada intento nuevo lleva su propia referencia.
    depositar(api, autorizacion, vacia, "2000.00")
    repetido = pagar(api, operador[0], cod_credito, vacia, "1030.00", referencia)
    assert repetido.status_code == 200, repetido.text
    assert (repetido.json()["idPago"], repetido.json()["estado"]) == (pago["idPago"], "RECHAZADO")
    assert debitos(consulta, vacia) == []
    nuevo = pagar(api, operador[0], cod_credito, vacia, "1030.00")
    assert nuevo.json()["estado"] == "CONFIRMADO"


def test_un_pago_con_la_cuenta_bloqueada_queda_rechazado_sin_mover_dinero(
        api, autorizacion, operador, credito, consulta):
    cod_credito, num_cuenta = credito()
    antes = saldo(api, autorizacion, num_cuenta)
    consulta("UPDATE cuentas.cuenta_ahorro SET estado_cuenta = 'BLOQUEADA' WHERE num_cuenta = %s", num_cuenta)
    respuesta = pagar(api, operador[0], cod_credito, num_cuenta, "1030.00")
    assert respuesta.status_code == 201, respuesta.text
    assert (respuesta.json()["estado"], respuesta.json()["motivo"]) == ("RECHAZADO", "CUENTA_NO_OPERATIVA")
    assert num_cuenta not in respuesta.json()["motivo"]
    consulta("UPDATE cuentas.cuenta_ahorro SET estado_cuenta = 'ACTIVA' WHERE num_cuenta = %s", num_cuenta)
    assert saldo(api, autorizacion, num_cuenta) == antes and debitos(consulta, num_cuenta) == []
    assert detalle(api, operador[0], cod_credito)["saldoPendiente"] == str(DEUDA)


def test_la_misma_referencia_devuelve_el_mismo_pago_y_otro_contenido_es_409(
        api, autorizacion, operador, credito, consulta):
    cod_credito, num_cuenta = credito()
    otro_credito, _ = credito()
    referencia = nueva_referencia()
    primero = pagar(api, operador[0], cod_credito, num_cuenta, "1030.00", referencia)
    assert primero.status_code == 201, primero.text
    despues = saldo(api, autorizacion, num_cuenta)
    repetido = pagar(api, operador[0], cod_credito, num_cuenta, "1030.00", referencia)
    assert repetido.status_code == 200, repetido.text
    assert repetido.json() == primero.json()
    assert saldo(api, autorizacion, num_cuenta) == despues and len(debitos(consulta, num_cuenta)) == 1
    for credito_, monto in ((cod_credito, "1030.01"), (otro_credito, "1030.00")):
        conflicto = pagar(api, operador[0], credito_, num_cuenta, monto, referencia)
        assert conflicto.status_code == 409, conflicto.text
        assert conflicto.json()["error"]["code"] == "IDEMPOTENCIA_CONFLICTO"
    assert len(debitos(consulta, num_cuenta)) == 1


def test_pagos_simultaneos_con_la_misma_referencia_debitan_una_vez(
        api, autorizacion, operador, credito, consulta):
    cod_credito, num_cuenta = credito()
    antes, referencia = saldo(api, autorizacion, num_cuenta), nueva_referencia()
    barrera = threading.Barrier(8)

    def intento(_):
        barrera.wait()
        return pagar(api, operador[0], cod_credito, num_cuenta, "1030.00", referencia)

    with ThreadPoolExecutor(8) as hilos:
        respuestas = list(hilos.map(intento, range(8)))
    assert sorted(r.status_code for r in respuestas) == [200] * 7 + [201], [r.text for r in respuestas]
    assert len({r.json()["idPago"] for r in respuestas}) == 1
    assert len(debitos(consulta, num_cuenta)) == 1
    assert antes - saldo(api, autorizacion, num_cuenta) == Decimal("1030.00")


def test_dos_pagos_simultaneos_sin_fondos_para_ambos_cobran_uno(
        api, autorizacion, operador, credito, abrir_cuenta, consulta):
    cod_credito, _ = credito()
    cuenta = abrir_cuenta()
    depositar(api, autorizacion, cuenta, "1030.00")
    barrera = threading.Barrier(2)

    def intento(_):
        barrera.wait()
        return pagar(api, operador[0], cod_credito, cuenta, "1030.00")

    with ThreadPoolExecutor(2) as hilos:
        respuestas = list(hilos.map(intento, range(2)))
    assert [r.status_code for r in respuestas] == [201, 201], [r.text for r in respuestas]
    assert sorted((r.json()["estado"], r.json()["motivo"]) for r in respuestas) == [
        ("CONFIRMADO", None), ("RECHAZADO", "SALDO_INSUFICIENTE")]
    assert saldo(api, autorizacion, cuenta) == 0 and len(debitos(consulta, cuenta)) == 1
    leido = detalle(api, operador[0], cod_credito)
    assert leido["saldoPendiente"] == str(DEUDA - CUOTAS[0])
    assert [c["estado"] for c in leido["cuotas"]] == ["PAGADA", "PENDIENTE", "PENDIENTE"]


def test_reintenta_el_pago_tras_un_deadlock(api, operador, credito, fallar_una_vez, consulta):
    from COREDB.services import creditos

    cod_credito, num_cuenta = credito()
    intentos = fallar_una_vez(creditos, 1213)
    respuesta = pagar(api, operador[0], cod_credito, num_cuenta, "1030.00")
    assert respuesta.status_code == 201, respuesta.text
    assert intentos.count("creditos.registrar_pago_cuota") == 2
    assert len(debitos(consulta, num_cuenta)) == 1


def test_pagos_que_no_se_admiten_no_dejan_rastro(api, operador, credito, abrir_cuenta, consulta):
    cod_credito, num_cuenta = credito()
    casos = [
        (cod_credito, num_cuenta, str(DEUDA + Decimal("0.01")), 422, "PAGO_NO_ADMITIDO"),
        (cod_credito, abrir_cuenta(titular="C002"), "100.00", 422, "CUENTA_NO_ELEGIBLE"),
        (cod_credito, abrir_cuenta("USD"), "100.00", 422, "CUENTA_NO_ELEGIBLE"),
        ("CRE-1999-000001", num_cuenta, "100.00", 404, "CREDITO_NO_ENCONTRADO"),
    ]
    for credito_, cuenta, monto, estado, codigo in casos:
        referencia = nueva_referencia()
        respuesta = pagar(api, operador[0], credito_, cuenta, monto, referencia)
        assert (respuesta.status_code, respuesta.json()["error"]["code"]) == (estado, codigo), respuesta.text
        assert cuenta not in respuesta.text and "C001" not in respuesta.text and monto not in respuesta.text
        assert api.get(f"{BASE}/pagos/{referencia}", headers=operador[0]).status_code == 404
    assert not consulta("SELECT 1 FROM creditos.pago WHERE cod_credito = %s", cod_credito)


def test_pagar_toda_la_deuda_cancela_el_credito(api, autorizacion, operador, credito):
    cod_credito, num_cuenta = credito()
    # El abono fue de 3000.00 y la deuda, con intereses, es de 3060.00.
    depositar(api, autorizacion, num_cuenta, DEUDA - Decimal("3000.00"))
    pago = pagar(api, operador[0], cod_credito, num_cuenta, str(DEUDA)).json()
    assert (pago["estado"], pago["estadoCredito"], pago["saldoPendiente"]) == ("CONFIRMADO", "CANCELADO", "0.00")
    leido = detalle(api, operador[0], cod_credito)
    assert (leido["estado"], leido["cuotasPagadas"], leido["proximoVencimiento"]) == ("CANCELADO", 3, None)
    otro = pagar(api, operador[0], cod_credito, num_cuenta, "1.00")
    assert (otro.status_code, otro.json()["error"]["code"]) == (422, "CREDITO_NO_ADMITIDO")


def test_un_pago_inexistente(api, operador):
    respuesta = api.get(f"{BASE}/pagos/{nueva_referencia()}", headers=operador[0])
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["code"] == "PAGO_NO_ENCONTRADO"


# ── Vencimientos y mora (tarea diaria de svc-cobranza) ──────────────────────


def test_la_tarea_diaria_de_svc_cobranza_vence_cuotas_y_registra_mora(
        api, operador, cobranza, credito, consulta):
    cod_credito, num_cuenta = credito()
    al_dia, _ = credito()
    vencer_cuota(consulta, cod_credito, 1, dias=3)

    corrida = api.post(f"{BASE}/vencimientos", json={}, headers=cobranza[0])
    assert corrida.status_code == 200, corrida.text
    assert corrida.json()["fecha"] == hoy_lima().isoformat()
    assert corrida.json()["cuotasVencidas"] >= 1 and corrida.json()["creditosActualizados"] >= 1
    leido = detalle(api, operador[0], cod_credito)
    assert (leido["estado"], leido["cuotasVencidas"]) == ("EN_MORA", 1)
    assert [(c["estado"], c["diasAtraso"]) for c in leido["cuotas"]] == [
        ("VENCIDA", 3), ("PENDIENTE", 0), ("PENDIENTE", 0)]
    assert detalle(api, operador[0], al_dia)["estado"] == "AL_DIA"
    eventos = consulta("SELECT accion, resultado, actor FROM creditos.evento_auditoria WHERE id_entidad IN (%s, %s)",
                       cod_credito, f"{cod_credito}:1")
    assert {(e["accion"], e["resultado"], e["actor"]) for e in eventos} >= {
        ("VENCER_CUOTA", "VENCIDA", cobranza[1]), ("ACTUALIZAR_ESTADO", "EN_MORA", cobranza[1])}
    # Correrla otra vez el mismo día no cambia nada de este crédito.
    assert api.post(f"{BASE}/vencimientos", json={}, headers=cobranza[0]).status_code == 200
    assert detalle(api, operador[0], cod_credito)["estado"] == "EN_MORA"

    ruta_mora = f"{BASE}/{cod_credito}/cuotas/1/mora"
    primera = api.post(ruta_mora, json={"montoCalculado": "12.50"}, headers=cobranza[0])
    assert primera.status_code == 201, primera.text
    assert {k: primera.json()[k] for k in ("codCredito", "numeroCuota", "montoCalculado", "diasAtraso",
                                            "vigente")} == {
        "codCredito": cod_credito, "numeroCuota": 1, "montoCalculado": "12.50", "diasAtraso": 3, "vigente": True}
    segunda = api.post(ruta_mora, json={"montoCalculado": "15.00"}, headers=cobranza[0])
    assert segunda.status_code == 201, segunda.text
    historial = api.get(ruta_mora, headers=operador[0])
    assert historial.status_code == 200, historial.text
    assert [(m["montoCalculado"], m["vigente"]) for m in historial.json()] == [("15.00", True), ("12.50", False)]
    leido = detalle(api, operador[0], cod_credito)
    assert (leido["moraVigente"], leido["cuotas"][0]["moraVigente"]) == ("15.00", "15.00")

    # Pagar la cuota vencida devuelve el crédito a AL_DIA; la mora no se cobra (decisión 5).
    pago = pagar(api, operador[0], cod_credito, num_cuenta, "1030.00").json()
    assert (pago["estado"], pago["estadoCredito"], pago["montoAplicado"]) == ("CONFIRMADO", "AL_DIA", "1030.00")
    assert detalle(api, operador[0], cod_credito)["moraVigente"] == "0.00"


def test_los_vencimientos_no_admiten_una_fecha_futura(api, cobranza):
    manana = api.post(f"{BASE}/vencimientos", json={"fecha": (hoy_lima() + timedelta(days=1)).isoformat()},
                      headers=cobranza[0])
    assert manana.status_code == 422
    assert manana.json()["error"]["code"] == "FECHA_NO_ADMITIDA"
    ayer = api.post(f"{BASE}/vencimientos", json={"fecha": (hoy_lima() - timedelta(days=1)).isoformat()},
                    headers=cobranza[0])
    assert ayer.status_code == 200, ayer.text
    assert ayer.json()["fecha"] == (hoy_lima() - timedelta(days=1)).isoformat()
    sin_cuerpo = api.post(f"{BASE}/vencimientos", headers=cobranza[0])
    assert sin_cuerpo.status_code == 200, sin_cuerpo.text


def test_la_mora_solo_se_registra_en_una_cuota_vencida_con_saldo(api, cobranza, credito):
    cod_credito, _ = credito()
    al_dia = api.post(f"{BASE}/{cod_credito}/cuotas/1/mora", json={"montoCalculado": "5.00"}, headers=cobranza[0])
    assert (al_dia.status_code, al_dia.json()["error"]["code"]) == (422, "CUOTA_NO_ADMITIDA")
    no_existe = api.post(f"{BASE}/{cod_credito}/cuotas/9/mora", json={"montoCalculado": "5.00"},
                         headers=cobranza[0])
    assert (no_existe.status_code, no_existe.json()["error"]["code"]) == (422, "CUOTA_NO_ADMITIDA")
    negativa = api.post(f"{BASE}/{cod_credito}/cuotas/1/mora", json={"montoCalculado": "-1"}, headers=cobranza[0])
    assert negativa.status_code == 422
    sin_credito = api.post(f"{BASE}/CRE-1999-000001/cuotas/1/mora", json={"montoCalculado": "5.00"},
                           headers=cobranza[0])
    assert (sin_credito.status_code, sin_credito.json()["error"]["code"]) == (404, "CREDITO_NO_ENCONTRADO")


# ── Conciliación y permisos ─────────────────────────────────────────────────


def test_conciliacion_de_pagos(api, autorizacion, operador, credito, abrir_cuenta):
    cod_credito, num_cuenta = credito()
    assert pagar(api, operador[0], cod_credito, num_cuenta, "1030.00").json()["estado"] == "CONFIRMADO"
    assert pagar(api, operador[0], cod_credito, abrir_cuenta(), "10.00").json()["estado"] == "RECHAZADO"
    respuesta = api.get(f"{BASE}/conciliacion/pagos", params={"fecha": hoy_lima().isoformat()},
                        headers=autorizacion)
    assert respuesta.status_code == 200, respuesta.text
    (fila,) = [f for f in respuesta.json() if f["canal"] == "VEN" and f["moneda"] == "PEN"]
    assert fila["fecha"] == hoy_lima().isoformat()
    assert fila["pagosConfirmados"] >= 1 and fila["pagosRechazados"] >= 1
    assert fila["importeCobrado"] == fila["importeAplicado"]
    assert api.get(f"{BASE}/conciliacion/pagos", headers=operador[0]).status_code == 403


def test_permisos_de_la_cobranza(api, operador, cobranza, analista, sesion_de, credito):
    cod_credito, num_cuenta = credito()
    cuerpo = {"numCuenta": num_cuenta, "monto": "1.00", "referencia": nueva_referencia()}
    assert api.post(f"{BASE}/{cod_credito}/pagos", json=cuerpo).status_code == 401
    asesor, _ = sesion_de("ASESOR")
    auditor, _ = sesion_de("AUDITOR")
    for encabezados in (analista, asesor, auditor, cobranza[0]):
        respuesta = api.post(f"{BASE}/{cod_credito}/pagos", json=cuerpo, headers=encabezados)
        assert respuesta.status_code == 403
        assert respuesta.json()["error"]["code"] == "PERMISO_DENEGADO"
    for encabezados in (operador[0], analista, auditor):
        assert api.post(f"{BASE}/vencimientos", json={}, headers=encabezados).status_code == 403
        assert api.post(f"{BASE}/{cod_credito}/cuotas/1/mora", json={"montoCalculado": "1.00"},
                        headers=encabezados).status_code == 403
    for encabezados in (auditor, asesor, analista, cobranza[0]):
        assert api.get(f"{BASE}/{cod_credito}", headers=encabezados).status_code == 200
        assert api.get(f"{BASE}/{cod_credito}/pagos", headers=encabezados).status_code == 200
