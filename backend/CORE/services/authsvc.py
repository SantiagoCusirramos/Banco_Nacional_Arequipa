"""Inicio de sesión: valida credenciales y emite el JWT de acceso."""

from sqlalchemy.orm import Session

from CORE.exceptions import (
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from CORE.models import UsuarioSistema
from CORE.services import auditoria, usuariossvc
from CORE.utils import tokens


def iniciar_sesion(
    db: Session,
    *,
    username: str,
    password: str,
    correlation_id: str | None = None,
) -> tuple[str, int, UsuarioSistema]:
    """Devuelve (access_token, expires_in, usuario).

    Usuario inexistente y clave incorrecta responden igual (401) para no
    permitir enumerar usuarios. Un usuario desactivado solo se revela
    cuando la clave fue correcta.
    """
    try:
        usuario = usuariossvc.autenticar(db, username=username, password=password)
    except NotFoundError as exc:
        raise AuthenticationError(
            "CREDENCIALES_INVALIDAS", "Usuario o contraseña incorrectos."
        ) from exc
    except ValidationError as exc:
        raise PermissionDeniedError("USUARIO_INACTIVO", "El usuario está desactivado.") from exc

    token, expires_in = tokens.crear_token_acceso(
        id_usuario=usuario.id_usuario, username=usuario.username, rol=usuario.rol
    )
    auditoria.registrar_evento(
        db,
        modulo="CORE",
        entidad="usuario_sistema",
        id_entidad=usuario.id_usuario,
        accion="LOGIN",
        actor=usuario.username,
        detalle={"rol": usuario.rol},
        correlation_id=correlation_id,
    )
    db.commit()
    return token, expires_in, usuario
