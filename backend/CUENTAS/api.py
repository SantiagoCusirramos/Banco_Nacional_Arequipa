from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from CUENTAS.exceptions import CuentasError
from CUENTAS.routers import cuentas


def montar_en(app: FastAPI) -> None:
    app.include_router(cuentas.router)

    @app.exception_handler(CuentasError)
    async def _cuentas_error(request: Request, exc: CuentasError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {"code": exc.code, "message": exc.message, "details": exc.details},
                "correlation_id": request.headers.get("x-correlation-id"),
            },
        )
