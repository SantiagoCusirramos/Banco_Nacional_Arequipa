"""Dependencias de FastAPI para los routers de CORE: sesión de BD y JWT."""

from collections.abc import Callable, Generator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from CORE.database import get_session_factory
from CORE.exceptions import AuthenticationError, PermissionDeniedError
from CORE.models import UsuarioSistema
from CORE.services import rbac
from CORE.utils import tokens

_bearer = HTTPBearer(auto_error=False, scheme_name="JWT")


def db_session() -> Generator[Session, None, None]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


def usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(db_session),
) -> UsuarioSistema:
    """Exige `Authorization: Bearer <jwt>` y devuelve el usuario vigente.

    Se vuelve a leer el usuario en BD: si fue desactivado o cambió de rol,
    el efecto es inmediato aunque el token aún no haya vencido.
    """
    if credenciales is None or credenciales.scheme.lower() != "bearer":
        raise AuthenticationError(
            "TOKEN_REQUERIDO", "Falta el encabezado Authorization: Bearer <token>."
        )
    claims = tokens.decodificar_token(credenciales.credentials)
    usuario = db.get(UsuarioSistema, claims["sub"])
    if usuario is None or not usuario.activo:
        raise AuthenticationError("USUARIO_NO_VIGENTE", "El usuario ya no está habilitado.")
    return usuario


def requiere_permiso(accion: str) -> Callable[..., UsuarioSistema]:
    """Dependencia que exige que el rol del usuario tenga `accion` en rbac.json.

    Uso:  @router.get("", dependencies=[Depends(requiere_permiso("VER_AUDITORIA"))])
    """

    def _dependencia(usuario: UsuarioSistema = Depends(usuario_actual)) -> UsuarioSistema:
        if not rbac.rol_puede(usuario.rol, accion):
            raise PermissionDeniedError(
                "PERMISO_DENEGADO",
                f"El rol {usuario.rol} no puede ejecutar {accion}.",
                details={"accion": accion},
            )
        return usuario

    return _dependencia
