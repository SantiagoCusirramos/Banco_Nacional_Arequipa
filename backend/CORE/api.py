"""API unificada del CORE.

Todas las acciones listadas en `Contexto_BNA/Acciones CORE.md` se
exponen bajo un único prefijo `/core`, sirviendo como único puente
entre la BD `bna` y el resto del software (incluido el futuro Bus de
Servicios, RNF-22).
"""

from fastapi import APIRouter, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from CORE.exceptions import CoreError
from CORE.routers import admin, auth, catalogos, clientes, creditos, cuentas, movimientos, tarjetas

api_router = APIRouter(prefix="/core")


def _montar_error(exc: CoreError, request: Request) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        headers={"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
            "correlation_id": request.headers.get("x-correlation-id"),
        },
    )


def _ubicacion_segura(parte: str | int) -> str | int:
    """Una clave del JSON recibido puede traer texto que no se codifica en UTF-8."""
    if isinstance(parte, int):
        return parte
    return parte.encode("utf-8", "backslashreplace").decode("utf-8")


def _montar_error_validacion(exc: RequestValidationError) -> JSONResponse:
    """422 con ubicación y tipo del error, sin los valores recibidos.

    El manejador por defecto devuelve `input`, que puede incluir contraseñas,
    y falla con 500 si contiene un surrogate aislado. `msg` repite el tipo
    porque el frontend lee ese campo.
    """
    return JSONResponse(
        status_code=422,
        content={
            "detail": [
                {
                    "loc": [_ubicacion_segura(parte) for parte in error["loc"]],
                    "type": error["type"],
                    "msg": error["type"],
                }
                for error in exc.errors()
            ]
        },
    )


def montar_en(app) -> None:
    """Incluye el router de CORE en la aplicación FastAPI y registra los
    manejadores de errores de negocio (RNF-29) y de validación."""
    api_router.include_router(auth.router)
    api_router.include_router(clientes.router)
    api_router.include_router(catalogos.router) 
    api_router.include_router(cuentas.router)
    api_router.include_router(movimientos.router)
    api_router.include_router(tarjetas.router)
    api_router.include_router(creditos.router)
    api_router.include_router(admin.usuarios_router)
    api_router.include_router(admin.permisos_router)
    api_router.include_router(admin.auditoria_router)
    api_router.include_router(admin.reportes_router)
    app.include_router(api_router)

    @app.exception_handler(CoreError)
    async def _core_error_handler(request: Request, exc: CoreError):
        return _montar_error(exc, request)

    @app.exception_handler(RequestValidationError)
    async def _validacion_handler(request: Request, exc: RequestValidationError):
        return _montar_error_validacion(exc)
