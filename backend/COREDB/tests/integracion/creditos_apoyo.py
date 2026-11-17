"""Ayudas compartidas por las pruebas de créditos contra la base real."""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi.testclient import TestClient

from COREDB.main import app

CENTIMO = Decimal("0.01")
BASE = "/coredb/creditos"
DOCUMENTO_C001 = "70000001"
DOCUMENTO_C002 = "70000002"


def sesion_servicio(autorizacion, modulo):
    api = TestClient(app)
    creado = api.post(
        "/coredb/usuarios/servicios",
        json={"modulo": modulo, "username": "svc-" + uuid.uuid4().hex[:10], "nombre": modulo.title()},
        headers=autorizacion,
    )
    assert creado.status_code == 201, creado.text
    cuerpo = creado.json()
    login = api.post("/coredb/auth/login",
                     json={"username": cuerpo["usuario"]["username"], "password": cuerpo["secreto"]})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, cuerpo["usuario"]["username"]


def empleado(admin, cargo="ANALISTA"):
    codigo = "E" + uuid.uuid4().hex[:10].upper()
    id_empleado = uuid.uuid4()
    with admin.cursor() as cursor:
        cursor.execute(
            "INSERT INTO core.empleado (id_empleado, codigo_empleado, nombre_completo, cargo) "
            "VALUES (%s, %s, 'Analista de pruebas', %s)", (id_empleado.bytes, codigo, cargo))
    return id_empleado


def usuario_con_empleado(autorizacion, rol, id_empleado):
    api = TestClient(app)
    username, password = "u" + uuid.uuid4().hex[:12], "clave-de-un-usuario-1"
    creado = api.post("/coredb/usuarios", headers=autorizacion, json={
        "username": username, "nombre": "N", "password": password, "rol": rol,
        "id_empleado": str(id_empleado)})
    assert creado.status_code == 201, creado.text
    login = api.post("/coredb/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def calendario(monto, plazo, inicio=None):
    """Un calendario coherente: amortización constante y 1 % de interés mensual."""
    inicio = inicio or date.today() + timedelta(days=40)
    monto = Decimal(monto)
    amortizacion = (monto / plazo).quantize(CENTIMO, rounding=ROUND_HALF_UP)
    saldo, cuotas = monto, []
    for n in range(1, plazo + 1):
        capital = saldo if n == plazo else amortizacion
        interes = (saldo * Decimal("0.01")).quantize(CENTIMO, rounding=ROUND_HALF_UP)
        cuotas.append({
            "numeroCuota": n, "fechaVencimiento": (inicio + timedelta(days=30 * (n - 1))).isoformat(),
            "saldoInicial": str(saldo), "amortizacion": str(capital), "interes": str(interes),
            "cuotaTotal": str(capital + interes), "saldoFinal": str(saldo - capital),
        })
        saldo -= capital
    return {"metodo": "FRANCES", "tasa": "0.1200", "cuotas": cuotas}


def expediente(monto="15000.00", plazo=12, version=1, id_solicitud=None, cod_cliente="C001", **cambios):
    cuerpo = {
        "idSolicitud": id_solicitud or str(uuid.uuid4()), "versionSolicitud": version,
        "codCliente": cod_cliente, "montoSolicitado": monto, "moneda": "PEN", "plazoMeses": plazo,
        "calendario": calendario(monto, plazo),
    }
    cuerpo.update(cambios)
    return cuerpo


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
