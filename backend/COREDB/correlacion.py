"""X-Correlation-ID de una petición.

Es opcional: si falta, o no es un UUID, la API genera uno. Vuelve siempre en la
respuesta, también en las de error, y es el que queda en la bitácora.
"""

import uuid

from fastapi import Header, Request, Response

CABECERA = "X-Correlation-ID"


def correlacion(
    request: Request, response: Response, x_correlation_id: str | None = Header(default=None)
) -> uuid.UUID:
    try:
        valor = uuid.UUID(x_correlation_id) if x_correlation_id else uuid.uuid4()
    except ValueError:
        valor = uuid.uuid4()
    request.state.correlacion = str(valor)
    response.headers[CABECERA] = str(valor)
    return valor


def cabeceras_de_error(request: Request) -> dict[str, str]:
    """Para las respuestas de error, que no pasan por el `response` de la ruta."""
    valor = getattr(request.state, "correlacion", None)
    return {CABECERA: valor} if valor else {}
