"""Entorno de pruebas: MySQL real con sql/esquema.sql, el simulador de los módulos y la API en hilos uvicorn.

Corren solo con DESEMBOLSO_TEST_MYSQL (por ejemplo mysql+pymysql://root:clave@127.0.0.1:3306), un MySQL 8.4 de
pruebas: se crea desde cero bna_desembolso_pruebas y la API se conecta con el usuario de permisos mínimos.
scripts/pruebas_integracion.sh lo prepara en contenedores. Sin esa variable, las pruebas se omiten.
"""
from __future__ import annotations

import os
import secrets
import socket
import threading
import time
import uuid

import httpx
import pymysql
import pytest
import uvicorn
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from DESEMBOLSO import esquema
from DESEMBOLSO.config import Config
from DESEMBOLSO.main import crear_app
from DESEMBOLSO.tests import datos

MYSQL = os.environ.get("DESEMBOLSO_TEST_MYSQL", "").strip()
BD_PRUEBA = "bna_desembolso_pruebas"
USUARIO_APP = "desembolso_pruebas"
CLAVE_APP = secrets.token_hex(16)
TABLAS = ["des_evento_entrega", "des_validacion", "des_solicitud_reversion", "des_auditoria", "des_orden", "des_correlativo"]

# Las cuentas de los datos del simulador, por su número corto de antes (CTA-0001 ... CTA-0013).
CTA = {f"{i:04d}": numero for i, (numero, *_resto) in enumerate(datos.CUENTAS, start=1)}


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _servir(aplicacion) -> tuple[str, uvicorn.Server]:
    puerto = _puerto_libre()
    servidor = uvicorn.Server(uvicorn.Config(aplicacion, host="127.0.0.1", port=puerto, log_level="warning"))
    threading.Thread(target=servidor.run, daemon=True).start()
    limite = time.time() + 15
    while not servidor.started:
        if time.time() > limite:
            raise RuntimeError("El servidor de pruebas no inició")
        time.sleep(0.05)
    return f"http://127.0.0.1:{puerto}", servidor


def _root():
    url = make_url(MYSQL)
    return pymysql.connect(host=url.host or "127.0.0.1", port=url.port or 3306, user=url.username or "root",
                           password=url.password or "", autocommit=True, charset="utf8mb4")


@pytest.fixture(scope="session")
def motor_prueba():
    if not MYSQL:
        pytest.skip("Requiere DESEMBOLSO_TEST_MYSQL (scripts/pruebas_integracion.sh).")
    conexion = _root()
    with conexion.cursor() as cursor:
        cursor.execute(f"DROP DATABASE IF EXISTS {BD_PRUEBA}")
        esquema.instalar(cursor, BD_PRUEBA, USUARIO_APP, CLAVE_APP)
        # Aplicarlo dos veces comprueba que desembolso-init puede correr en cada arranque.
        esquema.instalar(cursor, BD_PRUEBA, USUARIO_APP, CLAVE_APP)
    conexion.close()
    motor = create_engine(f"{MYSQL}/{BD_PRUEBA}", isolation_level="AUTOCOMMIT")
    yield motor
    motor.dispose()
    conexion = _root()
    with conexion.cursor() as cursor:
        cursor.execute(f"DROP DATABASE IF EXISTS {BD_PRUEBA}")
        cursor.execute(f"DROP USER IF EXISTS '{USUARIO_APP}'@'%'")
    conexion.close()


@pytest.fixture(scope="session")
def simulador():
    from DESEMBOLSO.tests.simulador import app as simulador_app
    url, servidor = _servir(simulador_app)
    yield url
    servidor.should_exit = True


@pytest.fixture(scope="session")
def config(motor_prueba, simulador) -> Config:
    url = make_url(MYSQL)
    return Config(
        _env_file=None,
        database_url=f"mysql+pymysql://{USUARIO_APP}:{CLAVE_APP}@{url.host}:{url.port or 3306}/{BD_PRUEBA}",
        coredb_url=simulador, evaluacion_url=simulador, cuentas_url=f"{simulador}/api/v1/cuentas",
        cobranza_url=simulador, cobranza_api_key=datos.CLAVE_COBRANZA,
        svc_usuario="svc-desembolso", svc_secreto=datos.SECRETO_SERVICIO,
        agencia_id="AG001", agencia_nombre="Agencia Arequipa Centro",
        trabajos_habilitados=False, timeout_abono_seg=0.8, timeout_dependencia_seg=3, reintentos_consulta=0,
        recuperacion_espera_seg=0, recuperacion_gracia_seg=1, entrega_backoff_base_seg=0, entrega_max_intentos=3,
        sesion_cache_seg=0,
    )


@pytest.fixture(scope="session")
def aplicacion(config):
    return crear_app(config)


@pytest.fixture(scope="session")
def api_url(aplicacion):
    url, servidor = _servir(aplicacion)
    yield url
    servidor.should_exit = True


@pytest.fixture(autouse=True)
def limpiar(request, motor_prueba, simulador):
    with motor_prueba.connect() as c:
        c.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for tabla in TABLAS:
            c.execute(text(f"TRUNCATE TABLE {tabla}"))
        c.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    httpx.post(f"{simulador}/_sim/reiniciar")
    yield


class ClienteApi:
    """Cliente HTTP de la API con la sesión de COREDB de un usuario (la del simulador)."""

    _tokens: dict[str, str] = {}

    def __init__(self, api_url: str, simulador: str, usuario: str | None):
        cabeceras = {}
        if usuario:
            if usuario not in self._tokens:
                r = httpx.post(f"{simulador}/coredb/auth/login", json={"username": usuario, "password": datos.CONTRASENA})
                self._tokens[usuario] = r.json()["access_token"]
            cabeceras["Authorization"] = f"Bearer {self._tokens[usuario]}"
        self.http = httpx.Client(base_url=f"{api_url}/api/v1", headers=cabeceras, timeout=20)

    def get(self, ruta, **kw):
        return self.http.get(ruta, **kw)

    def post(self, ruta, clave: str | None = None, **kw):
        cabeceras = kw.pop("headers", {})
        if clave:
            cabeceras["X-Idempotency-Key"] = clave
        return self.http.post(ruta, headers=cabeceras, **kw)

    def put(self, ruta, **kw):
        return self.http.put(ruta, **kw)

    # ---- atajos del flujo
    def preparar(self, aprobacion_id: str, clave: str | None = None) -> httpx.Response:
        return self.post("/ordenes", clave=clave or str(uuid.uuid4()), json={"aprobacion_id": aprobacion_id})

    def identidad(self, orden_id: str, documento: str) -> httpx.Response:
        return self.post(f"/ordenes/{orden_id}/identidad",
                         json={"metodo": "VERIFICACION_PRESENCIAL", "numero_documento": documento})

    def hasta_validada(self, aprobacion_id: str, cuenta_id: str) -> dict:
        orden = self.preparar(aprobacion_id).json()
        cliente = next(a["cliente"] for a in datos.APROBACIONES if a["id"] == aprobacion_id)
        r = self.identidad(orden["id"], datos.CLIENTES[cliente]["documento"])
        assert r.status_code == 200, r.text
        orden = r.json()
        r = self.put(f"/ordenes/{orden['id']}/cuenta-destino", json={"cuenta_id": cuenta_id, "version": orden["version"]})
        assert r.status_code == 200, r.text
        return r.json()

    def confirmar(self, orden: dict) -> httpx.Response:
        return self.post(f"/ordenes/{orden['id']}/confirmacion", clave=orden["idempotency_key"],
                         json={"version": orden["version"]})


@pytest.fixture
def cliente(api_url, simulador):
    def fabricar(usuario: str | None = "operador1") -> ClienteApi:
        return ClienteApi(api_url, simulador, usuario)
    return fabricar


@pytest.fixture
def sim(simulador):
    class Sim:
        def escenario(self, **cambios):
            httpx.post(f"{simulador}/_sim/escenarios", json=cambios).raise_for_status()

        def aprobacion(self, aprobacion_id, **cambios):
            httpx.post(f"{simulador}/_sim/aprobaciones/{aprobacion_id}", json=cambios).raise_for_status()

        def estado(self) -> dict:
            return httpx.get(f"{simulador}/_sim/estado").json()

        def abonos_en(self, numero_cuenta) -> list[dict]:
            return [m for m in self.estado()["movimientos"] if m["num_cuenta"] == numero_cuenta]
    return Sim()


@pytest.fixture
def sql(motor_prueba):
    def ejecutar(sentencia: str, **parametros):
        with motor_prueba.connect() as c:
            resultado = c.execute(text(sentencia), parametros)
            return resultado.mappings().all() if resultado.returns_rows else resultado.rowcount
    return ejecutar
