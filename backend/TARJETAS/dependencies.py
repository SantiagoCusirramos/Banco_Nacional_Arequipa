from uuid import UUID

from fastapi import Header, Request

from TARJETAS.core_client import CoreClient
from TARJETAS.exceptions import TarjetasError


def get_core_client():
    client = CoreClient()
    try:
        yield client
    finally:
        client.close()


def correlation_id(request: Request) -> str:
    return request.state.uuid_transaccion


def idempotency_key(x_idempotency_key: str | None = Header(default=None)) -> str:
    # Como en CUENTAS: la emision se repite sin duplicarse si llega con la misma llave
    if not x_idempotency_key:
        raise TarjetasError("ERR-TAR-HEADER-REQUERIDO", "Falta el header X-Idempotency-Key", 400,
                            {"header": "X-Idempotency-Key"})
    try:
        es_v4 = UUID(x_idempotency_key).version == 4
    except ValueError:
        es_v4 = False
    if not es_v4:
        raise TarjetasError("ERR-TAR-HEADER-INVALIDO", "X-Idempotency-Key debe ser un UUIDv4", 400,
                            {"header": "X-Idempotency-Key"})
    return x_idempotency_key


def autorizacion(authorization: str | None = Header(default=None)) -> str:
    # COREDB valida el JWT y el permiso; aqui solo se exige que venga para reenviarlo
    if not authorization:
        raise TarjetasError("ERR-TAR-TOKEN-REQUERIDO", "Falta el header Authorization: Bearer <token>", 401)
    esquema, _, valor = authorization.partition(" ")
    if esquema.lower() != "bearer" or not valor.strip():
        raise TarjetasError("ERR-TAR-TOKEN-INVALIDO", "Authorization debe tener el formato Bearer <token>", 401)
    return authorization
