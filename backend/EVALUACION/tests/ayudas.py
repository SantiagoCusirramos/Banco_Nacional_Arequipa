"""Datos y dobles de prueba: COREDB real (por HTTP), SOL en memoria y atajos de la API.

Las pruebas de integración corren con `scripts/pruebas_integracion.sh`, que levanta la base
integrada (bna-core-db, con sus datos de desarrollo) y COREDB en contenedores nuevos, crea el
administrador y el usuario de servicio `svc-evaluacion` con el script de arranque de COREDB, y
pasa sus datos en estas variables. Sin ellas, esas pruebas se omiten.
"""
from __future__ import annotations

import os
import secrets
import socket
import threading
import time
import uuid
from contextlib import contextmanager

import httpx
import pymysql
import uvicorn
from fastapi.testclient import TestClient

from EVALUACION.config import Config
from EVALUACION.main import Contexto
from EVALUACION.scripts.enviar_expediente_demo import sobre_de_sol

COREDB = os.environ.get("EVALUACION_TEST_COREDB", "").strip()
# COREDB está detrás del Bus (fase 2): el módulo presenta su credencial y las pruebas, la suya.
BUS_TOKEN = os.environ.get("EVALUACION_TEST_BUS_TOKEN", "").strip()
BUS_TOKEN_PRUEBAS = os.environ.get("EVALUACION_TEST_BUS_TOKEN_PRUEBAS", "").strip()
ADMIN_USUARIO = os.environ.get("EVALUACION_TEST_ADMIN_USUARIO", "admin")
ADMIN_PASSWORD = os.environ.get("EVALUACION_TEST_ADMIN_PASSWORD", "")
SERVICIO_USUARIO = os.environ.get("EVALUACION_TEST_SERVICIO_USUARIO", "svc-evaluacion")
SERVICIO_SECRETO = os.environ.get("EVALUACION_TEST_SERVICIO_SECRETO", "")
DB_HOST = os.environ.get("EVALUACION_TEST_DB_HOST", "")
DB_PORT = int(os.environ.get("EVALUACION_TEST_DB_PORT", "3306"))
DB_ADMIN_PASSWORD = os.environ.get("EVALUACION_TEST_DB_ADMIN_PASSWORD", "")
TOKEN_SOL = secrets.token_hex(24)
TOKEN_RESULTADOS = secrets.token_hex(24)
URL_SOL = "http://sol.prueba"
CLAVE_PERSONAS = "clave-de-una-persona-1"


class SolFalso:
    """Recibe los resultados de CR-INT-03. `respuestas` fija los códigos que devuelve, en orden."""

    def __init__(self):
        self.recibidos: list[httpx.Request] = []
        self.respuestas: list[int] = []

    def __call__(self, peticion: httpx.Request) -> httpx.Response:
        self.recibidos.append(peticion)
        estado = self.respuestas.pop(0) if self.respuestas else 200
        if estado == 0:
            raise httpx.ConnectTimeout("sin respuesta", request=peticion)
        return httpx.Response(estado, json={"recibido": estado == 200})


def config(**cambios) -> Config:
    valores = {"servicio_secreto": SERVICIO_SECRETO, "servicio_usuario": SERVICIO_USUARIO, "coredb_url": COREDB, "bus_token": BUS_TOKEN,
               "token_sol": TOKEN_SOL, "sol_url": URL_SOL, "sol_token_resultados": TOKEN_RESULTADOS,
               "envio_intervalo_seg": 0, "sesion_cache_seg": 0}
    c = Config(**{**valores, **cambios})
    c.validar()
    return c


def contexto(sol: SolFalso, **cambios) -> Contexto:
    return Contexto(config(**cambios), transporte_sol=httpx.MockTransport(sol))


def cabeceras(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "X-Correlation-ID": str(uuid.uuid4())}


# ------------------------------------------------------------------ COREDB real
def coredb(metodo: str, ruta: str, token: str | None = None, esperado: int | None = None, **opciones):
    encabezados = cabeceras(token) if token else {}
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


def persona(admin: str, rol: str, id_empleado: uuid.UUID | None = None) -> tuple[str, str]:
    """Crea un usuario con `rol` e inicia su sesión: (token, username)."""
    username = "u" + uuid.uuid4().hex[:12]
    cuerpo = {"username": username, "nombre": f"{rol.title()} de pruebas", "password": CLAVE_PERSONAS, "rol": rol}
    if id_empleado:
        cuerpo["id_empleado"] = str(id_empleado)
    coredb("POST", "/coredb/usuarios", admin, 201, json=cuerpo)
    return login(username, CLAVE_PERSONAS), username


def analista_registrado(admin: str) -> tuple[str, str]:
    """Un ANALISTA ligado a un empleado y registrado como analista de créditos. COREDB no crea
    empleados (los carga el administrador de la base), así que se insertan con bna_admin_user."""
    id_empleado = uuid.uuid4()
    conexion = pymysql.connect(host=DB_HOST, port=DB_PORT, user="bna_admin_user", password=DB_ADMIN_PASSWORD,
                               autocommit=True)
    try:
        with conexion.cursor() as cursor:
            cursor.execute("INSERT INTO core.empleado (id_empleado, codigo_empleado, nombre_completo, cargo) "
                           "VALUES (%s, %s, 'Analista de pruebas', 'ANALISTA')",
                           (id_empleado.bytes, "E" + uuid.uuid4().hex[:10].upper()))
    finally:
        conexion.close()
    sesion = persona(admin, "ANALISTA", id_empleado)
    coredb("POST", "/coredb/creditos/analistas", admin, 201, json={"idEmpleado": str(id_empleado)})
    return sesion


def cliente_nuevo(admin: str) -> str:
    """Un cliente del CORE que puede operar (OBSERVADO, como lo registra una persona)."""
    sufijo = f"{secrets.randbelow(10**8):08d}"
    r = coredb("POST", "/coredb/clientes", admin, 201, json={
        "tipo_documento": "DNI", "numero_documento": sufijo, "nombres": "Cliente", "apellido_paterno": "De Prueba",
        "apellido_materno": None, "correo": f"eva-{uuid.uuid4().hex[:12]}@example.com", "celular": "9" + sufijo,
        "version_contrato": "v1", "estado_habilitante": "OBSERVADO"})
    return r.json()["cod_cliente"]


# ------------------------------------------------------------------ SOL
def nuevo_sobre(cod_cliente: str, **cambios) -> dict:
    datos = {"id_cliente": cod_cliente, "numero_documento": "70000001", "nombres": "Juan",
             "apellido_paterno": "Perez", "apellido_materno": "Quispe", "monto": "15000.00", "plazo_meses": 12}
    datos.update(cambios)
    return sobre_de_sol(**datos)


def recibir(api: TestClient, sobre: dict, token: str = TOKEN_SOL):
    return api.post("/eva/applications", json=sobre, headers={
        "Authorization": f"Bearer {token}", "X-Idempotency-Key": sobre["idOperacion"],
        "X-Correlation-ID": sobre["idCorrelacion"]})


def evaluar(api: TestClient, token: str, id_solicitud: str, ingreso: str, deuda: str = "0.00",
            riesgo: str = "BUENO", version: int = 1, verificada: bool = True):
    return api.post(f"/eva/v1/solicitudes/{id_solicitud}/evaluaciones", headers=cabeceras(token),
                    json={"versionSolicitud": version, "ingresoMensual": ingreso, "deudaMensual": deuda,
                          "riesgo": riesgo, "verificada": verificada})


def decidir(api: TestClient, token: str, id_evaluacion: str, decision: str,
            comentario: str = "Sustento revisado con el cliente."):
    return api.post(f"/eva/v1/evaluaciones/{id_evaluacion}/decision", headers=cabeceras(token),
                    json={"decision": decision, "comentario": comentario})


def detalle(api: TestClient, token: str, id_solicitud: str) -> dict:
    r = api.get(f"/eva/v1/solicitudes/{id_solicitud}", headers=cabeceras(token))
    assert r.status_code == 200, r.text
    return r.json()


@contextmanager
def servidor(app):
    """La app en un uvicorn real, en un hilo: para probar con el cliente HTTP de SOL."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        puerto = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=puerto, log_level="warning"))
    hilo = threading.Thread(target=server.run, daemon=True)
    hilo.start()
    limite = time.monotonic() + 15
    while not server.started:
        if time.monotonic() > limite or not hilo.is_alive():
            raise RuntimeError("uvicorn no arrancó")
        time.sleep(0.05)
    try:
        yield f"http://127.0.0.1:{puerto}"
    finally:
        server.should_exit = True
        hilo.join(timeout=10)
