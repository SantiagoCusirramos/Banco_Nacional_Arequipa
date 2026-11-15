"""X-Correlation-ID: se recibe o se genera, se propaga al Bus y se devuelve."""
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware

from .ids import uuid7

correlacion_actual: ContextVar[str] = ContextVar("correlacion_actual", default="")


def correlation_id() -> str:
    valor = correlacion_actual.get()
    if not valor:
        valor = uuid7()
        correlacion_actual.set(valor)
    return valor


class MiddlewareCorrelacion(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        valor = request.headers.get("X-Correlation-ID") or uuid7()
        token = correlacion_actual.set(valor[:36])
        try:
            respuesta = await call_next(request)
        finally:
            correlacion_actual.reset(token)
        respuesta.headers["X-Correlation-ID"] = valor[:36]
        return respuesta
