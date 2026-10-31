"""Usuarios del sistema — acciones CREAR_USUARIO y ASIGNAR_ROLES.

Las contraseñas nuevas usan bcrypt (algoritmo_hash='BCRYPT', versión v2).
Los usuarios SHA-256 existentes, incluidos los seeds de la BD, migran en
su primer login exitoso. El rol es un ENUM: ADMINISTRADOR, ASESOR,
ANALISTA, OPERADOR, AUDITOR.
"""

import logging
from datetime import datetime

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from CORE.exceptions import ConflictError, NotFoundError, ValidationError
from CORE.models import Empleado, UsuarioSistema
from CORE.services import auditoria
from CORE.utils.hashing import (
    ALGORITMO_BCRYPT,
    ALGORITMO_SHA256,
    bcrypt_admite,
    es_utf8_valida,
    hash_bcrypt,
    verify_password,
)
from CORE.utils.ids import new_uuid7

logger = logging.getLogger(__name__)

ROLES_VALIDOS = ("ADMINISTRADOR", "ASESOR", "ANALISTA", "OPERADOR", "AUDITOR")
VERSION_HASH_BCRYPT = "v2"


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
    if not bcrypt_admite(password):
        raise ValidationError(
            "PASSWORD_NO_ADMITIDA",
            "La contraseña no puede superar 72 bytes ni contener caracteres inválidos.",
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
        hash_password=hash_bcrypt(password),
        algoritmo_hash=ALGORITMO_BCRYPT,
        version_hash=VERSION_HASH_BCRYPT,
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
    if not es_utf8_valida(password):
        raise ValidationError("PASSWORD_NO_ADMITIDA", "La contraseña contiene caracteres inválidos.")
    usuario = db.query(UsuarioSistema).filter(UsuarioSistema.username == username).first()
    if usuario is None or not verify_password(
        password, usuario.hash_password, usuario.algoritmo_hash
    ):
        raise NotFoundError("CREDENCIALES_INVALIDAS", "Usuario o contraseña incorrectos.")
    if not usuario.activo:
        raise ValidationError("USUARIO_INACTIVO", "El usuario está desactivado.")
    _migrar_a_bcrypt(db, usuario, password)
    return usuario


def _migrar_a_bcrypt(db: Session, usuario: UsuarioSistema, password: str) -> None:
    """Pasa un usuario SHA-256 a bcrypt tras verificar su contraseña.

    El UPDATE condicional hace que, con logins simultáneos, solo uno migre
    la fila y registre el evento. Una contraseña que bcrypt no admite sigue
    en SHA-256. Si el commit falla, el login válido continúa y la migración
    se reintenta en el siguiente. El error no se registra porque incluiría
    el hash nuevo.
    """
    if usuario.algoritmo_hash != ALGORITMO_SHA256 or not bcrypt_admite(password):
        return
    id_usuario = usuario.id_usuario
    nuevo_hash = hash_bcrypt(password)
    try:
        migradas = (
            db.query(UsuarioSistema)
            .filter(
                UsuarioSistema.id_usuario == id_usuario,
                UsuarioSistema.algoritmo_hash == ALGORITMO_SHA256,
            )
            .update(
                {
                    UsuarioSistema.hash_password: nuevo_hash,
                    UsuarioSistema.algoritmo_hash: ALGORITMO_BCRYPT,
                    UsuarioSistema.version_hash: VERSION_HASH_BCRYPT,
                },
                synchronize_session=False,
            )
        )
        if migradas == 1:
            auditoria.registrar_evento(
                db,
                modulo="CORE",
                entidad="usuario_sistema",
                id_entidad=id_usuario,
                accion="MIGRAR_HASH_PASSWORD",
                actor=usuario.username,
                detalle={
                    "algoritmo_anterior": ALGORITMO_SHA256,
                    "algoritmo_nuevo": ALGORITMO_BCRYPT,
                },
            )
        db.commit()
        db.refresh(usuario)
    except SQLAlchemyError:
        db.rollback()
        logger.warning("No se pudo migrar el hash del usuario %s.", id_usuario)


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
