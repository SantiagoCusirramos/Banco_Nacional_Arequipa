"""Datos y dobles de prueba compartidos: perfiles de COREDB, SOL en memoria y atajos de la API."""
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
from sqlalchemy.engine import make_url

from COREDB import permisos
from EVALUACION.auth import VerificadorCoreDb
from EVALUACION.config import Config
from EVALUACION.main import Contexto
from EVALUACION.scripts.enviar_expediente_demo import sobre_de_sol

URL_MYSQL = os.environ.get("EVALUACION_TEST_MYSQL", "").strip()
BASE = "bna_evaluacion_pruebas"
USUARIO = "evaluacion_pruebas"
CLAVE_APP = secrets.token_hex(16)
TOKEN_SOL = secrets.token_hex(24)
TOKEN_RESULTADOS = secrets.token_hex(24)
URL_SOL = "http://sol.prueba"


def _acciones(clave: str, por_omision: set[str] | None = None) -> list[str]:
    return sorted(permisos.PERMISOS.get(clave, por_omision or set()))


# Token -> lo que COREDB devolvería en GET /coredb/auth/me.
PERFILES = {
    "tok-analista": {"username": "ana.analista", "rol": "ANALISTA", "modulo": None, "acciones": _acciones("ANALISTA")},
    "tok-analista-2": {"username": "beto.analista", "rol": "ANALISTA", "modulo": None,
                       "acciones": _acciones("ANALISTA")},
    "tok-auditor": {"username": "aldo.auditor", "rol": "AUDITOR", "modulo": None, "acciones": _acciones("AUDITOR")},
    "tok-operador": {"username": "oscar.operador", "rol": "OPERADOR", "modulo": None, "acciones": _acciones("OPERADOR")},
    "tok-admin": {"username": "admin", "rol": "ADMINISTRADOR", "modulo": None, "acciones": _acciones("ADMINISTRADOR")},
    # Aún no está en COREDB/permisos.py: lo agrega el PR de Desembolso.
    "tok-desembolso": {"username": "svc-desembolso", "rol": "SERVICIO", "modulo": "DESEMBOLSO",
                       "acciones": _acciones("SERVICIO:DESEMBOLSO", {"VER_CUENTA", "REGISTRAR_MOVIMIENTO"})},
    "tok-cobranza": {"username": "svc-cobranza", "rol": "SERVICIO", "modulo": "COBRANZA",
                     "acciones": ["REGISTRAR_MOVIMIENTO", "VER_CUENTA"]},
}


def coredb_falso(peticion: httpx.Request) -> httpx.Response:
    token = peticion.headers.get("Authorization", "").removeprefix("Bearer ")
    perfil = PERFILES.get(token)
    if peticion.url.path != "/coredb/auth/me" or perfil is None:
        return httpx.Response(401, json={"error": {"code": "TOKEN_INVALIDO", "message": "Token inválido."}})
    return httpx.Response(200, json={"id_usuario": str(uuid.uuid4()), **perfil})


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


def cabeceras(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "X-Correlation-ID": str(uuid.uuid4())}


def nuevo_sobre(**cambios) -> dict:
    datos = {"id_cliente": "CLI000000001", "numero_documento": "70000001", "nombres": "Juan",
             "apellido_paterno": "Perez", "apellido_materno": "Quispe", "monto": "15000.00", "plazo_meses": 12}
    datos.update(cambios)
    return sobre_de_sol(**datos)


def _root():
    url = make_url(URL_MYSQL)
    return pymysql.connect(host=url.host or "127.0.0.1", port=url.port or 3306, user=url.username or "root",
                           password=url.password or "", autocommit=True, charset="utf8mb4")


def construir_contexto(url_base: str, sol: SolFalso, coredb=coredb_falso, **cambios) -> Contexto:
    valores = {"database_url": url_base, "coredb_url": "http://coredb.prueba", "token_sol": TOKEN_SOL,
               "sol_url": URL_SOL, "sol_token_resultados": TOKEN_RESULTADOS, "envio_intervalo_seg": 0}
    config = Config(**{**valores, **cambios})
    config.validar()
    verificador = VerificadorCoreDb(config.coredb_url, recordar_seg=0, transporte=httpx.MockTransport(coredb))
    return Contexto(config, verificador=verificador, transporte_sol=httpx.MockTransport(sol))


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


def recibir(api: TestClient, sobre: dict, token: str = TOKEN_SOL):
    return api.post("/eva/applications", json=sobre, headers={
        "Authorization": f"Bearer {token}", "X-Idempotency-Key": sobre["idOperacion"],
        "X-Correlation-ID": sobre["idCorrelacion"]})


def registrar_situacion(api: TestClient, id_evaluacion: str, ingreso: str, deuda: str = "0.00",
                        riesgo: str = "BUENO", token: str = "tok-analista", version: int | None = None,
                        verificada: bool = True):
    if version is None:
        version = api.get(f"/eva/v1/evaluaciones/{id_evaluacion}", headers=cabeceras(token)).json()["version"]
    return api.post(f"/eva/v1/evaluaciones/{id_evaluacion}/situacion-financiera", headers=cabeceras(token),
                    json={"ingresoMensual": ingreso, "deudaMensual": deuda, "riesgo": riesgo,
                          "verificada": verificada, "version": version})


def aprobada(api: TestClient, **cambios) -> dict:
    """Recibe un expediente y lo deja APROBADO por la regla. Devuelve el detalle de la evaluación."""
    acuse = recibir(api, nuevo_sobre(**cambios)).json()
    r = registrar_situacion(api, acuse["idEvaluacion"], "5000.00")
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "APROBADO"
    return r.json()
