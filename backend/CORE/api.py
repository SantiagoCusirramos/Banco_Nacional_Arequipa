"""API unificada del CORE.

Todas las acciones listadas en `Contexto_BNA/Acciones CORE.md` se
exponen bajo un único prefijo `/core`, sirviendo como único puente
entre la BD `bna` y el resto del software (incluido el futuro Bus de
Servicios, RNF-22).
"""

from fastapi import APIRouter, Request
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


def montar_en(app) -> None:
    """Incluye el router de CORE en la aplicación FastAPI y registra el
    manejador de errores de negocio (RNF-29)."""
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
