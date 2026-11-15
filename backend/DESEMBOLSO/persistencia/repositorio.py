"""Acceso a datos del modulo. Solo tablas des_* (PA-04)."""
from __future__ import annotations

from sqlalchemy import create_engine, func, select, text, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from .modelos import Orden


def crear_motor(url: str) -> Engine:
    # Sesión en UTC: los TIMESTAMP se leen en UTC en cualquier servidor (en Docker y en una PC en Lima).
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800, pool_size=10, max_overflow=10,
                         isolation_level="READ COMMITTED", connect_args={"init_command": "SET time_zone = '+00:00'"})


def fecha_lima(columna):
    """Día de Arequipa de una columna TIMESTAMP (UTC en la sesión)."""
    return func.date(func.convert_tz(columna, "+00:00", "-05:00"))


def crear_fabrica(motor: Engine) -> sessionmaker[Session]:
    return sessionmaker(motor, expire_on_commit=False)


def siguiente_codigo(sesion: Session, anio: int) -> str:
    """Correlativo DES-AAAA-NNNNNN sin carreras (LAST_INSERT_ID por conexion)."""
    sesion.execute(text(
        "INSERT INTO des_correlativo (anio, ultimo_numero) VALUES (:anio, LAST_INSERT_ID(1)) "
        "ON DUPLICATE KEY UPDATE ultimo_numero = LAST_INSERT_ID(ultimo_numero + 1)"), {"anio": anio})
    numero = sesion.execute(text("SELECT LAST_INSERT_ID()")).scalar_one()
    return f"DES-{anio}-{numero:06d}"


def orden_por_clave(sesion: Session, clave: str) -> Orden | None:
    return sesion.scalars(select(Orden).where(Orden.idempotency_key == clave)).first()


def credito_en_ejecucion(sesion: Session, credito_id: str) -> Orden | None:
    return sesion.scalars(select(Orden).where(Orden.credito_en_ejecucion == credito_id)).first()


def transitar(sesion: Session, orden_id: str, desde: set[str], hacia: str, **campos) -> bool:
    """UPDATE condicional: solo cambia si la orden sigue en uno de los estados esperados."""
    resultado = sesion.execute(
        update(Orden)
        .where(Orden.id == orden_id, Orden.estado.in_(desde))
        .values(estado=hacia, version=Orden.version + 1, **campos)
        .execution_options(synchronize_session=False))
    return resultado.rowcount == 1


def es_duplicado(exc: IntegrityError, indice: str) -> bool:
    return getattr(exc.orig, "args", [None])[0] == 1062 and indice in str(exc.orig)
