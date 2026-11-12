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


def autorizacion(authorization: str | None = Header(default=None)) -> str:
    # COREDB valida el JWT y el permiso; aqui solo se exige que venga para reenviarlo
    if not authorization:
        raise TarjetasError("ERR-TAR-TOKEN-REQUERIDO", "Falta el header Authorization: Bearer <token>", 401)
    esquema, _, valor = authorization.partition(" ")
    if esquema.lower() != "bearer" or not valor.strip():
        raise TarjetasError("ERR-TAR-TOKEN-INVALIDO", "Authorization debe tener el formato Bearer <token>", 401)
    return authorization
