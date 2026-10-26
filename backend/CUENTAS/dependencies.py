from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from fastapi import Depends, Header, Request

from CUENTAS.core_client import CoreClient
from CUENTAS.exceptions import CuentasError

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


def idempotency_key(x_idempotency_key: str | None = Header(default=None)) -> str:
    if not x_idempotency_key:
        raise _header_error("ERR-CTA-HEADER-REQUERIDO", "Falta el header X-Idempotency-Key", "X-Idempotency-Key")
    try:
        es_v4 = UUID(x_idempotency_key).version == 4
    except ValueError:
        es_v4 = False
    if not es_v4:
        raise _header_error("ERR-CTA-HEADER-INVALIDO", "X-Idempotency-Key debe ser un UUIDv4", "X-Idempotency-Key")
    return x_idempotency_key


def canal(x_channel_id: str | None = Header(default=None)) -> str:
    if not x_channel_id:
        raise _header_error("ERR-CTA-HEADER-REQUERIDO", "Falta el header X-Channel-ID", "X-Channel-ID")
    id_canal = CANALES.get(x_channel_id.upper())
    if not id_canal:
        raise CuentasError("ERR-CTA-HEADER-INVALIDO", "X-Channel-ID no reconocido", 400,
                           {"header": "X-Channel-ID", "permitidos": sorted(CANALES)})
    return id_canal


def request_timestamp(x_request_timestamp: str | None = Header(default=None)) -> datetime:
    if not x_request_timestamp:
        raise _header_error("ERR-CTA-HEADER-REQUERIDO", "Falta el header X-Request-Timestamp", "X-Request-Timestamp")
    try:
        return datetime.fromisoformat(x_request_timestamp.replace("Z", "+00:00"))
    except ValueError:
        raise _header_error("ERR-CTA-HEADER-INVALIDO", "X-Request-Timestamp debe ser ISO-8601", "X-Request-Timestamp")


@dataclass
class ContextoOperacion:
    idempotency_key: str
    id_canal: str
    cid: str


def contexto_operacion(
    key: str = Depends(idempotency_key),
    id_canal: str = Depends(canal),
    _ts: datetime = Depends(request_timestamp),
    cid: str = Depends(correlation_id),
) -> ContextoOperacion:
    return ContextoOperacion(key, id_canal, cid)
