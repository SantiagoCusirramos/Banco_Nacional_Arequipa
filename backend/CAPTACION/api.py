from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from CAPTACION import respuestas
from CAPTACION.errores import CaptacionError
from CAPTACION.observabilidad import registrar_middleware
from CAPTACION.routers import captacion, referencias


def _http(status: int) -> int:
    # ITIL-02: 422 se homologa a 400 en las rutas del personal.
    return 400 if status == 422 else status


def montar_en(app: FastAPI) -> None:
    registrar_middleware(app)
    app.include_router(captacion.router)
    app.include_router(referencias.router)

    @app.exception_handler(CaptacionError)
    async def _captacion(request: Request, exc: CaptacionError):
        return respuestas.error(request, _http(exc.status_code), exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validacion(request: Request, exc: RequestValidationError):
        # Sin `input`: no se devuelven los valores recibidos (documentos, correos, celulares).
        detalle = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        return respuestas.error(request, 400, "ERR-VALIDACION-ESQUEMA",
                                "Los datos de entrada no cumplen la especificación", detalle)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        return respuestas.error(request, _http(exc.status_code), f"ERR-HTTP-{exc.status_code}", str(exc.detail))
