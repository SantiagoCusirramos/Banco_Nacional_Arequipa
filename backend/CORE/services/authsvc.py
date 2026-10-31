"""Inicio de sesión: valida credenciales y emite el JWT de acceso."""

from sqlalchemy.orm import Session

from CORE.exceptions import AuthenticationError, NotFoundError, ValidationError
from CORE.models import UsuarioSistema
from CORE.services import auditoria, usuariossvc
from CORE.utils import tokens

LARGO_CORRELATION_ID = 36  # auditoria_evento.correlation_id


def iniciar_sesion(
    db: Session,
    *,
    username: str,
    password: str,
    correlation_id: str | None = None,
) -> tuple[str, int, UsuarioSistema]:
    """Devuelve (access_token, expires_in, usuario).

    Todo fallo de `autenticar()` (404 o 422) responde el mismo 401, sin
    distinguir usuario inexistente, clave incorrecta ni usuario inactivo.
    Ver AUTENTICACION.md.
    """
    try:
        usuario = usuariossvc.autenticar(db, username=username, password=password)
    except (NotFoundError, ValidationError) as exc:
        raise AuthenticationError(
            "CREDENCIALES_INVALIDAS", "Usuario o contraseña incorrectos."
        ) from exc

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
        # Lo envía el cliente: uno que no cabe no debe impedir el login.
        correlation_id=correlation_id if len(correlation_id or "") <= LARGO_CORRELATION_ID else None,
    )
    db.commit()
    return token, expires_in, usuario
