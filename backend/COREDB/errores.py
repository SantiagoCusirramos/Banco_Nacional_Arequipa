"""Errores de la API y su traducción desde la base."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError

# Los rechazos de la base empiezan con el código de la regla.
ESTADOS_POR_REGLA = {
    "BNA-CUENTA": 404,
    "BNA-DESBLOQUEO": 403,
    "BNA-IDEMPOTENCIA": 409,
}
# El mensaje de la base incluye saldos o consumos, que no se devuelven al cliente.
MENSAJES_POR_REGLA = {
    "BNA-DESBLOQUEO": "El desbloqueo de tarjetas no está disponible: pendiente de un cliente de Seguridad.",
    "BNA-SALDO": "Saldo disponible insuficiente.",
    "RN-TOP-001": "Se superó el tope diario del canal.",
}
ERROR_REGLA = 1644          # SIGNAL de core.fallar
ERROR_DUPLICADO = 1062
ERRORES_DATOS = {1048, 1216, 1217, 1264, 1292, 1366, 1406, 1451, 1452, 3819}
ERRORES_REINTENTABLES = {1205, 1213}  # espera de bloqueo y deadlock


class ErrorCoreDb(Exception):
    def __init__(self, code: str, message: str, status_code: int = 422):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ErrorBaseDatos(ErrorCoreDb):
    @staticmethod
    def _codigo(exc: DBAPIError) -> int | None:
        argumentos = getattr(exc.orig, "args", ())
        return argumentos[0] if argumentos else None

    @classmethod
    def es_reintentable(cls, exc: DBAPIError) -> bool:
        return cls._codigo(exc) in ERRORES_REINTENTABLES

    @classmethod
    def desde(cls, exc: DBAPIError) -> ErrorCoreDb:
        codigo = cls._codigo(exc)
        mensaje = str(exc.orig.args[1]) if len(exc.orig.args) > 1 else ""
        if codigo == ERROR_REGLA:
            regla = mensaje.split(":", 1)[0]
            return cls(regla, MENSAJES_POR_REGLA.get(regla, mensaje), ESTADOS_POR_REGLA.get(regla, 422))
        if codigo == ERROR_DUPLICADO:
            return cls("REGISTRO_DUPLICADO", "Ya existe un registro con esos datos.", 409)
        if codigo in ERRORES_DATOS:
            return cls("DATOS_INVALIDOS", "Los datos no cumplen las reglas de la base.", 422)
        raise exc


def _ubicacion(parte: str | int) -> str | int:
    if isinstance(parte, int):
        return parte
    return parte.encode("utf-8", "backslashreplace").decode("utf-8")


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorCoreDb)
    async def _error_core_db(request: Request, exc: ErrorCoreDb):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(DBAPIError)
    async def _error_base_datos(request: Request, exc: DBAPIError):
        # Un deadlock o una espera agotada fuera de con_reintentos, como en una lectura.
        if not ErrorBaseDatos.es_reintentable(exc):
            raise exc
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "CONFLICTO_CONCURRENCIA",
                    "message": "La operación no pudo completarse por concurrencia; reintente.",
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def _error_validacion(request: Request, exc: RequestValidationError):
        # Sin los valores recibidos: pueden incluir contraseñas.
        return JSONResponse(
            status_code=422,
            content={
                "detail": [
                    {"loc": [_ubicacion(p) for p in e["loc"]], "type": e["type"]}
                    for e in exc.errors()
                ]
            },
        )
