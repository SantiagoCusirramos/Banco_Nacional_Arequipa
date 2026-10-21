from uuid import uuid4

from fastapi import Header

from CUENTAS.core_client import CoreClient
from CUENTAS.exceptions import CuentasError


def get_core_client():
    client = CoreClient()
    try:
        yield client
    finally:
        client.close()


def correlation_id(x_correlation_id: str | None = Header(default=None)) -> str:
    return x_correlation_id or str(uuid4())


def idempotency_key(x_idempotency_key: str | None = Header(default=None)) -> str:
    if not x_idempotency_key:
        raise CuentasError("IDEMPOTENCY_KEY_REQUERIDA",
                           "Falta el header X-Idempotency-Key", 400)
    if len(x_idempotency_key) > 64:
        raise CuentasError("IDEMPOTENCY_KEY_INVALIDA",
                           "X-Idempotency-Key no puede pasar de 64 caracteres", 400)
    return x_idempotency_key
