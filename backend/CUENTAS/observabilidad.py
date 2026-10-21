import json
import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request

from CUENTAS import respuestas

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("BNA_SERVICE_LOGGER")
# httpx escribe lineas de texto; ITIL-02 pide solo JSON
logging.getLogger("httpx").setLevel(logging.WARNING)


def registrar_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def trazabilidad(request: Request, call_next):
        t0 = time.perf_counter()
        request.state.t0 = t0
        request.state.error_code = None
        request.state.uuid_transaccion = (
            request.headers.get("x-idempotency-key")
            or request.headers.get("x-correlation-id")
            or str(uuid4())
        )
        nivel, mensaje = None, "Ejecucion transaccional finalizada"
        try:
            response = await call_next(request)
        except Exception as exc:
            nivel = "CRITICAL"
            mensaje = f"Excepcion no controlada: {type(exc).__name__}: {str(exc)[:200]}"
            response = respuestas.error(
                request, 500, "ERR-INTERNO-SERVIDOR",
                "Ocurrio una falla tecnica no controlada al procesar la solicitud",
            )

        tiempo_ms = round((time.perf_counter() - t0) * 1000, 2)
        response.headers["X-Idempotency-Key"] = request.state.uuid_transaccion
        response.headers["X-Response-Time-MS"] = str(tiempo_ms)

        status = response.status_code
        if nivel is None:
            nivel = "INFO" if status < 400 else ("WARNING" if status < 500 else "ERROR")
        contexto = {}
        canal = request.headers.get("x-channel-id")
        if canal:
            contexto["canal"] = canal
        if request.state.error_code:
            contexto["error_code"] = request.state.error_code

        registro = {
            "timestamp": respuestas.ahora_iso(),
            "level": nivel,
            "uuid_transaccion": request.state.uuid_transaccion,
            "modulo": respuestas.MODULO,
            "endpoint": f"{request.method} {request.url.path}",
            "status_code": status,
            "tiempo_ms": tiempo_ms,
            "client_ip": request.client.host if request.client else "unknown",
            "mensaje": mensaje,
        }
        if contexto:
            registro["datos_contexto"] = contexto
        logger.log(getattr(logging, nivel), json.dumps(registro))
        return response
