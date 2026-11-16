"""Quién llama y qué puede hacer.

- Personal del banco (pantalla /captacion o /docs): token JWT de COREDB. CAPTACION lo
  valida con `GET /coredb/auth/me` y usa los permisos de COREDB: VER_CLIENTE para leer,
  CREAR_CLIENTE para trabajar un expediente (ASESOR y ADMINISTRADOR los tienen).
- Solicitud de Crédito (servicio): token fijo CAP_SOL_TOKEN, solo en /cap/references.
"""

import secrets
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from CAPTACION.config import settings
from CAPTACION.core_client import CoreDb, coredb
from CAPTACION.errores import CaptacionError

ESQUEMA_BEARER = HTTPBearer(
    auto_error=False, scheme_name="JWT",
    description="Personal: token de COREDB (POST /coredb/auth/login, campo access_token). "
                "Solicitud de Crédito: CAP_SOL_TOKEN, solo en /cap/references.",
)


@dataclass
class Actor:
    usuario: str
    rol: str
    acciones: frozenset[str]
    correlation_id: str


def get_core() -> CoreDb:
    return coredb()


def correlation_id(request: Request) -> str:
    return request.state.uuid_transaccion


def _bearer(request: Request) -> str:
    authorization = request.headers.get("Authorization") or ""
    esquema, _, valor = authorization.partition(" ")
    if not authorization:
        raise CaptacionError("ERR-CAP-TOKEN-REQUERIDO", "Falta el header Authorization: Bearer <token>.", 401)
    if esquema.lower() != "bearer" or not valor.strip():
        raise CaptacionError("ERR-CAP-TOKEN-INVALIDO", "Authorization debe tener el formato Bearer <token>.", 401)
    return valor.strip()


def _actor(request: Request, core: CoreDb) -> Actor:
    perfil = core.perfil(_bearer(request), request.state.uuid_transaccion)
    return Actor(perfil["username"], perfil["rol"], frozenset(perfil.get("acciones", [])),
                 request.state.uuid_transaccion)


def requiere(accion: str):
    def dependencia(request: Request,
                    _credenciales: HTTPAuthorizationCredentials | None = Security(ESQUEMA_BEARER),
                    core: CoreDb = Depends(get_core)) -> Actor:
        actor = _actor(request, core)
        if accion not in actor.acciones:
            raise CaptacionError("ERR-CAP-PERMISO-DENEGADO",
                                 f"El rol {actor.rol} no tiene el permiso {accion}.", 403)
        return actor
    return dependencia


lector = requiere("VER_CLIENTE")
asesor = requiere("CREAR_CLIENTE")


def servicio_sol(request: Request,
                 _credenciales: HTTPAuthorizationCredentials | None = Security(ESQUEMA_BEARER)) -> None:
    """Solo Solicitud de Crédito: compara el token en tiempo constante."""
    token = settings.cap_sol_token
    if len(token) < 32:
        raise HTTPException(503, "CR-INT-01 no está configurado en CAPTACION.")
    recibido = request.headers.get("Authorization", "")
    if not secrets.compare_digest(recibido.encode(), f"Bearer {token}".encode()):
        raise HTTPException(401, "Servicio no autorizado.")
