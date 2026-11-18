"""Middleware de observabilidad: logging de peticiones y correlación."""

import logging
import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


log = logging.getLogger("bna.atm")


class ObservabilidadMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        inicio = time.perf_counter()
        # Correlation ID: usar el del cliente o generar uno
        corr_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.state.correlation_id = corr_id

        # Log de entrada
        log.info("%s %s corr=%s", request.method, request.url.path, corr_id[:8])

        try:
            response = await call_next(request)
        except Exception as e:
            log.exception("Error en %s %s corr=%s: %s", request.method, request.url.path, corr_id[:8], e)
            raise

        duracion_ms = round((time.perf_counter() - inicio) * 1000)
        # Propagar correlation ID en la respuesta
        response.headers["X-Correlation-ID"] = corr_id
        log.info("%s %s -> %s en %d ms corr=%s",
                 request.method, request.url.path, response.status_code, duracion_ms, corr_id[:8])
        return response


def registrar_middleware(app):
    app.add_middleware(ObservabilidadMiddleware)