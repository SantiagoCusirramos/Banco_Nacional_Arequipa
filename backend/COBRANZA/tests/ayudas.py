"""Datos de prueba sobre COREDB y la base integrada reales (por HTTP) y atajos de la API.

Las pruebas de integración corren con `scripts/pruebas_integracion.sh`, que levanta la base
integrada (bna-core-db, con sus datos de desarrollo) y COREDB en contenedores nuevos, crea el
administrador y los usuarios de servicio `svc-cobranza` y `svc-evaluacion` con los scripts de
arranque de COREDB, y pasa sus datos en estas variables. Sin ellas, esas pruebas se omiten.

Para llegar a un crédito ya desembolsado se usa el mismo camino de COREDB que Desembolso:
cliente ACTIVO, expediente y aprobación, cuenta con fondos, verificación del documento, orden,
validación de identidad y confirmación. Así Cobranza encuentra el crédito como en el producto.
"""
from __future__ import annotations

import os
import secrets
import uuid
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

import httpx
import pymysql
from fastapi.testclient import TestClient

from COBRANZA.config import Config
from COBRANZA.main import Contexto

COREDB = os.environ.get("COBRANZA_TEST_COREDB", "").strip()
# COREDB está detrás del Bus (fase 2): el módulo presenta su credencial y las pruebas, la suya.
BUS_TOKEN = os.environ.get("COBRANZA_TEST_BUS_TOKEN", "").strip()
BUS_TOKEN_PRUEBAS = os.environ.get("COBRANZA_TEST_BUS_TOKEN_PRUEBAS", "").strip()
ADMIN_USUARIO = os.environ.get("COBRANZA_TEST_ADMIN_USUARIO", "admin")
ADMIN_PASSWORD = os.environ.get("COBRANZA_TEST_ADMIN_PASSWORD", "")
SERVICIO_USUARIO = os.environ.get("COBRANZA_TEST_SERVICIO_USUARIO", "svc-cobranza")
SERVICIO_SECRETO = os.environ.get("COBRANZA_TEST_SERVICIO_SECRETO", "")
EVALUACION_USUARIO = os.environ.get("COBRANZA_TEST_EVALUACION_USUARIO", "svc-evaluacion")
EVALUACION_SECRETO = os.environ.get("COBRANZA_TEST_EVALUACION_SECRETO", "")
DB_HOST = os.environ.get("COBRANZA_TEST_DB_HOST", "")
DB_PORT = int(os.environ.get("COBRANZA_TEST_DB_PORT", "3306"))
DB_ADMIN_PASSWORD = os.environ.get("COBRANZA_TEST_DB_ADMIN_PASSWORD", "")
CLAVE_PERSONAS = "clave-de-una-persona-1"
CENTIMO = Decimal("0.01")


def config(**cambios) -> Config:
    valores = {"servicio_secreto": SERVICIO_SECRETO, "servicio_usuario": SERVICIO_USUARIO, "coredb_url": COREDB,
               "bus_token": BUS_TOKEN, "sesion_cache_seg": 0}
    c = Config(**{**valores, **cambios})
    c.validar()
    return c


def contexto(**cambios) -> Contexto:
    return Contexto(config(**cambios))


def cabeceras(token: str, **otras) -> dict:
    return {"Authorization": f"Bearer {token}", "X-Correlation-ID": str(uuid.uuid4()), **otras}


# ------------------------------------------------------------------ COREDB real
def coredb(metodo: str, ruta: str, token: str | None = None, esperado: int | None = None, **opciones):
    encabezados = {**opciones.pop("headers", {})}
    if token:
        encabezados.update(cabeceras(token))
    if BUS_TOKEN_PRUEBAS:
        encabezados["X-Bus-Token"] = BUS_TOKEN_PRUEBAS
    r = httpx.request(metodo, COREDB + ruta, headers=encabezados, timeout=15, **opciones)
    if esperado is not None:
        assert r.status_code == esperado, f"{metodo} {ruta}: {r.status_code} {r.text}"
    return r


def login(username: str, password: str) -> str:
    return coredb("POST", "/coredb/auth/login", esperado=200,
                  json={"username": username, "password": password}).json()["access_token"]


def token_admin() -> str:
    return login(ADMIN_USUARIO, ADMIN_PASSWORD)


def token_servicio() -> str:
    return login(SERVICIO_USUARIO, SERVICIO_SECRETO)


def token_evaluacion() -> str:
    return login(EVALUACION_USUARIO, EVALUACION_SECRETO)


def persona(admin: str, rol: str) -> tuple[str, str]:
    """Crea un usuario con `rol` e inicia su sesión: (token, username)."""
    username = "u" + uuid.uuid4().hex[:12]
    coredb("POST", "/coredb/usuarios", admin, 201, json={
        "username": username, "nombre": f"{rol.title()} de pruebas", "password": CLAVE_PERSONAS, "rol": rol})
    return login(username, CLAVE_PERSONAS), username


def cliente_activo(admin: str) -> tuple[str, str]:
    """Un cliente ACTIVO: (cod_cliente, número de DNI)."""
    documento = f"{secrets.randbelow(10**8):08d}"
    r = coredb("POST", "/coredb/clientes", admin, 201, json={
        "tipo_documento": "DNI", "numero_documento": documento, "nombres": "Cliente", "apellido_paterno": "De Prueba",
        "apellido_materno": None, "correo": f"cob-{uuid.uuid4().hex[:12]}@example.com", "celular": "9" + documento,
        "version_contrato": "v1", "estado_habilitante": "OBSERVADO"})
    cod_cliente = r.json()["cod_cliente"]
    coredb("POST", f"/coredb/clientes/{cod_cliente}/estado", admin, 200,
           json={"estado": "ACTIVO", "motivo": "Identidad confirmada para las pruebas de Cobranza."})
    return cod_cliente, documento


def abrir_cuenta(admin: str, *titulares: str, moneda: str = "PEN", regimen: str = "INDIVIDUAL") -> str:
    numero = secrets.randbelow(10**15)
    coredb("POST", "/coredb/cuentas", admin, 201, json={
        "num_cuenta": f"CTA-{numero:016d}", "cci": f"{numero:020d}", "moneda": moneda, "regimen": regimen,
        "id_agencia": "AQP01", "titulares": list(titulares)})
    return f"CTA-{numero:016d}"


def depositar(admin: str, num_cuenta: str, monto: str) -> None:
    coredb("POST", "/coredb/movimientos", admin, 201, json={
        "num_cuenta": num_cuenta, "tipo": "DEPOSITO", "monto": monto, "glosa": "Fondos para las pruebas de Cobranza",
        "id_canal": "VEN", "idempotency_key": str(uuid.uuid4())})


def saldo(admin: str, num_cuenta: str) -> str:
    return coredb("GET", f"/coredb/cuentas/{num_cuenta}", admin, 200).json()["saldo_disponible"]


def calendario(monto: str, plazo: int) -> dict:
    """Un calendario coherente, como lo arma SOL: amortización constante y 1 % de interés mensual."""
    inicio = date.today() + timedelta(days=30)
    monto_d = Decimal(monto)
    amortizacion = (monto_d / plazo).quantize(CENTIMO, rounding=ROUND_HALF_UP)
    saldo_d, cuotas = monto_d, []
    for n in range(1, plazo + 1):
        capital = saldo_d if n == plazo else amortizacion
        interes = (saldo_d * Decimal("0.01")).quantize(CENTIMO, rounding=ROUND_HALF_UP)
        cuotas.append({"numeroCuota": n, "fechaVencimiento": (inicio + timedelta(days=30 * (n - 1))).isoformat(),
                       "saldoInicial": str(saldo_d), "amortizacion": str(capital), "interes": str(interes),
                       "cuotaTotal": str(capital + interes), "saldoFinal": str(saldo_d - capital)})
        saldo_d -= capital
    return {"metodo": "FRANCES", "tasa": "0.1268", "cuotas": cuotas}


def aprobada(admin: str, cod_cliente: str, monto: str = "1200.00", plazo: int = 3) -> tuple[str, str]:
    """Una solicitud APROBADA por la regla: (idSolicitud, idEvaluacion)."""
    id_solicitud = str(uuid.uuid4())
    acuse = coredb("POST", "/coredb/creditos/solicitudes", token_evaluacion(), 201, json={
        "idSolicitud": id_solicitud, "versionSolicitud": 1, "codCliente": cod_cliente, "montoSolicitado": monto,
        "moneda": "PEN", "plazoMeses": plazo, "calendario": calendario(monto, plazo)}).json()
    r = coredb("POST", f"/coredb/creditos/solicitudes/{id_solicitud}/evaluaciones", admin, 200, json={
        "versionSolicitud": 1, "ingresoMensual": "9000.00", "deudaMensual": "0.00", "riesgo": "BUENO",
        "verificada": True})
    assert r.json()["resultado"] == "APROBADO", r.text
    return id_solicitud, acuse["idEvaluacion"]


def con_admin_de_la_base(sql: str, parametros: tuple) -> int:
    """Una sentencia con bna_admin_user: para fechar en el pasado lo que la API solo crea hoy."""
    conexion = pymysql.connect(host=DB_HOST, port=DB_PORT, user="bna_admin_user", password=DB_ADMIN_PASSWORD,
                               autocommit=True)
    try:
        with conexion.cursor() as cursor:
            return cursor.execute(sql, parametros)
    finally:
        conexion.close()


def credito_desembolsado(admin: str, operador: str, monto: str = "1200.00", plazo: int = 3,
                         fondos: str = "5000.00") -> dict:
    """Un crédito desembolsado por el camino real de COREDB, con su cuenta y sus cuotas."""
    cod_cliente, documento = cliente_activo(admin)
    id_solicitud, id_evaluacion = aprobada(admin, cod_cliente, monto, plazo)
    num_cuenta = abrir_cuenta(admin, cod_cliente)
    depositar(admin, num_cuenta, fondos)

    verificacion = coredb("POST", "/coredb/clientes/validaciones/documento", operador, 201, json={
        "tipo_documento": "DNI", "numero_documento": documento, "identidad_verificada": True})
    id_validacion = verificacion.json()["id_validacion"]
    assert verificacion.json()["resultado"] == "APROBADO", verificacion.text

    orden = coredb("POST", "/coredb/creditos/ordenes", operador, 201,
                   headers={"X-Idempotency-Key": str(uuid.uuid4())},
                   json={"idEvaluacion": id_evaluacion, "numCuenta": num_cuenta, "canal": "VEN"}).json()
    coredb("POST", f"/coredb/creditos/ordenes/{orden['idOrden']}/validaciones", operador, 201, json={
        "tipo": "IDENTIDAD", "resultado": "APROBADA", "referenciaEvidencia": str(id_validacion),
        "detalle": "Documento original verificado en ventanilla."})
    confirmada = coredb("POST", f"/coredb/creditos/ordenes/{orden['idOrden']}/confirmacion", operador, 201).json()
    return {"codCliente": cod_cliente, "documento": documento, "idSolicitud": id_solicitud,
            "idEvaluacion": id_evaluacion, "numCuenta": num_cuenta, "codCredito": confirmada["codCredito"],
            "orden": orden}


def atrasar_cuotas(cod_credito: str, dias: int = 40, numero_cuota: int = 1) -> int:
    """Mueve al pasado una cuota OFICIAL del crédito para poder probar mora y vencimientos."""
    return con_admin_de_la_base(
        "UPDATE creditos.cuota q "
        "JOIN creditos.credito cr ON cr.id_calendario = q.id_calendario "
        "SET q.fecha_vencimiento = q.fecha_vencimiento - INTERVAL %s DAY "
        "WHERE cr.cod_credito = %s AND q.numero_cuota = %s",
        (dias, cod_credito, numero_cuota))


# ------------------------------------------------------------------ Cobranza
def pago_legacy(api: TestClient, token: str, datos: dict, referencia: str | None = None, **cambios):
    cuerpo = {
        "codCliente": datos["codCliente"], "codCredito": datos["codCredito"], "montoPago": datos["montoPago"],
        "cuentaOrigen": datos["numCuenta"], "referenciaTransaccion": referencia or str(uuid.uuid4()),
        "idCanal": "HB", **cambios,
    }
    return api.post("/cr-int-08/pagos", headers=cabeceras(token), json=cuerpo)


def pago_nuevo(api: TestClient, token: str, cod_credito: str, num_cuenta: str, monto: str,
               referencia: str | None = None, **cambios):
    cuerpo = {"numCuenta": num_cuenta, "monto": monto, "referencia": referencia or str(uuid.uuid4()),
              "canal": "VEN", **cambios}
    return api.post(f"/api/v1/creditos/{cod_credito}/pagos", headers=cabeceras(token), json=cuerpo)
