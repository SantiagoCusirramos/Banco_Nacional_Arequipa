"""Dependencias de FastAPI para el módulo ATM."""

import uuid
from typing import Annotated
from fastapi import Depends, Header, HTTPException, Request
from pydantic import BaseModel

from ATM.config import settings
from ATM.core_client import CoreClient
from ATM.exceptions import AtmError
from ATM.errores import traducir


class ContextoOperacion(BaseModel):
    """Contexto extraído de cabeceras para operaciones que requieren idempotencia."""
    id_canal: str | None = None
    id_terminal: str | None = None
    idempotency_key: str
    correlation_id: str
    authorization: str | None = None


async def get_core_client() -> CoreClient:
    """Cliente HTTP para llamar a TARJETAS y CUENTAS por el Bus."""
    return CoreClient(
        base_url=settings.bus_base_url,
        timeout=settings.core_timeout_seconds,
        bus_token=settings.bus_token,
    )


def correlation_id(request: Request) -> str:
    """Correlation ID de la petición (cabecera o generado)."""
    return request.state.correlation_id


def autorizacion(authorization: Annotated[str | None, Header()] = None) -> str | None:
    """Token de autorización (Bearer) que se reenvía a los módulos downstream."""
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None


def idempotency_key(x_idempotency_key: Annotated[str | None, Header()] = None) -> str:
    """Llave de idempotencia (UUIDv4) obligatoria para operaciones que modifican estado."""
    if not x_idempotency_key:
        raise AtmError("ERR-ATM-HEADER-REQUERIDO", "Falta la cabecera X-Idempotency-Key", 400)
    try:
        uuid.UUID(x_idempotency_key, version=4)
    except ValueError:
        raise AtmError("ERR-ATM-HEADER-INVALIDO", "X-Idempotency-Key debe ser un UUIDv4", 400)
    return x_idempotency_key


def canal_o_terminal(
    id_canal: Annotated[str | None, Header()] = None,
    id_terminal: Annotated[str | None, Header()] = None,
) -> tuple[str | None, str | None]:
    """Valida que se indique exactamente uno de id_canal o id_terminal."""
    if (id_canal is None) == (id_terminal is None):
        raise AtmError("ERR-ATM-CANAL_O_TERMINAL", "Se debe indicar id_canal o id_terminal, uno de los dos", 400)
    return id_canal, id_terminal


def contexto_operacion(
    request: Request,
    cid: str = Depends(correlation_id),
    token: str | None = Depends(autorizacion),
    key: str = Depends(idempotency_key),
) -> ContextoOperacion:
    """Contexto completo para operaciones de débito (autorizar, confirmar).
    Los campos id_canal/id_terminal vienen en el cuerpo de la petición (validados por Pydantic)."""
    return ContextoOperacion(
        id_canal=None,
        id_terminal=None,
        idempotency_key=key,
        correlation_id=cid,
        authorization=token,
    )