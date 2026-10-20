"""Usuarios del sistema — acciones CREAR_USUARIO y ASIGNAR_ROLES.

El hash es SHA256 hex (CHAR(64), algoritmo_hash='SHA256') para ser
compatible con los seeds de la BD. El rol es un ENUM: ADMINISTRADOR,
ASESOR, ANALISTA, OPERADOR, AUDITOR.
"""

from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from CORE.exceptions import ConflictError, NotFoundError, ValidationError
from CORE.models import Empleado, UsuarioSistema
from CORE.services import auditoria
from CORE.utils.hashing import hash_sha256
from CORE.utils.ids import new_uuid7

ROLES_VALIDOS = ("ADMINISTRADOR", "ASESOR", "ANALISTA", "OPERADOR", "AUDITOR")


def listar_usuarios(
    db: Session, *, activo: bool | None = None, rol: str | None = None,
    limite: int = 50, offset: int = 0,
) -> list[UsuarioSistema]:
    q = db.query(UsuarioSistema)
    if activo is not None:
        q = q.filter(UsuarioSistema.activo.is_(activo))
    if rol:
        q = q.filter(UsuarioSistema.rol == rol)
    return q.order_by(UsuarioSistema.creado_en.desc()).offset(offset).limit(limite).all()


def obtener_usuario(db: Session, id_usuario: str) -> UsuarioSistema:
    usuario = db.get(UsuarioSistema, id_usuario)
    if usuario is None:
        raise NotFoundError("USUARIO_NO_ENCONTRADO", f"Usuario {id_usuario} no existe.")
    return usuario


def crear_usuario(
    db: Session,
    *,
    username: str,
    nombre: str,
    password: str,
    rol: str,
    id_empleado: str | None = None,
    activo: bool = True,
    actor: str = "sistema",
    correlation_id: str | None = None,
) -> UsuarioSistema:
    if rol not in ROLES_VALIDOS:
        raise ValidationError(
            "ROL_INVALIDO",
            f"Rol {rol} no admitido. Opciones: {', '.join(ROLES_VALIDOS)}.",
        )
    if len(password) < 8:
        raise ValidationError(
            "PASSWORD_DEBIL",
            "La contraseña debe tener al menos 8 caracteres.",
        )
    if id_empleado is not None and db.get(Empleado, id_empleado) is None:
        raise NotFoundError("EMPLEADO_NO_ENCONTRADO", f"Empleado {id_empleado} no existe.")

    existente = db.query(UsuarioSistema).filter(UsuarioSistema.username == username).first()
    if existente is not None:
        raise ConflictError(
            "USERNAME_DUPLICADO",
            f"Ya existe un usuario con el nombre {username}.",
            details={"id_usuario": existente.id_usuario},
        )

    usuario = UsuarioSistema(
        id_usuario=new_uuid7(),
        username=username,
        nombre=nombre,
        rol=rol,
        hash_password=hash_sha256(password),
        algoritmo_hash="SHA256",
        version_hash="v1",
        id_empleado=id_empleado,
        activo=activo,
        creado_en=datetime.now(),
    )
    db.add(usuario)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "USUARIO_DUPLICADO", "Conflicto de unicidad al crear el usuario."
        ) from exc

    auditoria.registrar_evento(
        db,
        modulo="CORE",
        entidad="usuario_sistema",
        id_entidad=usuario.id_usuario,
        accion="CREAR_USUARIO",
        actor=actor,
        detalle={"username": username, "rol": rol, "id_empleado": id_empleado},
        correlation_id=correlation_id,
    )
    db.commit()
    return usuario


def asignar_rol(
    db: Session,
    id_usuario: str,
    *,
    nuevo_rol: str,
    actor: str = "sistema",
    correlation_id: str | None = None,
) -> UsuarioSistema:
    if nuevo_rol not in ROLES_VALIDOS:
        raise ValidationError(
            "ROL_INVALIDO",
            f"Rol {nuevo_rol} no admitido. Opciones: {', '.join(ROLES_VALIDOS)}.",
        )
    usuario = obtener_usuario(db, id_usuario)
    rol_anterior = usuario.rol
    usuario.rol = nuevo_rol

    auditoria.registrar_evento(
        db,
        modulo="CORE",
        entidad="usuario_sistema",
        id_entidad=id_usuario,
        accion="ASIGNAR_ROLES",
        actor=actor,
        detalle={"rol_anterior": rol_anterior, "rol_nuevo": nuevo_rol},
        correlation_id=correlation_id,
    )
    db.commit()
    return usuario


def autenticar(db: Session, *, username: str, password: str) -> UsuarioSistema:
    """Valida credenciales (verificación de hash, sin exponer la clave)."""
    from CORE.utils.hashing import verify_sha256

    usuario = db.query(UsuarioSistema).filter(UsuarioSistema.username == username).first()
    if usuario is None or not verify_sha256(password, usuario.hash_password):
        raise NotFoundError("CREDENCIALES_INVALIDAS", "Usuario o contraseña incorrectos.")
    if not usuario.activo:
        raise ValidationError("USUARIO_INACTIVO", "El usuario está desactivado.")
    return usuario


def vista_publica(usuario: UsuarioSistema) -> dict:
    return {
        "id_usuario": usuario.id_usuario,
        "username": usuario.username,
        "nombre": usuario.nombre,
        "rol": usuario.rol,
        "id_empleado": usuario.id_empleado,
        "activo": usuario.activo,
        "creado_en": usuario.creado_en,
    }
