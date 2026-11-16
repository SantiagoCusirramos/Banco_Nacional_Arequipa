"""Datos de prueba sobre COREDB y la base integrada reales (por HTTP) y atajos de la API.

Las pruebas de integración corren con `scripts/pruebas_integracion.sh`, que levanta la base
integrada (bna-core-db, con sus datos de desarrollo) y COREDB en contenedores nuevos, crea el
administrador y los usuarios de servicio `svc-desembolso` y `svc-evaluacion` con los scripts de
arranque de COREDB, y pasa sus datos en estas variables. Sin ellas, esas pruebas se omiten.
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

from DESEMBOLSO.config import Config
from DESEMBOLSO.main import Contexto

COREDB = os.environ.get("DESEMBOLSO_TEST_COREDB", "").strip()
ADMIN_USUARIO = os.environ.get("DESEMBOLSO_TEST_ADMIN_USUARIO", "admin")
ADMIN_PASSWORD = os.environ.get("DESEMBOLSO_TEST_ADMIN_PASSWORD", "")
SERVICIO_USUARIO = os.environ.get("DESEMBOLSO_TEST_SERVICIO_USUARIO", "svc-desembolso")
SERVICIO_SECRETO = os.environ.get("DESEMBOLSO_TEST_SERVICIO_SECRETO", "")
EVALUACION_USUARIO = os.environ.get("DESEMBOLSO_TEST_EVALUACION_USUARIO", "svc-evaluacion")
EVALUACION_SECRETO = os.environ.get("DESEMBOLSO_TEST_EVALUACION_SECRETO", "")
DB_HOST = os.environ.get("DESEMBOLSO_TEST_DB_HOST", "")
DB_PORT = int(os.environ.get("DESEMBOLSO_TEST_DB_PORT", "3306"))
DB_ADMIN_PASSWORD = os.environ.get("DESEMBOLSO_TEST_DB_ADMIN_PASSWORD", "")
CLAVE_PERSONAS = "clave-de-una-persona-1"
CENTIMO = Decimal("0.01")


def config(**cambios) -> Config:
    valores = {"servicio_secreto": SERVICIO_SECRETO, "servicio_usuario": SERVICIO_USUARIO, "coredb_url": COREDB,
               "sesion_cache_seg": 0}
    c = Config(**{**valores, **cambios})
    c.validar()
    return c


def contexto(**cambios) -> Contexto:
    return Contexto(config(**cambios))


def cabeceras(token: str, **otras) -> dict:
    return {"Authorization": f"Bearer {token}", "X-Correlation-ID": str(uuid.uuid4()), **otras}


# ------------------------------------------------------------------ COREDB real
def coredb(metodo: str, ruta: str, token: str | None = None, esperado: int | None = None, **opciones):
    r = httpx.request(metodo, COREDB + ruta, headers=cabeceras(token) if token else {}, timeout=15, **opciones)
    if esperado is not None:
        assert r.status_code == esperado, f"{metodo} {ruta}: {r.status_code} {r.text}"
    return r


def login(username: str, password: str) -> str:
    return coredb("POST", "/coredb/auth/login", esperado=200,
                  json={"username": username, "password": password}).json()["access_token"]


def token_admin() -> str:
    return login(ADMIN_USUARIO, ADMIN_PASSWORD)


def token_evaluacion() -> str:
    return login(EVALUACION_USUARIO, EVALUACION_SECRETO)


def persona(admin: str, rol: str) -> tuple[str, str]:
    """Crea un usuario con `rol` e inicia su sesión: (token, username)."""
    username = "u" + uuid.uuid4().hex[:12]
    coredb("POST", "/coredb/usuarios", admin, 201, json={
        "username": username, "nombre": f"{rol.title()} de pruebas", "password": CLAVE_PERSONAS, "rol": rol})
    return login(username, CLAVE_PERSONAS), username


def cliente_activo(admin: str) -> tuple[str, str]:
    """Un cliente ACTIVO: (cod_cliente, número de DNI). Una persona lo registra OBSERVADO y el
    administrador lo activa; la verificación del documento solo aprueba a un cliente ACTIVO."""
    documento = f"{secrets.randbelow(10**8):08d}"
    r = coredb("POST", "/coredb/clientes", admin, 201, json={
        "tipo_documento": "DNI", "numero_documento": documento, "nombres": "Cliente", "apellido_paterno": "De Prueba",
        "apellido_materno": None, "correo": f"des-{uuid.uuid4().hex[:12]}@example.com", "celular": "9" + documento,
        "version_contrato": "v1", "estado_habilitante": "OBSERVADO"})
    cod_cliente = r.json()["cod_cliente"]
    coredb("POST", f"/coredb/clientes/{cod_cliente}/estado", admin, 200,
           json={"estado": "ACTIVO", "motivo": "Identidad confirmada para las pruebas de Desembolso."})
    return cod_cliente, documento


def abrir_cuenta(admin: str, *titulares: str, moneda: str = "PEN", regimen: str = "INDIVIDUAL") -> str:
    numero = secrets.randbelow(10**15)
    coredb("POST", "/coredb/cuentas", admin, 201, json={
        "num_cuenta": f"CTA-{numero:016d}", "cci": f"{numero:020d}", "moneda": moneda, "regimen": regimen,
        "id_agencia": "AQP01", "titulares": list(titulares)})
    return f"CTA-{numero:016d}"


def saldo(admin: str, num_cuenta: str) -> str:
    return coredb("GET", f"/coredb/cuentas/{num_cuenta}", admin, 200).json()["saldo_disponible"]


def movimientos(admin: str, num_cuenta: str) -> list[dict]:
    return coredb("GET", f"/coredb/movimientos/cuenta/{num_cuenta}", admin, 200).json()


def calendario(monto: str, plazo: int) -> dict:
    """Un calendario coherente, como lo arma SOL: amortización constante y 1 % de interés mensual."""
    inicio = date.today() + timedelta(days=40)
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


def aprobada(admin: str, cod_cliente: str, monto: str = "15000.00", plazo: int = 12) -> tuple[str, str]:
    """Una solicitud APROBADA por la regla: (idSolicitud, idEvaluacion). El expediente lo registra
    svc-evaluacion, como lo hace Evaluación, y el administrador lo evalúa con ingreso holgado."""
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


# ------------------------------------------------------------------ Desembolso
def verificar(api: TestClient, token: str, documento: str, verificada: bool = True):
    return api.post("/api/v1/identidad", headers=cabeceras(token),
                    json={"tipoDocumento": "DNI", "numeroDocumento": documento, "identidadVerificada": verificada})


def preparar(api: TestClient, token: str, id_evaluacion: str, num_cuenta: str, llave: str | None = None, **cambios):
    return api.post("/api/v1/ordenes", headers=cabeceras(token, **{"X-Idempotency-Key": llave or str(uuid.uuid4())}),
                    json={"idEvaluacion": id_evaluacion, "numCuenta": num_cuenta, **cambios})


def validar_identidad(api: TestClient, token: str, id_orden: str, id_validacion: int):
    return api.post(f"/api/v1/ordenes/{id_orden}/validaciones", headers=cabeceras(token), json={
        "tipo": "IDENTIDAD", "resultado": "APROBADA", "referenciaEvidencia": str(id_validacion),
        "detalle": "Documento original verificado en ventanilla."})


def confirmar(api: TestClient, token: str, id_orden: str):
    return api.post(f"/api/v1/ordenes/{id_orden}/confirmacion", headers=cabeceras(token))


def orden_preparada(api: TestClient, admin: str, operador: str, cuenta: str | None = None):
    """Cliente ACTIVO con su aprobación, su cuenta y una orden PREPARADA, más la verificación de
    hoy de su documento. Devuelve un dict con todo."""
    cod_cliente, documento = cliente_activo(admin)
    id_solicitud, id_evaluacion = aprobada(admin, cod_cliente)
    num_cuenta = cuenta or abrir_cuenta(admin, cod_cliente)
    verificacion = verificar(api, operador, documento)
    assert verificacion.status_code == 201 and verificacion.json()["resultado"] == "APROBADO", verificacion.text
    orden = preparar(api, operador, id_evaluacion, num_cuenta)
    assert orden.status_code == 201, orden.text
    return {"codCliente": cod_cliente, "documento": documento, "idSolicitud": id_solicitud,
            "idEvaluacion": id_evaluacion, "numCuenta": num_cuenta, "idValidacion": verificacion.json()["idValidacion"],
            "orden": orden.json()}


def orden_validada(api: TestClient, admin: str, operador: str):
    datos = orden_preparada(api, admin, operador)
    r = validar_identidad(api, operador, datos["orden"]["idOrden"], datos["idValidacion"])
    assert r.status_code == 201 and r.json()["estado"] == "VALIDADA", r.text
    return datos
