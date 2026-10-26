from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from CUENTAS import respuestas
from CUENTAS.errores import traducir
from CUENTAS.exceptions import CuentasError
from CUENTAS.observabilidad import registrar_middleware
from CUENTAS.routers import cuentas


def montar_en(app: FastAPI) -> None:
    registrar_middleware(app)
    app.include_router(cuentas.router)

    @app.exception_handler(CuentasError)
    async def _cuentas_error(request: Request, exc: CuentasError):
        status, error_code = traducir(exc.code, exc.status_code)
        return respuestas.error(request, status, error_code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validacion(request: Request, exc: RequestValidationError):
        detalle = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        return respuestas.error(
            request, 400, "ERR-VALIDACION-ESQUEMA",
            "Los parametros de entrada no cumplen la especificacion tecnica requerida", detalle,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        return respuestas.error(request, exc.status_code, f"ERR-HTTP-{exc.status_code}", str(exc.detail))
