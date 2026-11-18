"""Montaje de la API del módulo ATM."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from ATM import respuestas
from ATM.errores import traducir
from ATM.exceptions import AtmError
from ATM.observabilidad import registrar_middleware
from ATM.routers import atm


def montar_en(app: FastAPI) -> None:
    registrar_middleware(app)
    app.include_router(atm.router)

    @app.exception_handler(AtmError)
    async def _atm_error(request: Request, exc: AtmError):
        status, error_code = traducir(exc.code, exc.status_code)
        return respuestas.error(request, status, error_code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validacion(request: Request, exc: RequestValidationError):
        detalle = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        return respuestas.error(
            request, 400, "ERR-ATM-VALIDACION-ESQUEMA",
            "Los parametros de entrada no cumplen la especificacion tecnica requerida", detalle,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        return respuestas.error(request, exc.status_code, f"ERR-HTTP-{exc.status_code}", str(exc.detail))


STATIC_DIR = Path(__file__).resolve().parent / "static"


def montar_pantalla(app: FastAPI) -> None:
    """La pantalla (/), el panel técnico (/tecnico.html), el logo y las fuentes. Va al final:
    lo que no es una ruta de la API se busca en static/. StaticFiles resuelve la ruta y rechaza
    todo lo que quede fuera de esa carpeta (S-1: nada de ../config.py ni /proc/self/environ)."""
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="pantalla")
