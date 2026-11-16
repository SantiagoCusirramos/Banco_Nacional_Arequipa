"""Créditos, área de desembolso (CONTRATO_CREDITOS.md §4) contra la base real."""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from creditos_apoyo import BASE, calendario, empleado, expediente, sesion_servicio, usuario_con_empleado
from fastapi.testclient import TestClient

from COREDB.main import app

DOCUMENTO_C001 = "70000001"
DOCUMENTO_C002 = "70000002"


@pytest.fixture
def api():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def servicio(autorizacion, datos_base):
    return sesion_servicio(autorizacion, "EVALUACION")


@pytest.fixture(scope="module")
def servicio_desembolso(autorizacion, datos_base):
    return sesion_servicio(autorizacion, "DESEMBOLSO")


@pytest.fixture(scope="module")
def analista(autorizacion, admin, datos_base):
    id_empleado = empleado(admin)
    registrado = TestClient(app).post(f"{BASE}/analistas", json={"idEmpleado": str(id_empleado)},
                                      headers=autorizacion)
    assert registrado.status_code == 201, registrado.text
    return usuario_con_empleado(autorizacion, "ANALISTA", id_empleado)


@pytest.fixture(scope="module")
def operador(autorizacion, datos_base):
    """(encabezados, username) de un OPERADOR de ventanilla."""
    api = TestClient(app)
    username, password = "u" + uuid.uuid4().hex[:12], "clave-de-un-usuario-1"
    creado = api.post("/coredb/usuarios", headers=autorizacion, json={
        "username": username, "nombre": "Operador", "password": password, "rol": "OPERADOR"})
    assert creado.status_code == 201, creado.text
    login = api.post("/coredb/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, username


def aprobada(api, servicio, analista, cod_cliente="C001", monto="15000.00", plazo=12, inicio=None):
    """Una solicitud aprobada por la regla (R-A): (idSolicitud, idEvaluacion)."""
    cuerpo = expediente(monto=monto, plazo=plazo, cod_cliente=cod_cliente)
    if inicio is not None:
        cuerpo["calendario"] = calendario(monto, plazo, inicio=inicio)
    registrada = api.post(f"{BASE}/solicitudes", json=cuerpo, headers=servicio[0])
    assert registrada.status_code == 201, registrada.text
    evaluada = api.post(f"{BASE}/solicitudes/{cuerpo['idSolicitud']}/evaluaciones", headers=analista, json={
        "versionSolicitud": 1, "ingresoMensual": "50000.00", "deudaMensual": "0.00", "riesgo": "BUENO",
        "verificada": True})
    assert evaluada.status_code == 200, evaluada.text
    assert evaluada.json()["resultado"] == "APROBADO"
    return cuerpo["idSolicitud"], evaluada.json()["idEvaluacion"]


def preparar(api, encabezados, id_evaluacion, num_cuenta, llave=None, **cambios):
    cuerpo = {"idEvaluacion": id_evaluacion, "numCuenta": num_cuenta, **cambios}
    return api.post(f"{BASE}/ordenes", json=cuerpo,
                    headers={**encabezados, "X-Idempotency-Key": str(llave or uuid.uuid4())})


def verificar_documento(api, encabezados, documento=DOCUMENTO_C001, verificada=True):
    respuesta = api.post("/coredb/clientes/validaciones/documento", headers=encabezados, json={
        "tipo_documento": "DNI", "numero_documento": documento, "identidad_verificada": verificada})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def validar_identidad(api, encabezados, id_orden, documento=DOCUMENTO_C001):
    verificacion = verificar_documento(api, encabezados, documento)
    return api.post(f"{BASE}/ordenes/{id_orden}/validaciones", headers=encabezados, json={
        "tipo": "IDENTIDAD", "resultado": "APROBADA", "referenciaEvidencia": str(verificacion["id_validacion"])})


def orden_validada(api, servicio, analista, operador, abrir_cuenta, **datos):
    id_solicitud, id_evaluacion = aprobada(api, servicio, analista, **datos)
    num_cuenta = abrir_cuenta()
    orden = preparar(api, operador[0], id_evaluacion, num_cuenta)
    assert orden.status_code == 201, orden.text
    validada = validar_identidad(api, operador[0], orden.json()["idOrden"])
    assert validada.status_code == 201, validada.text
    assert validada.json()["estado"] == "VALIDADA"
    return id_solicitud, orden.json(), num_cuenta


def saldo(api, autorizacion, num_cuenta):
    respuesta = api.get(f"/coredb/cuentas/{num_cuenta}", headers=autorizacion)
    assert respuesta.status_code == 200, respuesta.text
    return Decimal(respuesta.json()["saldo_disponible"])


def hoy_lima():
    return (datetime.now(timezone.utc) - timedelta(hours=5)).date()


# ── Preparación ─────────────────────────────────────────────────────────────


def test_prepara_la_orden_de_una_aprobacion(api, servicio, analista, operador, abrir_cuenta, consulta):
    id_solicitud, id_evaluacion = aprobada(api, servicio, analista)
    num_cuenta = abrir_cuenta()
    correlacion = str(uuid.uuid4())
    respuesta = api.post(f"{BASE}/ordenes", json={"idEvaluacion": id_evaluacion, "numCuenta": num_cuenta},
                         headers={**operador[0], "X-Idempotency-Key": str(uuid.uuid4()),
                                  "X-Correlation-ID": correlacion})
    assert respuesta.status_code == 201, respuesta.text
    orden = respuesta.json()
    assert orden["codigoOrden"].startswith(f"DES-{hoy_lima().year}-") and len(orden["codigoOrden"]) == 15
    assert {k: orden[k] for k in ("estado", "importe", "moneda", "numCuenta", "canal", "idEvaluacion",
                                   "idSolicitud", "codCliente", "codCredito", "uuidTransaccionAbono")} == {
        "estado": "PREPARADA", "importe": "15000.00", "moneda": "PEN", "numCuenta": num_cuenta, "canal": "VEN",
        "idEvaluacion": id_evaluacion, "idSolicitud": id_solicitud, "codCliente": "C001", "codCredito": None,
        "uuidTransaccionAbono": None}
    (evento,) = consulta(
        "SELECT actor, BIN_TO_UUID(correlation_id) AS correlacion, modulo_emisor FROM creditos.evento_auditoria "
        "WHERE id_entidad = %s AND accion = 'PREPARAR_ORDEN'", orden["idOrden"])
    assert evento == {"actor": operador[1], "correlacion": correlacion, "modulo_emisor": 13}
    validaciones = api.get(f"{BASE}/ordenes/{orden['idOrden']}", headers=operador[0]).json()["validaciones"]
    assert [(v["tipo"], v["resultado"]) for v in validaciones] == [("CUENTA", "APROBADA")]


def test_la_misma_llave_devuelve_la_misma_orden_y_otro_contenido_es_409(
        api, servicio, analista, operador, abrir_cuenta, consulta):
    _, id_evaluacion = aprobada(api, servicio, analista)
    num_cuenta, llave = abrir_cuenta(), uuid.uuid4()
    primera = preparar(api, operador[0], id_evaluacion, num_cuenta, llave)
    assert primera.status_code == 201, primera.text
    repetida = preparar(api, operador[0], id_evaluacion, num_cuenta, llave)
    assert repetida.status_code == 200, repetida.text
    assert repetida.json()["idOrden"] == primera.json()["idOrden"]
    otra = preparar(api, operador[0], id_evaluacion, num_cuenta, llave, canal="HB")
    assert otra.status_code == 409
    assert otra.json()["error"]["code"] == "IDEMPOTENCIA_CONFLICTO"
    (fila,) = consulta("SELECT count(*) AS n FROM creditos.orden_desembolso WHERE id_evaluacion = UUID_TO_BIN(%s)",
                       id_evaluacion)
    assert fila["n"] == 1


@pytest.mark.parametrize("llave", [None, "no-es-uuid"])
def test_preparar_exige_una_llave_uuid(api, operador, llave):
    cabeceras = dict(operador[0]) | ({} if llave is None else {"X-Idempotency-Key": llave})
    respuesta = api.post(f"{BASE}/ordenes", json={"idEvaluacion": str(uuid.uuid4()), "numCuenta": "CTA-1"},
                         headers=cabeceras)
    assert respuesta.status_code == 422


def test_sin_aprobacion_vigente_no_hay_orden(api, servicio, analista, operador, abrir_cuenta):
    num_cuenta = abrir_cuenta()
    inexistente = preparar(api, operador[0], str(uuid.uuid4()), num_cuenta)
    assert inexistente.status_code == 422
    assert inexistente.json()["error"]["code"] == "APROBACION_NO_VIGENTE"
    cuerpo = expediente()
    api.post(f"{BASE}/solicitudes", json=cuerpo, headers=servicio[0])
    observada = api.post(f"{BASE}/solicitudes/{cuerpo['idSolicitud']}/evaluaciones", headers=analista, json={
        "versionSolicitud": 1, "ingresoMensual": "4000.00", "deudaMensual": "0.00", "riesgo": "BUENO",
        "verificada": True}).json()
    assert observada["resultado"] == "OBSERVADO"
    respuesta = preparar(api, operador[0], observada["idEvaluacion"], num_cuenta)
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "APROBACION_NO_VIGENTE"


def test_una_aprobacion_tiene_una_sola_orden_abierta(api, servicio, analista, operador, abrir_cuenta):
    _, id_evaluacion = aprobada(api, servicio, analista)
    num_cuenta = abrir_cuenta()
    assert preparar(api, operador[0], id_evaluacion, num_cuenta).status_code == 201
    segunda = preparar(api, operador[0], id_evaluacion, num_cuenta)
    assert segunda.status_code == 422
    assert segunda.json()["error"]["code"] == "ORDEN_NO_ADMITIDA"


@pytest.mark.parametrize("cuenta", ["otro_titular", "otra_moneda", "inexistente"])
def test_la_cuenta_debe_ser_elegible(api, servicio, analista, operador, abrir_cuenta, cuenta):
    _, id_evaluacion = aprobada(api, servicio, analista)
    num_cuenta = {"otro_titular": lambda: abrir_cuenta(titular="C002"),
                  "otra_moneda": lambda: abrir_cuenta("USD"),
                  "inexistente": lambda: "CTA-NO-EXISTE"}[cuenta]()
    respuesta = preparar(api, operador[0], id_evaluacion, num_cuenta)
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "CUENTA_NO_ELEGIBLE"
    assert num_cuenta not in respuesta.text and "C001" not in respuesta.text


def test_no_se_prepara_si_la_primera_cuota_ya_vencio(api, servicio, analista, operador, abrir_cuenta):
    _, id_evaluacion = aprobada(api, servicio, analista, inicio=date.today() - timedelta(days=1))
    respuesta = preparar(api, operador[0], id_evaluacion, abrir_cuenta())
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "CALENDARIO_INVALIDO"


# ── Validaciones y cuenta ───────────────────────────────────────────────────


def test_la_identidad_verificada_hoy_valida_la_orden(api, servicio, analista, operador, abrir_cuenta, consulta):
    _, orden, _ = orden_validada(api, servicio, analista, operador, abrir_cuenta)
    detalle = api.get(f"{BASE}/ordenes/{orden['idOrden']}", headers=operador[0]).json()
    assert detalle["estado"] == "VALIDADA"
    assert [v["tipo"] for v in detalle["validaciones"]] == ["CUENTA", "IDENTIDAD"]
    assert [e["accion"] for e in detalle["eventos"]] == ["PREPARAR_ORDEN", "VALIDAR_ORDEN"]


@pytest.mark.parametrize("evidencia", ["otro_cliente", "rechazada", "texto"])
def test_la_evidencia_de_identidad_debe_ser_del_titular_y_aprobada(
        api, servicio, analista, operador, abrir_cuenta, evidencia):
    _, id_evaluacion = aprobada(api, servicio, analista)
    orden = preparar(api, operador[0], id_evaluacion, abrir_cuenta()).json()
    referencia = {
        "otro_cliente": lambda: str(verificar_documento(api, operador[0], DOCUMENTO_C002)["id_validacion"]),
        "rechazada": lambda: str(verificar_documento(api, operador[0], verificada=False)["id_validacion"]),
        "texto": lambda: "DNI verificado",
    }[evidencia]()
    respuesta = api.post(f"{BASE}/ordenes/{orden['idOrden']}/validaciones", headers=operador[0], json={
        "tipo": "IDENTIDAD", "resultado": "APROBADA", "referenciaEvidencia": referencia})
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "VALIDACION_NO_ADMITIDA"


def test_una_validacion_rechazada_devuelve_la_orden_a_preparada(api, servicio, analista, operador, abrir_cuenta):
    _, orden, _ = orden_validada(api, servicio, analista, operador, abrir_cuenta)
    respuesta = api.post(f"{BASE}/ordenes/{orden['idOrden']}/validaciones", headers=operador[0], json={
        "tipo": "ANTIFRAUDE", "resultado": "RECHAZADA", "referenciaEvidencia": "ALERTA-1",
        "detalle": "Operación inusual"})
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["estado"] == "PREPARADA"


def test_cambiar_la_cuenta_de_una_orden(api, servicio, analista, operador, abrir_cuenta):
    _, orden, _ = orden_validada(api, servicio, analista, operador, abrir_cuenta)
    nueva = abrir_cuenta()
    respuesta = api.put(f"{BASE}/ordenes/{orden['idOrden']}/cuenta", headers=operador[0], json={"numCuenta": nueva})
    assert respuesta.status_code == 200, respuesta.text
    # La identidad sigue aprobada: con la validación CUENTA nueva, la orden sigue VALIDADA.
    assert (respuesta.json()["numCuenta"], respuesta.json()["estado"]) == (nueva, "VALIDADA")
    ajena = abrir_cuenta(titular="C002")
    rechazo = api.put(f"{BASE}/ordenes/{orden['idOrden']}/cuenta", headers=operador[0], json={"numCuenta": ajena})
    assert rechazo.status_code == 422
    assert rechazo.json()["error"]["code"] == "CUENTA_NO_ELEGIBLE"
    inexistente = api.put(f"{BASE}/ordenes/{uuid.uuid4()}/cuenta", headers=operador[0], json={"numCuenta": nueva})
    assert inexistente.status_code == 404
    assert inexistente.json()["error"]["code"] == "ORDEN_NO_ENCONTRADA"


# ── Confirmación ────────────────────────────────────────────────────────────


def test_no_se_confirma_una_orden_sin_validar(api, servicio, analista, operador, abrir_cuenta):
    _, id_evaluacion = aprobada(api, servicio, analista)
    orden = preparar(api, operador[0], id_evaluacion, abrir_cuenta()).json()
    respuesta = api.post(f"{BASE}/ordenes/{orden['idOrden']}/confirmacion", headers=operador[0])
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "ORDEN_NO_ADMITIDA"
    inexistente = api.post(f"{BASE}/ordenes/{uuid.uuid4()}/confirmacion", headers=operador[0])
    assert inexistente.status_code == 404


def test_confirmar_abona_crea_el_credito_y_desembolsa_la_solicitud(
        api, autorizacion, servicio, analista, operador, abrir_cuenta, consulta):
    id_solicitud, orden, num_cuenta = orden_validada(api, servicio, analista, operador, abrir_cuenta)
    antes = saldo(api, autorizacion, num_cuenta)
    respuesta = api.post(f"{BASE}/ordenes/{orden['idOrden']}/confirmacion", headers=operador[0])
    assert respuesta.status_code == 201, respuesta.text
    confirmada = respuesta.json()
    assert confirmada["estado"] == "CONFIRMADA" and confirmada["codigoOrden"] == orden["codigoOrden"]
    assert confirmada["codCredito"].startswith(f"CRE-{hoy_lima().year}-")
    assert datetime.fromisoformat(confirmada["fechaEfectiva"]).tzinfo is not None
    assert saldo(api, autorizacion, num_cuenta) - antes == Decimal("15000.00")
    (movimiento,) = consulta(
        "SELECT BIN_TO_UUID(uuid_transaccion) AS uuid, tipo_operacion, monto, id_canal FROM cuentas.movimiento "
        "WHERE num_cuenta = %s", num_cuenta)
    assert movimiento == {"uuid": confirmada["uuidTransaccionAbono"], "tipo_operacion": "DESEMBOLSO",
                          "monto": Decimal("15000.00"), "id_canal": "VEN"}

    solicitud = api.get(f"{BASE}/solicitudes/{id_solicitud}", headers=operador[0]).json()
    assert solicitud["estado"] == "DESEMBOLSADA"
    assert solicitud["calendario"]["tipo"] == "OFICIAL"
    assert api.get(f"{BASE}/aprobaciones", params={"idSolicitud": id_solicitud}, headers=operador[0]).json() == []
    detalle = api.get(f"{BASE}/ordenes/{orden['idOrden']}", headers=operador[0]).json()
    assert (detalle["codCredito"], detalle["usuarioConfirmacion"]) == (confirmada["codCredito"], operador[1])
    assert detalle["eventos"][-1]["accion"] == "CONFIRMAR_ORDEN"


def test_repetir_la_confirmacion_no_abona_otra_vez(api, autorizacion, servicio, analista, operador, abrir_cuenta,
                                                   consulta):
    _, orden, num_cuenta = orden_validada(api, servicio, analista, operador, abrir_cuenta)
    primera = api.post(f"{BASE}/ordenes/{orden['idOrden']}/confirmacion", headers=operador[0])
    assert primera.status_code == 201, primera.text
    despues = saldo(api, autorizacion, num_cuenta)
    repetida = api.post(f"{BASE}/ordenes/{orden['idOrden']}/confirmacion", headers=operador[0])
    assert repetida.status_code == 200, repetida.text
    assert repetida.json() == primera.json()
    assert saldo(api, autorizacion, num_cuenta) == despues
    (fila,) = consulta("SELECT count(*) AS n FROM cuentas.movimiento WHERE num_cuenta = %s", num_cuenta)
    assert fila["n"] == 1


def test_reintenta_la_confirmacion_tras_un_deadlock(api, servicio, analista, operador, abrir_cuenta,
                                                    fallar_una_vez, consulta):
    from COREDB.services import creditos

    _, orden, num_cuenta = orden_validada(api, servicio, analista, operador, abrir_cuenta)
    intentos = fallar_una_vez(creditos, 1213)
    respuesta = api.post(f"{BASE}/ordenes/{orden['idOrden']}/confirmacion", headers=operador[0])
    assert respuesta.status_code == 201, respuesta.text
    assert intentos.count("creditos.confirmar_orden") == 2
    (fila,) = consulta("SELECT count(*) AS n FROM cuentas.movimiento WHERE num_cuenta = %s", num_cuenta)
    assert fila["n"] == 1


# ── Rechazo ─────────────────────────────────────────────────────────────────


def test_rechazar_una_orden_deja_libre_la_aprobacion(api, servicio, analista, operador, abrir_cuenta):
    _, id_evaluacion = aprobada(api, servicio, analista)
    num_cuenta = abrir_cuenta()
    orden = preparar(api, operador[0], id_evaluacion, num_cuenta).json()
    respuesta = api.post(f"{BASE}/ordenes/{orden['idOrden']}/rechazo", headers=operador[0],
                         json={"motivo": "El cliente desiste"})
    assert respuesta.status_code == 200, respuesta.text
    assert (respuesta.json()["estado"], respuesta.json()["motivoRechazo"]) == ("RECHAZADA", "El cliente desiste")
    confirmar = api.post(f"{BASE}/ordenes/{orden['idOrden']}/confirmacion", headers=operador[0])
    assert confirmar.status_code == 422
    otra_vez = api.post(f"{BASE}/ordenes/{orden['idOrden']}/rechazo", headers=operador[0], json={"motivo": "Otra"})
    assert otra_vez.status_code == 422
    assert otra_vez.json()["error"]["code"] == "ORDEN_NO_ADMITIDA"
    assert preparar(api, operador[0], id_evaluacion, num_cuenta).status_code == 201


def test_rechazar_exige_motivo(api, operador):
    respuesta = api.post(f"{BASE}/ordenes/{uuid.uuid4()}/rechazo", headers=operador[0], json={"motivo": ""})
    assert respuesta.status_code == 422


# ── Monitor y conciliación ──────────────────────────────────────────────────


def test_monitor_de_ordenes(api, servicio, analista, operador, servicio_desembolso, abrir_cuenta):
    _, id_evaluacion = aprobada(api, servicio, analista, cod_cliente="C002")
    orden = preparar(api, operador[0], id_evaluacion, abrir_cuenta(titular="C002")).json()
    lista = api.get(f"{BASE}/ordenes", params={"codCliente": "C002", "estado": "PREPARADA"},
                    headers=servicio_desembolso[0])
    assert lista.status_code == 200, lista.text
    assert orden["idOrden"] in {o["idOrden"] for o in lista.json()}
    assert all(o["codCliente"] == "C002" and o["estado"] == "PREPARADA" for o in lista.json())
    assert api.get(f"{BASE}/ordenes", params={"estado": "OTRO"}, headers=operador[0]).status_code == 422
    inexistente = api.get(f"{BASE}/ordenes/{uuid.uuid4()}", headers=operador[0])
    assert inexistente.status_code == 404
    assert inexistente.json()["error"]["code"] == "ORDEN_NO_ENCONTRADA"


def test_conciliacion_de_desembolsos(api, autorizacion, servicio, analista, operador, abrir_cuenta):
    _, orden, _ = orden_validada(api, servicio, analista, operador, abrir_cuenta)
    assert api.post(f"{BASE}/ordenes/{orden['idOrden']}/confirmacion", headers=operador[0]).status_code == 201
    respuesta = api.get(f"{BASE}/conciliacion/desembolsos", params={"fecha": hoy_lima().isoformat()},
                        headers=autorizacion)
    assert respuesta.status_code == 200, respuesta.text
    (fila,) = [f for f in respuesta.json() if f["moneda"] == "PEN"]
    assert fila["fecha"] == hoy_lima().isoformat()
    assert fila["ordenesConfirmadas"] >= 1 and fila["ordenesSinAbono"] == 0
    assert fila["importeOrdenes"] == fila["importeAbonado"]
    assert api.get(f"{BASE}/conciliacion/desembolsos", headers=operador[0]).status_code == 403


# ── Permisos ────────────────────────────────────────────────────────────────


def test_permisos_del_desembolso(api, servicio, analista, servicio_desembolso, sesion_de):
    cuerpo = {"idEvaluacion": str(uuid.uuid4()), "numCuenta": "CTA-1"}
    llave = {"X-Idempotency-Key": str(uuid.uuid4())}
    assert api.post(f"{BASE}/ordenes", json=cuerpo, headers=llave).status_code == 401
    asesor, _ = sesion_de("ASESOR")
    for encabezados in (analista, asesor, servicio_desembolso[0], servicio[0]):
        respuesta = api.post(f"{BASE}/ordenes", json=cuerpo, headers={**encabezados, **llave})
        assert respuesta.status_code == 403
        assert respuesta.json()["error"]["code"] == "PERMISO_DENEGADO"
    assert api.get(f"{BASE}/ordenes", headers=servicio_desembolso[0]).status_code == 200
    assert api.get(f"{BASE}/aprobaciones", headers=servicio_desembolso[0]).status_code == 200


def test_el_operador_verifica_el_documento(api, operador):
    assert verificar_documento(api, operador[0])["resultado"] == "APROBADO"
