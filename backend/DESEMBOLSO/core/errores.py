"""Formato unico de errores: {codigo, mensaje, detalle, correlation_id}."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .correlacion import correlation_id

log = logging.getLogger("desembolso")


class ErrorNegocio(Exception):
    def __init__(self, estado_http: int, codigo: str, mensaje: str, detalle: dict | None = None):
        super().__init__(mensaje)
        self.estado_http = estado_http
        self.codigo = codigo
        self.mensaje = mensaje
        self.detalle = detalle


class DependenciaNoDisponible(ErrorNegocio):
    """Un modulo contraparte no respondio. `incierto` indica que la operacion pudo ejecutarse."""

    def __init__(self, modulo: str, incierto: bool = False, causa: str = ""):
        super().__init__(503, "DEPENDENCIA_NO_DISPONIBLE", f"El servicio de {modulo} no está disponible",
                         {"modulo": modulo, "causa": causa})
        self.modulo = modulo
        self.incierto = incierto


def _cuerpo(codigo: str, mensaje: str, detalle=None) -> dict:
    return {"codigo": codigo, "mensaje": mensaje, "detalle": detalle, "correlation_id": correlation_id()}


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorNegocio)
    async def _negocio(_: Request, exc: ErrorNegocio):
        return JSONResponse(status_code=exc.estado_http, content=_cuerpo(exc.codigo, exc.mensaje, exc.detalle))

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError):
        errores = [{"campo": ".".join(str(p) for p in e["loc"][1:]), "mensaje": e["msg"]} for e in exc.errors()]
        return JSONResponse(status_code=422, content=_cuerpo("VALIDACION_ENTRADA", "Datos de entrada inválidos", errores))

    @app.exception_handler(Exception)
    async def _inesperado(_: Request, exc: Exception):
        log.exception("Error no controlado")
        return JSONResponse(status_code=500, content=_cuerpo("ERROR_INTERNO", "Ocurrió un error inesperado"))
