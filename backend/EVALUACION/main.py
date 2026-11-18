"""API de Evaluación Crediticia (módulo 12, Línea de Créditos). Puerto 8015 en el producto.

    uvicorn EVALUACION.main:app --port 8015      (desde backend/)

No tiene base propia: todo se guarda en COREDB (`creditos.*`, CONTRATO_CREDITOS.md §3).

Rutas:
  CR-INT-02  POST /eva/applications, GET /eva/operations/{idOperacion}     SOL, con su token
  Personal   /eva/v1/solicitudes..., /eva/v1/evaluaciones/{id}/decision,  token de COREDB de la
             /eva/v1/aprobaciones, /eva/v1/catalogo, /eva/v1/resultados-sol persona, reenviado
  CR-INT-03  lo entrega un trabajador interno a SOL (envios.py)
"""
from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from contextlib import asynccontextmanager
from typing import Literal

import httpx
from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .auth import DECIDIR, EVALUAR, VER, Sesion, VerificadorCoreDb, canal_sol, persona
from .comun import ErrorEva, correlacion_valida, fijar_correlacion, restaurar_correlacion
from .config import Config
from .contratos import DecisionIn, RevocacionIn, SituacionIn, SobreExpediente, expediente_coredb, \
    validar_expediente
from .coredb import ClienteCoreDb
from .envios import DespachadorResultados, Trabajador

VERSION = "1.0.0"
log = logging.getLogger("evaluacion")
BASE = "/coredb/creditos"

EstadoSolicitud = Literal["REGISTRADA", "EN_EVALUACION", "APROBADA", "RECHAZADA", "DESEMBOLSADA"]


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


class Contexto:
    """Lo que la API necesita en ejecución: COREDB, verificador de sesiones y envíos a SOL."""

    def __init__(self, config: Config, *, transporte_coredb: httpx.BaseTransport | None = None,
                 transporte_sol: httpx.BaseTransport | None = None):
        self.config = config
        self.coredb = ClienteCoreDb(config.coredb_url, config.servicio_usuario, config.servicio_secreto,
                                    timeout=config.timeout_seg, transporte=transporte_coredb,
                                    bus_token=config.bus_token)
        self.verificador = VerificadorCoreDb(config.coredb_url, config.timeout_seg, config.sesion_cache_seg,
                                             transporte=transporte_coredb, bus_token=config.bus_token)
        self.despachador = DespachadorResultados(config, self.coredb, transporte_sol)
        self._trabajador: Trabajador | None = None

    def iniciar(self) -> None:
        if self.config.envio_intervalo_seg > 0 and self.despachador.configurado:
            self._trabajador = Trabajador(self.despachador, self.config.envio_intervalo_seg)
            self._trabajador.start()

    def cerrar(self) -> None:
        if self._trabajador:
            self._trabajador.detener()
            self._trabajador.join(timeout=5)
        self.despachador.cerrar()
        self.verificador.cerrar()
        self.coredb.cerrar()


def _error(estado: int, codigo: str, mensaje: str) -> JSONResponse:
    return JSONResponse(status_code=estado, content={"error": {"code": codigo, "message": mensaje}})


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
            "Módulo 12 de la Línea de Créditos, sin base propia. Recibe el expediente de Solicitud (CR-INT-02) y "
            "lo registra en COREDB con su usuario de servicio; el analista consulta, registra la situación "
            "financiera (COREDB corre la regla RN-EVA-002-P) y decide los casos OBSERVADO con su propio token de "
            "COREDB, que Evaluación reenvía; el resultado final vuelve a Solicitud (CR-INT-03). Montos como texto "
            "decimal (\"500.00\")."),
    )
    app.state.ctx = contexto

    def ctx(request: Request) -> Contexto:
        return request.app.state.ctx

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
        return _error(exc.estado, exc.codigo, exc.mensaje)

    @app.exception_handler(RequestValidationError)
    async def _error_validacion(_request: Request, exc: RequestValidationError):
        # Como COREDB: dice qué campo falló, sin repetir los valores recibidos (pueden ser datos personales).
        return JSONResponse(status_code=422, content={"detail": [
            {"loc": list(e.get("loc", ())), "type": e.get("type"), "msg": e.get("msg")} for e in exc.errors()]})

    # ------------------------------------------------------------------ Salud
    @app.get("/salud", tags=["Estado"], summary="COREDB responde y el usuario de servicio inicia sesión")
    def salud(request: Request):
        c = ctx(request)
        if not c.coredb.salud():
            return _error(503, "COREDB_NO_DISPONIBLE", "COREDB no responde.")
        try:
            c.coredb.token_servicio()
        except ErrorEva as exc:
            return _error(503, exc.codigo, exc.mensaje)
        return {"estado": "ok", "modulo": "EVALUACION", "version": VERSION,
                "resultadosASol": "configurado" if c.despachador.configurado else "pendiente: falta EVALUACION_SOL_URL"}

    # ------------------------------------------------------------------ CR-INT-02 (SOL)
    t02 = "CR-INT-02 Solicitud a Evaluación"

    @app.post("/eva/applications", tags=[t02], status_code=201,
              summary="Recibir el expediente de una versión de solicitud",
              responses={200: {"description": "Repetición: el mismo acuse"},
                         409: {"description": "IDEMPOTENCIA_CONFLICTO: la misma versión con otro contenido"},
                         422: {"description": "EXPEDIENTE_INCONSISTENTE, CLIENTE_NO_HABILITADO, CALENDARIO_INVALIDO "
                                              "o SOLICITUD_NO_ADMITIDA"}})
    def recibir_expediente(sobre: SobreExpediente, request: Request, _sol: str = Depends(canal_sol),
                           x_idempotency_key: str | None = Header(default=None)):
        """Registra la versión en COREDB y devuelve el acuse que SOL valida. COREDB reconoce la
        misma versión con el mismo contenido (200, el mismo acuse), así que reenviar es seguro."""
        if x_idempotency_key is not None and x_idempotency_key != sobre.idOperacion:
            raise ErrorEva(422, "CLAVE_DISTINTA", "X-Idempotency-Key debe ser igual a idOperacion.")
        validar_expediente(sobre)
        estado, acuse = ctx(request).coredb.como_servicio("POST", f"{BASE}/solicitudes", json=expediente_coredb(sobre))
        return JSONResponse(status_code=estado, content={
            "idSolicitud": sobre.idSolicitud, "versionSolicitud": sobre.versionSolicitud,
            "idOperacion": sobre.idOperacion, "idEvaluacion": acuse["idEvaluacion"], "ronda": acuse["ronda"],
            "acuse": f"ACK-{acuse['idEvaluacion']}"})

    @app.get("/eva/operations/{id_operacion}", tags=[t02], summary="Consultar la recepción de una operación",
             responses={404: {"description": "Sin registro de la operación: SOL puede enviarla"}})
    def consultar_operacion(id_operacion: str, _sol: str = Depends(canal_sol)):
        """Evaluación no guarda las operaciones de SOL: responde 404 y SOL reenvía el expediente, que
        COREDB reconoce por su versión y contenido sin registrarlo dos veces (devuelve el mismo acuse)."""
        raise ErrorEva(404, "OPERACION_NO_RECIBIDA",
                       "Evaluación no guarda operaciones: reenvía el expediente, que se reconoce sin duplicarse.")

    # ------------------------------------------------------------------ Personal
    tan = "Analista"

    @app.get("/eva/v1/solicitudes", tags=[tan], summary="Bandeja de solicitudes de crédito")
    def bandeja(request: Request, estado: EstadoSolicitud | None = None,
                codCliente: str | None = Query(None, min_length=1, max_length=12, pattern=r"^[A-Za-z0-9]+$"),
                limite: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                sesion: Sesion = Depends(persona(VER))):
        params = {"limite": limite, "offset": offset, "estado": estado, "codCliente": codCliente}
        _, datos = ctx(request).coredb.como_persona(
            sesion.token, "GET", f"{BASE}/solicitudes", params={k: v for k, v in params.items() if v is not None})
        return datos

    @app.get("/eva/v1/solicitudes/{id_solicitud}", tags=[tan], summary="Calendario, evaluaciones e historial")
    def detalle(id_solicitud: uuid.UUID, request: Request, sesion: Sesion = Depends(persona(VER))):
        return ctx(request).coredb.como_persona(sesion.token, "GET", f"{BASE}/solicitudes/{id_solicitud}")[1]

    @app.post("/eva/v1/solicitudes/{id_solicitud}/evaluaciones", tags=[tan],
              summary="Registrar la situación financiera y aplicar la regla")
    def evaluar(id_solicitud: uuid.UUID, datos: SituacionIn, request: Request,
                sesion: Sesion = Depends(persona(EVALUAR))):
        return ctx(request).coredb.como_persona(
            sesion.token, "POST", f"{BASE}/solicitudes/{id_solicitud}/evaluaciones", json=datos.a_coredb())[1]

    @app.post("/eva/v1/evaluaciones/{id_evaluacion}/decision", tags=[tan],
              summary="Decidir un resultado OBSERVADO: aprobar o rechazar")
    def decidir(id_evaluacion: uuid.UUID, datos: DecisionIn, request: Request,
                sesion: Sesion = Depends(persona(DECIDIR))):
        return ctx(request).coredb.como_persona(
            sesion.token, "POST", f"{BASE}/evaluaciones/{id_evaluacion}/decision", json=datos.model_dump())[1]

    @app.post("/eva/v1/solicitudes/{id_solicitud}/revocacion", tags=[tan],
              summary="Revocar una aprobación sin desembolso")
    def revocar(id_solicitud: uuid.UUID, datos: RevocacionIn, request: Request,
                sesion: Sesion = Depends(persona(DECIDIR))):
        return ctx(request).coredb.como_persona(
            sesion.token, "POST", f"{BASE}/solicitudes/{id_solicitud}/revocacion", json=datos.model_dump())[1]

    @app.get("/eva/v1/aprobaciones", tags=[tan], summary="Aprobaciones vigentes sin desembolso")
    def aprobaciones(request: Request,
                     codCliente: str | None = Query(None, min_length=1, max_length=12, pattern=r"^[A-Za-z0-9]+$"),
                     idSolicitud: uuid.UUID | None = None, sesion: Sesion = Depends(persona(VER))):
        params = {"codCliente": codCliente, "idSolicitud": str(idSolicitud) if idSolicitud else None}
        _, datos = ctx(request).coredb.como_persona(
            sesion.token, "GET", f"{BASE}/aprobaciones", params={k: v for k, v in params.items() if v is not None})
        return datos

    @app.get("/eva/v1/catalogo", tags=[tan], summary="Estados, reglas y vigencia de la aprobación")
    def catalogo(request: Request, sesion: Sesion = Depends(persona(VER))):
        return ctx(request).coredb.como_persona(sesion.token, "GET", "/coredb/catalogos/creditos")[1]

    @app.get("/eva/v1/resultados-sol", tags=[tan], summary="Resultados que se devuelven a Solicitud (CR-INT-03)")
    def resultados_sol(request: Request, _sesion: Sesion = Depends(persona(VER))):
        c = ctx(request)
        return {"configurado": c.despachador.configurado, "ventanaDias": c.config.envio_ventana_dias,
                "items": c.despachador.resultados()}

    return app


app = crear_app()
