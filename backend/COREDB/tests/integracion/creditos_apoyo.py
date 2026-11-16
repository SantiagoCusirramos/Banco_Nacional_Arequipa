"""Ayudas compartidas por las pruebas de créditos contra la base real."""

import uuid
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from fastapi.testclient import TestClient

from COREDB.main import app

CENTIMO = Decimal("0.01")
BASE = "/coredb/creditos"


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
