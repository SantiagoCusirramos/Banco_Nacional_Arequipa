from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from fastapi import Depends, Header, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from CUENTAS.core_client import CoreClient
from CUENTAS.exceptions import CuentasError

# Esquema Bearer registrado en OpenAPI para que Swagger muestre el boton Authorize (JWT de COREDB)
ESQUEMA_BEARER = HTTPBearer(
    auto_error=False,
    scheme_name="JWT",
    description="Token JWT de COREDB: POST /coredb/auth/login, campo access_token.",
)

# X-Channel-ID (ITIL-01) -> id_canal de CORE. VEN no esta en ITIL-01, se agrega porque CORE lo tiene
CANALES = {"ATM": "ATM", "AGE": "AGE", "VEN": "VEN", "WEB": "HB", "MOB": "BD"}


def get_core_client():
    client = CoreClient()
    try:
        yield client
    finally:
        client.close()


def correlation_id(request: Request) -> str:
    return request.state.uuid_transaccion


def _header_error(codigo: str, mensaje: str, header: str) -> CuentasError:
    return CuentasError(codigo, mensaje, 400, {"header": header})


def idempotency_key(x_idempotency_key: str | None = Header(
        default=None,
        description="UUIDv4 unico por operacion. Reintentar con la misma llave devuelve el resultado original.",
        examples=["550e8400-e29b-41d4-a716-446655440000"])) -> str:
    if not x_idempotency_key:
        raise _header_error("ERR-CTA-HEADER-REQUERIDO", "Falta el header X-Idempotency-Key", "X-Idempotency-Key")
    try:
        es_v4 = UUID(x_idempotency_key).version == 4
    except ValueError:
        es_v4 = False
    if not es_v4:
        raise _header_error("ERR-CTA-HEADER-INVALIDO", "X-Idempotency-Key debe ser un UUIDv4", "X-Idempotency-Key")
    return x_idempotency_key


def canal(x_channel_id: str | None = Header(
        default=None,
        description="Canal de origen: ATM, AGE, VEN, WEB o MOB.",
        examples=["WEB"])) -> str:
    if not x_channel_id:
        raise _header_error("ERR-CTA-HEADER-REQUERIDO", "Falta el header X-Channel-ID", "X-Channel-ID")
    id_canal = CANALES.get(x_channel_id.upper())
    if not id_canal:
        raise CuentasError("ERR-CTA-HEADER-INVALIDO", "X-Channel-ID no reconocido", 400,
                           {"header": "X-Channel-ID", "permitidos": sorted(CANALES)})
    return id_canal


def request_timestamp(x_request_timestamp: str | None = Header(
        default=None,
        description="Fecha y hora ISO-8601 de la peticion.",
        examples=["2026-11-15T12:00:00Z"])) -> datetime:
    if not x_request_timestamp:
        raise _header_error("ERR-CTA-HEADER-REQUERIDO", "Falta el header X-Request-Timestamp", "X-Request-Timestamp")
    try:
        return datetime.fromisoformat(x_request_timestamp.replace("Z", "+00:00"))
    except ValueError:
        raise _header_error("ERR-CTA-HEADER-INVALIDO", "X-Request-Timestamp debe ser ISO-8601", "X-Request-Timestamp")


def autorizacion(
    request: Request,
    _credenciales: HTTPAuthorizationCredentials | None = Security(ESQUEMA_BEARER),
) -> str:
    # Se lee el header original para conservar los codigos de error propios de Cuentas
    authorization = request.headers.get("Authorization")
    # COREDB valida el JWT; aqui solo se exige que venga para reenviarlo
    if not authorization:
        raise CuentasError("ERR-CTA-TOKEN-REQUERIDO", "Falta el header Authorization: Bearer <token>", 401)
    esquema, _, valor = authorization.partition(" ")
    if esquema.lower() != "bearer" or not valor.strip():
        raise CuentasError("ERR-CTA-TOKEN-INVALIDO", "Authorization debe tener el formato Bearer <token>", 401)
    return authorization


@dataclass
class ContextoOperacion:
    idempotency_key: str
    id_canal: str
    cid: str
    authorization: str


def contexto_operacion(
    key: str = Depends(idempotency_key),
    id_canal: str = Depends(canal),
    _ts: datetime = Depends(request_timestamp),
    cid: str = Depends(correlation_id),
    authorization: str = Depends(autorizacion),
) -> ContextoOperacion:
    return ContextoOperacion(key, id_canal, cid, authorization)
