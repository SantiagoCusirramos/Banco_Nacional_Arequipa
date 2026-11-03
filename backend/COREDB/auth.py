"""Autenticación y permisos de COREDB.

`actor_actual` exige `Authorization: Bearer <jwt>`, valida el token y vuelve a leer el
usuario: si se desactivó o cambió de rol, el efecto es inmediato aunque el token no
haya vencido. `requiere_permiso(accion)` agrega el permiso del mapa de permisos.py.
El actor de la auditoría y el origen de un cambio de tarjeta salen del token, nunca
de la petición. Sigue siendo una dependencia reemplazable:

    app.dependency_overrides[actor_actual] = otra_dependencia
"""

import uuid
from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from COREDB import permisos, tokens
from COREDB.auth_tipos import Actor
from COREDB.database import db_session
from COREDB.errores import ErrorAutenticacion, ErrorCoreDb
from COREDB.models import Usuario

__all__ = ["Actor", "actor_actual", "requiere_permiso"]

_bearer = HTTPBearer(auto_error=False, scheme_name="JWT")


def actor_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(db_session),
) -> Actor:
    if credenciales is None or credenciales.scheme.lower() != "bearer":
        raise ErrorAutenticacion(
            "TOKEN_REQUERIDO", "Falta el encabezado Authorization: Bearer <token>."
        )
    claims = tokens.decodificar(credenciales.credentials)
    usuario = db.get(Usuario, uuid.UUID(claims["sub"]))
    if usuario is None or not usuario.activo:
        raise ErrorAutenticacion("USUARIO_NO_VIGENTE", "El usuario ya no está habilitado.")
    return Actor(usuario.id_usuario, usuario.username, usuario.rol, usuario.modulo)


def requiere_permiso(accion: str) -> Callable[..., Actor]:
    """Dependencia que exige `accion`. Uso: actor: Actor = Depends(requiere_permiso("X"))."""
    if accion not in permisos.ACCIONES:
        raise ValueError(f"Acción desconocida: {accion}")

    def _dependencia(actor: Actor = Depends(actor_actual)) -> Actor:
        if not permisos.puede(actor, accion):
            raise ErrorCoreDb(
                "PERMISO_DENEGADO", f"El rol {actor.clave_permisos} no puede ejecutar {accion}.", 403
            )
        return actor

    _dependencia.accion = accion  # lo lee la prueba que exige un permiso en cada escritura
    return _dependencia
