import time
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse

MODULO = "CUENTAS"


def ahora_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _uuid(request: Request) -> str:
    return getattr(request.state, "uuid_transaccion", None) or str(uuid4())


def exito(request: Request, data, status_code: int = 200,
          message: str = "Operacion ejecutada satisfactoriamente") -> JSONResponse:
    t0 = getattr(request.state, "t0", None)
    metadata = {
        "uuid_transaccion": _uuid(request),
        "timestamp": ahora_iso(),
        "modulo_emisor": MODULO,
    }
    if t0 is not None:
        metadata["tiempo_ejecucion_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    return JSONResponse(status_code=status_code, content={
        "success": True,
        "status_code": status_code,
        "message": message,
        "data": data,
        "metadata": metadata,
    })


def error(request: Request, status_code: int, error_code: str, message: str,
          details: dict | list | None = None) -> JSONResponse:
    request.state.error_code = error_code
    return JSONResponse(status_code=status_code, content={
        "success": False,
        "status_code": status_code,
        "error_code": error_code,
        "message": message,
        "details": details or {},
        "metadata": {
            "uuid_transaccion": _uuid(request),
            "timestamp": ahora_iso(),
            "modulo_emisor": MODULO,
        },
    })
