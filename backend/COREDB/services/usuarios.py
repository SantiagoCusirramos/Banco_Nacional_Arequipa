"""Usuarios, portado de CORE/services/usuariossvc.py sobre los procedimientos.

`autenticar` aún no tiene ruta: el login llega con el JWT.
"""

import logging
import uuid

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


def autenticar(db: Session, *, username: str, password: str) -> Usuario:
    """Lanza CREDENCIALES_INVALIDAS o USUARIO_INACTIVO; ver CORE/AUTENTICACION.md."""
    if not es_utf8_valida(password):
        raise ErrorCoreDb("PASSWORD_NO_ADMITIDA", "La contraseña contiene caracteres inválidos.")
    usuario = db.query(Usuario).filter(Usuario.username == username).first()
    if usuario is None or usuario.algoritmo_hash != ALGORITMO_BCRYPT:
        simular_verificacion()
    if usuario is None or not verify_password(
        password, usuario.hash_password, usuario.algoritmo_hash
    ):
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
