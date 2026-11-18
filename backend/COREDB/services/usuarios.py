"""Usuarios, portado de CORE/services/usuariossvc.py sobre los procedimientos.

El CORE legado se eliminó en #125; el original queda en el historial de git.

`autenticar` la usa POST /coredb/auth/login. Los usuarios de servicio (un módulo que
se autentica en la API) reciben un secreto generado aquí, que se entrega una sola vez
y se guarda solo como hash bcrypt.
"""

import logging
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from COREDB.database import llamar
from COREDB.errores import ErrorCoreDb
from COREDB.models import Usuario
from COREDB.services.hashing import (
    ALGORITMO_BCRYPT,
    ALGORITMO_SHA256,
    bcrypt_admite,
    es_utf8_valida,
    hash_bcrypt,
    simular_verificacion,
    verify_password,
)
from COREDB.transacciones import con_reintentos

logger = logging.getLogger(__name__)

VERSION_HASH_BCRYPT = "v2"
BYTES_SECRETO = 32  # token_urlsafe(32): 43 caracteres ASCII, dentro del límite de bcrypt


def obtener(db: Session, id_usuario: uuid.UUID) -> Usuario:
    usuario = db.get(Usuario, id_usuario)
    if usuario is None:
        raise ErrorCoreDb("USUARIO_NO_ENCONTRADO", f"Usuario {id_usuario} no existe.", 404)
    return usuario


def listar(db: Session, *, limite: int, offset: int) -> list[Usuario]:
    return db.query(Usuario).order_by(Usuario.username).offset(offset).limit(limite).all()


def crear(
    db: Session,
    *,
    username: str,
    nombre: str,
    password: str,
    rol: str,
    id_empleado: uuid.UUID | None,
    actor: str,
) -> Usuario:
    if not bcrypt_admite(password):
        raise ErrorCoreDb(
            "PASSWORD_NO_ADMITIDA",
            "La contraseña no puede superar 72 bytes ni contener caracteres inválidos.",
        )
    id_usuario, hash_password = uuid.uuid4(), hash_bcrypt(password)
    con_reintentos(
        db,
        lambda: llamar(
            db,
            "core.crear_usuario",
            id_usuario, username, nombre, rol, hash_password,
            ALGORITMO_BCRYPT, VERSION_HASH_BCRYPT, id_empleado, True, actor,
        ),
        nombre="crear_usuario",
    )
    return obtener(db, id_usuario)


def asignar_rol(db: Session, id_usuario: uuid.UUID, *, rol: str, actor: str) -> Usuario:
    usuario = obtener(db, id_usuario)
    con_reintentos(
        db,
        lambda: llamar(db, "core.asignar_rol", id_usuario, rol, actor, salidas=1),
        nombre="asignar_rol",
    )
    db.refresh(usuario)
    return usuario


def _bloqueado_hasta(db: Session, id_usuario: uuid.UUID | None) -> datetime | None:
    """Hasta cuándo está bloqueado el login (bd-v1.12), o None. Se consulta también sin
    usuario, para que el tiempo de respuesta no delate si existe."""
    hasta = db.execute(
        text("SELECT core.fn_login_bloqueado_hasta(:id)"),
        {"id": id_usuario.bytes if id_usuario else None},
    ).scalar_one()
    return hasta.replace(tzinfo=timezone.utc) if hasta is not None else None


def _registrar_fallo(db: Session, id_usuario: uuid.UUID | None, correlation_id: uuid.UUID | None) -> None:
    """Cuenta el fallo y, al quinto seguido, bloquea el login de una persona (bd-v1.12).
    Sin usuario la base no hace nada, pero la llamada cuesta lo mismo."""
    con_reintentos(
        db,
        lambda: llamar(db, "core.registrar_login_fallido", id_usuario, correlation_id, salidas=1),
        nombre="registrar_login_fallido",
    )


def autenticar(
    db: Session, *, username: str, password: str, correlation_id: uuid.UUID | None = None
) -> Usuario:
    """Lanza CREDENCIALES_INVALIDAS, LOGIN_BLOQUEADO o USUARIO_INACTIVO; el login responde a
    todos con el mismo 401. Cinco fallos seguidos bloquean a una persona 15 minutos
    (bd-v1.12; los usuarios de servicio no se bloquean). Con el login bloqueado ni
    siquiera se verifica la contraseña."""
    if not es_utf8_valida(password):
        raise ErrorCoreDb("PASSWORD_NO_ADMITIDA", "La contraseña contiene caracteres inválidos.")
    usuario = db.query(Usuario).filter(Usuario.username == username).first()
    id_usuario = usuario.id_usuario if usuario is not None else None
    bloqueado = _bloqueado_hasta(db, id_usuario) is not None
    if usuario is None or bloqueado or usuario.algoritmo_hash != ALGORITMO_BCRYPT:
        simular_verificacion()
    if usuario is None or bloqueado or not verify_password(
        password, usuario.hash_password, usuario.algoritmo_hash
    ):
        _registrar_fallo(db, id_usuario, correlation_id)
        if bloqueado:
            raise ErrorCoreDb("LOGIN_BLOQUEADO", "El login del usuario está bloqueado.", 401)
        raise ErrorCoreDb("CREDENCIALES_INVALIDAS", "Usuario o contraseña incorrectos.", 401)
    if not usuario.activo:
        raise ErrorCoreDb("USUARIO_INACTIVO", "El usuario está desactivado.", 401)
    _migrar_a_bcrypt(db, usuario, password)
    return usuario


def _migrar_a_bcrypt(db: Session, usuario: Usuario, password: str) -> None:
    if usuario.algoritmo_hash != ALGORITMO_SHA256 or not bcrypt_admite(password):
        return
    id_usuario = usuario.id_usuario
    try:
        llamar(
            db, "core.migrar_hash_usuario",
            id_usuario, ALGORITMO_SHA256, hash_bcrypt(password),
            ALGORITMO_BCRYPT, VERSION_HASH_BCRYPT, usuario.username,
            salidas=1,
        )
        db.commit()
        db.refresh(usuario)
    except (SQLAlchemyError, ErrorCoreDb):
        # El error no se registra porque incluiría el hash nuevo.
        db.rollback()
        logger.warning("No se pudo migrar el hash del usuario %s.", id_usuario)


def _secreto() -> tuple[str, str]:
    secreto = secrets.token_urlsafe(BYTES_SECRETO)
    return secreto, hash_bcrypt(secreto)


def crear_servicio(
    db: Session, *, modulo: str, username: str, nombre: str, actor: str
) -> tuple[Usuario, str]:
    """Crea el usuario de servicio de un módulo. Devuelve (usuario, secreto)."""
    id_usuario = uuid.uuid4()
    secreto, hash_password = _secreto()
    con_reintentos(
        db,
        lambda: llamar(
            db, "core.crear_usuario_servicio",
            id_usuario, username, nombre, modulo, hash_password,
            ALGORITMO_BCRYPT, VERSION_HASH_BCRYPT, actor,
        ),
        nombre="crear_usuario_servicio",
    )
    return obtener(db, id_usuario), secreto


def renovar_credencial(db: Session, id_usuario: uuid.UUID, *, actor: str) -> tuple[Usuario, str]:
    """Reemplaza el secreto de un usuario de servicio; el anterior deja de servir."""
    usuario = obtener(db, id_usuario)
    secreto, hash_password = _secreto()
    con_reintentos(
        db,
        lambda: llamar(
            db, "core.renovar_credencial",
            id_usuario, hash_password, ALGORITMO_BCRYPT, VERSION_HASH_BCRYPT, actor,
            salidas=1,
        ),
        nombre="renovar_credencial",
    )
    db.refresh(usuario)
    return usuario, secreto


def cambiar_estado(db: Session, id_usuario: uuid.UUID, *, activo: bool, actor: str) -> Usuario:
    """Revoca o restituye el acceso; pedir el estado que ya tiene no cambia nada."""
    usuario = obtener(db, id_usuario)
    con_reintentos(
        db,
        lambda: llamar(db, "core.cambiar_estado_usuario", id_usuario, activo, actor, salidas=1),
        nombre="cambiar_estado_usuario",
    )
    db.refresh(usuario)
    return usuario


def registrar_login(db: Session, usuario: Usuario, correlation_id: uuid.UUID | None) -> None:
    """El evento LOGIN; el actor lo toma la base de la fila del usuario."""
    con_reintentos(
        db,
        lambda: llamar(db, "core.registrar_login", usuario.id_usuario, correlation_id),
        nombre="registrar_login",
    )


def desbloquear_login(db: Session, id_usuario: uuid.UUID, *, actor: str) -> Usuario:
    """Levanta el bloqueo del login (bd-v1.12) y reinicia los fallos."""
    usuario = obtener(db, id_usuario)
    con_reintentos(
        db,
        lambda: llamar(db, "core.desbloquear_login", id_usuario, actor),
        nombre="desbloquear_login",
    )
    return con_bloqueo(db, usuario)


def con_bloqueo(db: Session, usuario: Usuario) -> Usuario:
    """El usuario con `bloqueado_hasta` (no es una columna: lo calcula la base)."""
    usuario.bloqueado_hasta = _bloqueado_hasta(db, usuario.id_usuario)
    return usuario
