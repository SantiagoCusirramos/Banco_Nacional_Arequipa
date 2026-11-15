"""API de Evaluación Crediticia (módulo 12, Línea de Créditos). Puerto 8015 en el producto.

    uvicorn EVALUACION.main:app --port 8015      (desde backend/)

Rutas:
  CR-INT-02  POST /eva/applications, GET /eva/operations/{idOperacion}       SOL, con su token
  CR-INT-04  GET /eva/v1/aprobaciones, GET /eva/v1/aprobaciones/{id},        Desembolso (usuario de
             POST /eva/v1/aprobaciones/{id}/desembolso                       servicio de COREDB)
  Personal   /eva/v1/evaluaciones..., /eva/v1/envios..., /eva/v1/historial   token de COREDB
  CR-INT-03  la entrega un trabajador interno a SOL (envios.py)
"""
from __future__ import annotations

import json
import logging
import sys
import time
from contextlib import asynccontextmanager
from typing import Literal

import httpx
from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.pool import NullPool

from .auth import AUDITAR, DECIDIR, EVALUAR, LECTURA, Perfil, VerificadorCoreDb, canal_sol, lector_aprobaciones, \
    persona, servicio_desembolso
from .comun import ErrorEva, correlacion_valida, fijar_correlacion, restaurar_correlacion
from .config import Config
from .contratos import DecisionIn, DesembolsoIn, RevocacionIn, SituacionIn, SobreExpediente
from .envios import DespachadorResultados, Trabajador
from .servicio import Servicio

VERSION = "0.5.0"
log = logging.getLogger("evaluacion")


class _FormatoJson(logging.Formatter):
    def format(self, registro: logging.LogRecord) -> str:
        datos = {"timestamp": self.formatTime(registro, "%Y-%m-%dT%H:%M:%S"), "nivel": registro.levelname,
                 "modulo": "EVALUACION", "mensaje": registro.getMessage()}
        datos.update(getattr(registro, "contexto", {}))
        return json.dumps(datos, ensure_ascii=False)


def _configurar_registros() -> None:
    raiz = logging.getLogger("evaluacion")
    if not raiz.handlers:
        salida = logging.StreamHandler(sys.stdout)
        salida.setFormatter(_FormatoJson())
        raiz.addHandler(salida)
        raiz.setLevel(logging.INFO)
        raiz.propagate = False


def crear_motor(config: Config, *, sin_pool: bool = False) -> Engine:
    opciones = {"poolclass": NullPool} if sin_pool else {"pool_pre_ping": True, "pool_recycle": 1800}
    return create_engine(config.database_url, isolation_level="READ COMMITTED", hide_parameters=True,
                         connect_args={"connect_timeout": 5, "init_command": "SET time_zone = '+00:00'"},
                         **opciones)


class Contexto:
    """Lo que la API necesita en ejecución: base, reglas, verificador de sesiones y envíos."""

    def __init__(self, config: Config, *, engine: Engine | None = None, verificador: VerificadorCoreDb | None = None,
                 transporte_sol: httpx.BaseTransport | None = None):
        self.config = config
        self.engine = engine or crear_motor(config)
        self.verificador = verificador or VerificadorCoreDb(config.coredb_url, config.timeout_seg,
                                                            config.sesion_cache_seg)
        self.servicio = Servicio(self.engine, config)
        self.despachador = DespachadorResultados(self.engine, config, transporte_sol)
        self._trabajador: Trabajador | None = None

    def iniciar(self) -> None:
        if self.config.envio_intervalo_seg > 0:
            self._trabajador = Trabajador(self.despachador, self.config.envio_intervalo_seg)
            self._trabajador.start()

    def cerrar(self) -> None:
        if self._trabajador:
            self._trabajador.detener()
            self._trabajador.join(timeout=5)
        self.despachador.cerrar()
        self.engine.dispose()


def _servicio(request: Request) -> Servicio:
    return request.app.state.ctx.servicio


async def _cuerpo_json(request: Request) -> dict:
    """El sobre tal como llegó, para guardarlo y compararlo; Starlette ya lo leyó y lo reutiliza."""
    return await request.json()


def _error(estado: int, codigo: str, mensaje: str, detalle: dict | None = None) -> JSONResponse:
    cuerpo = {"code": codigo, "message": mensaje}
    if detalle:
        cuerpo["details"] = detalle
    return JSONResponse(status_code=estado, content={"error": cuerpo})


def crear_app(config: Config | None = None, *, contexto: Contexto | None = None) -> FastAPI:
    """Sin argumentos lee la configuración del entorno al arrancar; las pruebas pasan su contexto."""

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI):
        _configurar_registros()
        if getattr(app.state, "ctx", None) is None:
            app.state.ctx = Contexto(config or Config.desde_entorno())
        app.state.ctx.iniciar()
        try:
            yield
        finally:
            app.state.ctx.cerrar()

    app = FastAPI(
        title="BNA · Evaluación Crediticia", version=VERSION, lifespan=ciclo_de_vida,
        description=(
            "Módulo 12 de la Línea de Créditos. Recibe el expediente de Solicitud (CR-INT-02), registra la "
            "situación financiera, aplica la regla provisional RN-EVA-002-P, devuelve el resultado a Solicitud "
            "(CR-INT-03) y ofrece la aprobación vigente a Desembolso (CR-INT-04), con el calendario de SOL sin "
            "cambios. El personal entra con el token de COREDB; SOL, con su token de servicio; Desembolso, con "
            "su usuario de servicio de COREDB. Montos como texto decimal (\"500.00\")."),
    )
    app.state.ctx = contexto

    @app.middleware("http")
    async def correlacion_y_registro(request: Request, call_next):
        correlacion = correlacion_valida(request.headers.get("X-Correlation-ID"))
        marca = fijar_correlacion(correlacion)
        inicio = time.perf_counter()
        try:
            respuesta = await call_next(request)
        finally:
            restaurar_correlacion(marca)
        respuesta.headers["X-Correlation-ID"] = correlacion
        ruta = request.scope.get("route")
        log.info("peticion", extra={"contexto": {
            "metodo": request.method, "ruta": getattr(ruta, "path", request.url.path),
            "estado": respuesta.status_code, "duracion_ms": round((time.perf_counter() - inicio) * 1000, 1),
            "correlacion": correlacion}})
        return respuesta

    @app.exception_handler(ErrorEva)
    async def _error_eva(_request: Request, exc: ErrorEva):
        return _error(exc.estado, exc.codigo, exc.mensaje, exc.detalle)

    @app.exception_handler(RequestValidationError)
    async def _error_validacion(_request: Request, exc: RequestValidationError):
        # Como COREDB: dice qué campo falló, sin repetir los valores recibidos (pueden ser datos personales).
        return JSONResponse(status_code=422, content={"detail": [
            {"loc": list(e.get("loc", ())), "type": e.get("type"), "msg": e.get("msg")} for e in exc.errors()]})

    @app.exception_handler(DBAPIError)
    async def _error_base(_request: Request, exc: DBAPIError):
        original = getattr(exc, "orig", None)
        codigo = original.args[0] if original is not None and original.args else None
        if codigo == 1644:  # SIGNAL de un trigger: una regla de datos que la aplicación no debió romper
            return _error(409, "REGLA_DE_DATOS", str(original.args[1]))
        log.error("Error de base de datos", extra={"contexto": {"error": type(exc).__name__}})
        return _error(503, "BASE_NO_DISPONIBLE", "La base de Evaluación no respondió. Intenta de nuevo.")

    # ------------------------------------------------------------------ Salud
    @app.get("/salud", tags=["Estado"], summary="El proceso y su base responden")
    def salud(request: Request):
        try:
            with request.app.state.ctx.engine.connect() as c:
                c.execute(text("SELECT 1"))
        except DBAPIError:
            return _error(503, "BASE_NO_DISPONIBLE", "La base de Evaluación no responde.")
        ctx = request.app.state.ctx
        return {"estado": "ok", "modulo": "EVALUACION", "version": VERSION,
                "resultadosASol": "configurado" if ctx.despachador.configurado else "pendiente: SOL en modo SIMULADO"}

    # ------------------------------------------------------------------ CR-INT-02 (SOL)
    t02 = "CR-INT-02 Solicitud a Evaluación"

    @app.post("/eva/applications", tags=[t02], status_code=201,
              summary="Recibir el expediente de una versión de solicitud",
              responses={200: {"description": "Repetición: el mismo acuse"},
                         409: {"description": "Operación reutilizada o versión ya recibida"}})
    def recibir_expediente(sobre: SobreExpediente, request: Request, crudo: dict = Depends(_cuerpo_json),
                           _sol: str = Depends(canal_sol), x_idempotency_key: str | None = Header(default=None)):
        if x_idempotency_key is not None and x_idempotency_key != sobre.idOperacion:
            raise ErrorEva(422, "CLAVE_DISTINTA", "X-Idempotency-Key debe ser igual a idOperacion.")
        acuse, nuevo = _servicio(request).recibir_expediente(sobre, crudo)
        return JSONResponse(status_code=201 if nuevo else 200, content=acuse)

    @app.get("/eva/operations/{id_operacion}", tags=[t02], summary="Consultar la recepción de una operación",
             responses={404: {"description": "No recibido: SOL puede enviarlo"}})
    def consultar_operacion(id_operacion: str, request: Request, _sol: str = Depends(canal_sol)):
        acuse = _servicio(request).acuse(id_operacion)
        if acuse is None:
            raise ErrorEva(404, "OPERACION_NO_RECIBIDA", "Evaluación no recibió esa operación.")
        return acuse

    # ------------------------------------------------------------------ CR-INT-04 (Desembolso)
    t04 = "CR-INT-04 Evaluación a Desembolso"

    @app.get("/eva/v1/aprobaciones", tags=[t04], summary="Buscar aprobaciones por documento o crédito")
    def buscar_aprobaciones(request: Request, numeroDocumento: str | None = Query(None, max_length=20),
                            codCredito: str | None = Query(None, max_length=20),
                            estado: Literal["VIGENTE", "VENCIDA", "DESEMBOLSADA", "REVOCADA"] | None = None,
                            perfil: Perfil = Depends(lector_aprobaciones)):
        return {"items": _servicio(request).buscar_aprobaciones(perfil, numeroDocumento, codCredito, estado)}

    @app.get("/eva/v1/aprobaciones/{id_aprobacion}", tags=[t04], summary="Una aprobación, con el calendario de SOL")
    def obtener_aprobacion(id_aprobacion: str, request: Request, perfil: Perfil = Depends(lector_aprobaciones)):
        return _servicio(request).obtener_aprobacion(id_aprobacion, perfil)

    @app.post("/eva/v1/aprobaciones/{id_aprobacion}/desembolso", tags=[t04],
              summary="Registrar que la aprobación se desembolsó (solo Desembolso)")
    def registrar_desembolso(id_aprobacion: str, datos: DesembolsoIn, request: Request,
                             perfil: Perfil = Depends(servicio_desembolso)):
        return _servicio(request).registrar_desembolso(id_aprobacion, datos, perfil)

    # ------------------------------------------------------------------ Personal
    tan = "Analista"

    @app.get("/eva/v1/evaluaciones", tags=[tan], summary="Bandeja de evaluaciones")
    def listar_evaluaciones(request: Request,
                            estado: Literal["PENDIENTE", "EN_REVISION", "APROBADO", "OBSERVADO", "RECHAZADO"] | None = None,
                            buscar: str | None = Query(None, max_length=80), limite: int = Query(50, ge=1, le=200),
                            perfil: Perfil = Depends(persona(*LECTURA))):
        return _servicio(request).listar_evaluaciones(perfil, estado, buscar, limite)

    @app.get("/eva/v1/evaluaciones/{id_evaluacion}", tags=[tan], summary="Expediente, evaluación e historial")
    def detalle_evaluacion(id_evaluacion: str, request: Request, perfil: Perfil = Depends(persona(*LECTURA))):
        return _servicio(request).detalle(id_evaluacion, perfil)

    @app.post("/eva/v1/evaluaciones/{id_evaluacion}/situacion-financiera", tags=[tan],
              summary="Registrar la situación financiera y aplicar la regla")
    def registrar_situacion(id_evaluacion: str, datos: SituacionIn, request: Request,
                            perfil: Perfil = Depends(persona(EVALUAR))):
        return _servicio(request).registrar_situacion(id_evaluacion, datos, perfil)

    @app.post("/eva/v1/evaluaciones/{id_evaluacion}/decision", tags=[tan],
              summary="Decidir un caso EN_REVISION: aprobar, observar (SOL corrige) o rechazar")
    def decidir(id_evaluacion: str, datos: DecisionIn, request: Request, perfil: Perfil = Depends(persona(DECIDIR))):
        return _servicio(request).decidir(id_evaluacion, datos, perfil)

    @app.post("/eva/v1/aprobaciones/{id_aprobacion}/revocacion", tags=[tan], summary="Revocar una aprobación vigente")
    def revocar(id_aprobacion: str, datos: RevocacionIn, request: Request, perfil: Perfil = Depends(persona(DECIDIR))):
        return _servicio(request).revocar(id_aprobacion, datos, perfil)

    @app.get("/eva/v1/envios", tags=[tan], summary="Resultados por entregar a Solicitud (CR-INT-03)")
    def listar_envios(request: Request, estado: Literal["PENDIENTE", "ENTREGADO", "ERROR"] | None = None,
                      limite: int = Query(50, ge=1, le=200), _perfil: Perfil = Depends(persona(*LECTURA))):
        return {"items": _servicio(request).listar_envios(estado, limite),
                "configurado": request.app.state.ctx.despachador.configurado}

    @app.post("/eva/v1/envios/{id_operacion}/reintento", tags=[tan], summary="Reintentar un envío en ERROR")
    def reintentar_envio(id_operacion: str, request: Request, perfil: Perfil = Depends(persona(DECIDIR))):
        return _servicio(request).reintentar_envio(id_operacion, perfil)

    @app.get("/eva/v1/historial", tags=[tan], summary="Últimos eventos del módulo")
    def historial(request: Request, limite: int = Query(100, ge=1, le=500),
                  _perfil: Perfil = Depends(persona(AUDITAR, DECIDIR))):
        return {"items": _servicio(request).historial(limite)}

    return app


app = crear_app()
