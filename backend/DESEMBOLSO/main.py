"""API de Desembolso (módulo 13, Línea de Créditos). Puerto 8016 en el producto.

    uvicorn DESEMBOLSO.main:app --port 8016      (desde backend/)

No tiene base propia: todo se guarda en COREDB (`creditos.*`, CONTRATO_CREDITOS.md §4).

Rutas, todas con el token de COREDB de la persona:
  /api/v1/sesion                       perfil en Desembolso (OPERADOR, SUPERVISOR, AUDITOR)
  /api/v1/identidad                    verificación del documento en ventanilla (evidencia IDENTIDAD)
  /api/v1/aprobaciones                 aprobaciones vigentes, leídas de COREDB (CR-INT-04)
  /api/v1/clientes/{cod}/cuentas       cuentas del titular y si admiten el abono
  /api/v1/ordenes...                   preparar, cambiar la cuenta, validar, confirmar, rechazar, monitor
  /api/v1/conciliacion                 órdenes confirmadas frente a lo abonado
Lo que hace la persona va con su token, que Desembolso reenvía; las aprobaciones y las cuentas
se leen con el usuario de servicio svc-desembolso.
"""
from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from contextlib import asynccontextmanager
from datetime import date
from typing import Any, Literal

import httpx
from fastapi import Depends, FastAPI, Header, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .auth import CONCILIAR, DESEMBOLSAR, VER, Sesion, VerificadorCoreDb, persona
from .comun import ErrorDes, correlacion_valida, fijar_correlacion, restaurar_correlacion
from .config import Config
from .contratos import CuentaIn, IdentidadIn, OrdenIn, RechazoIn, ValidacionIn
from .coredb import ClienteCoreDb

VERSION = "2.0.0"
log = logging.getLogger("desembolso")
BASE = "/coredb/creditos"

EstadoOrden = Literal["PREPARADA", "VALIDADA", "EN_PROCESO", "POR_VERIFICAR", "CONFIRMADA", "RECHAZADA",
                      "REVERTIDA"]
ABIERTAS = ("PREPARADA", "VALIDADA")
CodCliente = Path(min_length=1, max_length=12, pattern=r"^[A-Za-z0-9]+$")
CodClienteQuery = Query(None, min_length=1, max_length=12, pattern=r"^[A-Za-z0-9]+$")

# Rol de COREDB → perfil en Desembolso. COREDB no tiene un rol de supervisor: lo hace el
# ADMINISTRADOR (decisión del equipo pendiente, T6). Otro rol con VER_CREDITO solo consulta.
PERFILES = {"OPERADOR": "OPERADOR", "ADMINISTRADOR": "SUPERVISOR", "AUDITOR": "AUDITOR"}


def perfil_de(rol: str) -> str:
    return PERFILES.get(rol, "CONSULTA")


def elegibilidad(cuenta: dict, cod_cliente: str, moneda: str | None) -> tuple[bool, str | None]:
    """Si la cuenta admite el abono: de ahorros, INDIVIDUAL, ACTIVA, del titular y en la moneda del
    crédito. Es un aviso para la pantalla: COREDB lo vuelve a comprobar al preparar y al confirmar."""
    if cuenta["regimen"] != "INDIVIDUAL":
        return False, "CUENTA_MANCOMUNADA"
    if cuenta["titulares"] != [cod_cliente]:
        return False, "TITULAR_DISTINTO"
    if cuenta["estado_cuenta"] != "ACTIVA":
        return False, "CUENTA_NO_ACTIVA"
    if moneda and cuenta["moneda"] != moneda:
        return False, "MONEDA_DISTINTA"
    return True, None


class _FormatoJson(logging.Formatter):
    def format(self, registro: logging.LogRecord) -> str:
        datos = {"timestamp": self.formatTime(registro, "%Y-%m-%dT%H:%M:%S"), "nivel": registro.levelname,
                 "modulo": "DESEMBOLSO", "mensaje": registro.getMessage()}
        datos.update(getattr(registro, "contexto", {}))
        return json.dumps(datos, ensure_ascii=False)


def _configurar_registros() -> None:
    raiz = logging.getLogger("desembolso")
    if not raiz.handlers:
        salida = logging.StreamHandler(sys.stdout)
        salida.setFormatter(_FormatoJson())
        raiz.addHandler(salida)
        raiz.setLevel(logging.INFO)
        raiz.propagate = False


class Contexto:
    """Lo que la API necesita en ejecución: COREDB y el verificador de sesiones."""

    def __init__(self, config: Config, *, transporte_coredb: httpx.BaseTransport | None = None):
        self.config = config
        self.coredb = ClienteCoreDb(config.coredb_url, config.servicio_usuario, config.servicio_secreto,
                                    timeout=config.timeout_seg, transporte=transporte_coredb)
        self.verificador = VerificadorCoreDb(config.coredb_url, config.timeout_seg, config.sesion_cache_seg,
                                             transporte=transporte_coredb)

    def cerrar(self) -> None:
        self.verificador.cerrar()
        self.coredb.cerrar()


def _error(estado: int, codigo: str, mensaje: str) -> JSONResponse:
    return JSONResponse(status_code=estado, content={"error": {"code": codigo, "message": mensaje}})


def _sin_vacios(params: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in params.items() if v is not None}


def crear_app(config: Config | None = None, *, contexto: Contexto | None = None) -> FastAPI:
    """Sin argumentos lee la configuración del entorno al arrancar; las pruebas pasan su contexto."""

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI):
        _configurar_registros()
        if getattr(app.state, "ctx", None) is None:
            app.state.ctx = Contexto(config or Config.desde_entorno())
        try:
            yield
        finally:
            app.state.ctx.cerrar()

    app = FastAPI(
        title="BNA · Desembolso de Créditos", version=VERSION, lifespan=ciclo_de_vida,
        description=(
            "Módulo 13 de la Línea de Créditos, sin base propia. El operador verifica el documento del titular, "
            "elige una aprobación vigente (leída de COREDB, CR-INT-04) y una cuenta de ahorros individual del "
            "titular, prepara la orden, registra la identidad del día y confirma. COREDB abona, crea el crédito "
            "con su calendario oficial y deja la solicitud DESEMBOLSADA en una sola operación; confirmar otra vez "
            "devuelve lo mismo sin otro abono. Lo que hace la persona va con su token de COREDB, que Desembolso "
            "reenvía. Montos como texto decimal (\"15000.00\")."),
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

    @app.exception_handler(ErrorDes)
    async def _error_des(_request: Request, exc: ErrorDes):
        return _error(exc.estado, exc.codigo, exc.mensaje)

    @app.exception_handler(RequestValidationError)
    async def _error_validacion(_request: Request, exc: RequestValidationError):
        # Como COREDB: dice qué campo falló, sin repetir los valores recibidos (documentos, cuentas).
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
        except ErrorDes as exc:
            return _error(503, exc.codigo, exc.mensaje)
        return {"estado": "ok", "modulo": "DESEMBOLSO", "version": VERSION}

    # ------------------------------------------------------------------ Sesión e identidad
    tes = "Operación en agencia"

    @app.get("/api/v1/sesion", tags=[tes], summary="Perfil de la persona en Desembolso")
    def sesion(sesion: Sesion = Depends(persona(VER, DESEMBOLSAR))):
        p = sesion.perfil
        return {"usuario": p.usuario, "rol": p.rol, "perfil": perfil_de(p.rol),
                "puedeOperar": p.puede(DESEMBOLSAR), "puedeConciliar": p.puede(CONCILIAR)}

    @app.post("/api/v1/identidad", tags=[tes], status_code=201,
              summary="Verificar el documento del titular en ventanilla",
              responses={403: {"description": "PERMISO_DENEGADO"}})
    def verificar_identidad(datos: IdentidadIn, request: Request, sesion: Sesion = Depends(persona(DESEMBOLSAR))):
        """El operador revisó el documento original y a la persona. COREDB registra la verificación y
        la aprueba solo para un cliente ACTIVO; su `idValidacion` es la evidencia IDENTIDAD de la orden,
        válida el mismo día (fecha de Lima). Sin identidad verificada, la respuesta no dice si el
        documento es de un cliente."""
        _, v = ctx(request).coredb.como_persona(sesion.token, "POST", "/coredb/clientes/validaciones/documento",
                                                json=datos.a_coredb())
        cliente = v.get("cliente") or {}
        nombre = " ".join(x for x in (cliente.get("nombres"), cliente.get("apellido_paterno"),
                                      cliente.get("apellido_materno")) if x)
        return JSONResponse(status_code=201, content={
            "idValidacion": v["id_validacion"], "resultado": v["resultado"], "motivo": v.get("motivo"),
            "codCliente": cliente.get("cod_cliente"), "nombre": nombre or None,
            "estadoCliente": cliente.get("estado_cliente")})

    @app.get("/api/v1/aprobaciones", tags=[tes], summary="Aprobaciones vigentes sin desembolso (CR-INT-04)",
             responses={422: {"description": "FILTRO_REQUERIDO: indica codCliente o idSolicitud"}})
    def aprobaciones(request: Request, codCliente: str | None = CodClienteQuery,
                     idSolicitud: uuid.UUID | None = None, _sesion: Sesion = Depends(persona(VER, DESEMBOLSAR))):
        """Se leen de COREDB con el usuario de servicio: la última ronda aprobada, dentro de sus 30 días
        y sin desembolso confirmado, con el calendario de Solicitud sin cambios. `ordenAbierta` es la
        orden PREPARADA o VALIDADA que ya tiene, si la hay."""
        if not codCliente and not idSolicitud:
            raise ErrorDes(422, "FILTRO_REQUERIDO", "Indica el cliente o la solicitud.")
        c = ctx(request).coredb
        params = _sin_vacios({"codCliente": codCliente, "idSolicitud": str(idSolicitud) if idSolicitud else None})
        _, lista = c.como_servicio("GET", f"{BASE}/aprobaciones", params=params)
        for aprobacion in lista:
            _, ordenes = c.como_servicio("GET", f"{BASE}/ordenes", params={"idSolicitud": aprobacion["idSolicitud"]})
            abierta = next((o for o in ordenes if o["estado"] in ABIERTAS), None)
            aprobacion["ordenAbierta"] = (
                {"idOrden": abierta["idOrden"], "codigoOrden": abierta["codigoOrden"], "estado": abierta["estado"]}
                if abierta else None)
        return lista

    @app.get("/api/v1/clientes/{cod_cliente}/cuentas", tags=[tes],
             summary="Cuentas del titular y si admiten el abono")
    def cuentas(request: Request, cod_cliente: str = CodCliente,
                moneda: str | None = Query(None, pattern=r"^[A-Z]{3}$"),
                _sesion: Sesion = Depends(persona(DESEMBOLSAR))):
        """Las cuentas en las que el cliente es titular, leídas de COREDB con el usuario de servicio. Solo
        admite el abono una cuenta de ahorros INDIVIDUAL, ACTIVA, del titular y en la moneda del crédito;
        `motivo` dice por qué otra no: CUENTA_MANCOMUNADA, TITULAR_DISTINTO, CUENTA_NO_ACTIVA o
        MONEDA_DISTINTA."""
        _, lista = ctx(request).coredb.como_servicio("GET", "/coredb/cuentas", params={"cod_cliente": cod_cliente})
        resultado = []
        for cuenta in lista:
            elegible, motivo = elegibilidad(cuenta, cod_cliente, moneda)
            resultado.append({"numCuenta": cuenta["num_cuenta"], "moneda": cuenta["moneda"],
                              "regimen": cuenta["regimen"], "estadoCuenta": cuenta["estado_cuenta"],
                              "elegible": elegible, "motivo": motivo})
        return resultado

    # ------------------------------------------------------------------ Órdenes
    tor = "Órdenes de desembolso"

    @app.post("/api/v1/ordenes", tags=[tor], status_code=201, summary="Preparar la orden de una aprobación",
              responses={200: {"description": "La misma llave con el mismo contenido: la misma orden"},
                         409: {"description": "IDEMPOTENCIA_CONFLICTO"},
                         422: {"description": "APROBACION_NO_VIGENTE, CALENDARIO_INVALIDO, ORDEN_NO_ADMITIDA o "
                                              "CUENTA_NO_ELEGIBLE"}})
    def preparar(datos: OrdenIn, request: Request, llave: uuid.UUID = Header(alias="X-Idempotency-Key"),
                 sesion: Sesion = Depends(persona(DESEMBOLSAR))):
        """El importe es el monto aprobado. Se rechaza si la aprobación venció, si su primera cuota ya
        venció, si ya tiene una orden abierta o si la cuenta no es elegible."""
        estado, orden = ctx(request).coredb.como_persona(
            sesion.token, "POST", f"{BASE}/ordenes", json=datos.a_coredb(),
            cabeceras={"X-Idempotency-Key": str(llave)})
        return JSONResponse(status_code=estado, content=orden)

    @app.get("/api/v1/ordenes", tags=[tor], summary="Monitor de órdenes")
    def monitor(request: Request, estado: EstadoOrden | None = None, codCliente: str | None = CodClienteQuery,
                idSolicitud: uuid.UUID | None = None, limite: int = Query(50, ge=1, le=200),
                offset: int = Query(0, ge=0), sesion: Sesion = Depends(persona(VER))):
        params = _sin_vacios({"estado": estado, "codCliente": codCliente, "limite": limite, "offset": offset,
                              "idSolicitud": str(idSolicitud) if idSolicitud else None})
        return ctx(request).coredb.como_persona(sesion.token, "GET", f"{BASE}/ordenes", params=params)[1]

    @app.get("/api/v1/ordenes/{id_orden}", tags=[tor], summary="La orden, sus validaciones, bitácora y calendario",
             responses={404: {"description": "ORDEN_NO_ENCONTRADA"}})
    def detalle(id_orden: uuid.UUID, request: Request, sesion: Sesion = Depends(persona(VER))):
        """Agrega el calendario vigente de la solicitud: el PRELIMINAR de Solicitud antes del desembolso
        y el OFICIAL, su copia, después."""
        c = ctx(request).coredb
        _, orden = c.como_persona(sesion.token, "GET", f"{BASE}/ordenes/{id_orden}")
        _, solicitud = c.como_persona(sesion.token, "GET", f"{BASE}/solicitudes/{orden['idSolicitud']}")
        orden["estadoSolicitud"] = solicitud["estado"]
        orden["plazoMeses"] = solicitud["plazoMeses"]
        orden["calendario"] = solicitud["calendario"]
        return orden

    @app.put("/api/v1/ordenes/{id_orden}/cuenta", tags=[tor], summary="Cambiar la cuenta de la orden",
             responses={422: {"description": "ORDEN_NO_ADMITIDA o CUENTA_NO_ELEGIBLE"}})
    def cambiar_cuenta(id_orden: uuid.UUID, datos: CuentaIn, request: Request,
                       sesion: Sesion = Depends(persona(DESEMBOLSAR))):
        return ctx(request).coredb.como_persona(sesion.token, "PUT", f"{BASE}/ordenes/{id_orden}/cuenta",
                                                json=datos.model_dump())[1]

    @app.post("/api/v1/ordenes/{id_orden}/validaciones", tags=[tor], status_code=201,
              summary="Registrar una validación (IDENTIDAD con la verificación de hoy)",
              responses={422: {"description": "VALIDACION_NO_ADMITIDA u ORDEN_NO_ADMITIDA"}})
    def validar(id_orden: uuid.UUID, datos: ValidacionIn, request: Request,
                sesion: Sesion = Depends(persona(DESEMBOLSAR))):
        """Con la última IDENTIDAD y la última CUENTA aprobadas, la orden queda VALIDADA. La identidad
        vale el mismo día (T7): una verificación de otro día se rechaza."""
        estado, orden = ctx(request).coredb.como_persona(
            sesion.token, "POST", f"{BASE}/ordenes/{id_orden}/validaciones", json=datos.a_coredb())
        return JSONResponse(status_code=estado, content=orden)

    @app.post("/api/v1/ordenes/{id_orden}/confirmacion", tags=[tor], status_code=201,
              summary="Confirmar: abonar, crear el crédito y desembolsar la solicitud",
              responses={200: {"description": "Ya estaba confirmada: el mismo crédito y el mismo abono"},
                         422: {"description": "ORDEN_NO_ADMITIDA, APROBACION_NO_VIGENTE, VALIDACION_NO_ADMITIDA "
                                              "o CUENTA_NO_ELEGIBLE"}})
    def confirmar(id_orden: uuid.UUID, request: Request, sesion: Sesion = Depends(persona(DESEMBOLSAR))):
        """Una sola operación de COREDB: el abono, el crédito AL_DIA con su calendario OFICIAL y la
        solicitud DESEMBOLSADA. Si se pierde la respuesta, se repite: devuelve lo mismo sin otro abono."""
        estado, confirmada = ctx(request).coredb.como_persona(
            sesion.token, "POST", f"{BASE}/ordenes/{id_orden}/confirmacion")
        return JSONResponse(status_code=estado, content=confirmada)

    @app.post("/api/v1/ordenes/{id_orden}/rechazo", tags=[tor], summary="Rechazar la orden",
              responses={422: {"description": "ORDEN_NO_ADMITIDA"}})
    def rechazar(id_orden: uuid.UUID, datos: RechazoIn, request: Request,
                 sesion: Sesion = Depends(persona(DESEMBOLSAR))):
        """La aprobación sigue vigente y admite otra orden."""
        return ctx(request).coredb.como_persona(sesion.token, "POST", f"{BASE}/ordenes/{id_orden}/rechazo",
                                                json=datos.model_dump())[1]

    @app.get("/api/v1/conciliacion", tags=["Supervisión"],
             summary="Órdenes confirmadas frente a lo abonado, por día y moneda")
    def conciliacion(request: Request, fecha: date | None = None, sesion: Sesion = Depends(persona(CONCILIAR))):
        params = {"fecha": fecha.isoformat()} if fecha else {}
        return ctx(request).coredb.como_persona(sesion.token, "GET", f"{BASE}/conciliacion/desembolsos",
                                                params=params)[1]

    return app


app = crear_app()
