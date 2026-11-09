"""Conexión a la base integrada como bna_app_user.

Cada conexión fija UTC y modo estricto. PyMySQL no acepta varias sentencias
en init_command, por eso es un solo SET. Las escrituras se hacen con
`llamar`, que ejecuta un procedimiento; las lecturas usan los modelos.
"""

import re
import uuid
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.types import BINARY, DateTime, TypeDecorator

from COREDB.config import get_settings
from COREDB.errores import ErrorBaseDatos

# El mismo modo de database/conf/mysql/bna.cnf.
SQL_MODE = (
    "STRICT_ALL_TABLES,ONLY_FULL_GROUP_BY,NO_ZERO_IN_DATE,NO_ZERO_DATE,"
    "ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION"
)
INIT_COMMAND = f"SET SESSION time_zone = '+00:00', sql_mode = '{SQL_MODE}'"

_PROCEDIMIENTO = re.compile(r"[a-z_]+\.[a-z_]+")

_engine: Engine | None = None
_sesiones: sessionmaker[Session] | None = None


class UuidBinario(TypeDecorator):
    """uuid.UUID en Python, BINARY(16) en la base."""

    impl = BINARY(16)
    cache_ok = True

    def process_bind_param(self, value: uuid.UUID | None, dialect) -> bytes | None:
        return None if value is None else value.bytes

    def process_result_value(self, value: bytes | None, dialect) -> uuid.UUID | None:
        return None if value is None else uuid.UUID(bytes=value)


class FechaUtc(TypeDecorator):
    """DATETIME guarda UTC sin zona; aquí se lee con zona para publicarla con Z."""

    impl = DateTime
    cache_ok = True

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        return None if value is None else value.replace(tzinfo=timezone.utc)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_settings().database_url,
            pool_pre_ping=True,
            pool_recycle=1800,
            # Los parámetros incluyen hashes y tokens: no van en el texto de las excepciones.
            hide_parameters=True,
            connect_args={"init_command": INIT_COMMAND},
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _sesiones
    if _sesiones is None:
        _sesiones = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
    return _sesiones


def db_session() -> Iterator[Session]:
    sesion = get_session_factory()()
    try:
        yield sesion
    finally:
        sesion.close()


def verificar_configuracion() -> None:
    """Falla si el servidor no tiene la configuración que exigen las reglas."""
    with get_session_factory()() as sesion:
        sesion.execute(text("CALL core.verificar_configuracion()"))


def _valor(valor: Any) -> Any:
    return valor.bytes if isinstance(valor, uuid.UUID) else valor


def llamar(
    db: Session, procedimiento: str, *entradas: Any, salidas: int = 0
) -> tuple[Any, ...]:
    """Ejecuta un procedimiento y devuelve sus parámetros OUT.

    Los OUT son variables de sesión, por eso se leen en la misma conexión.
    No confirma: la transacción es de quien llama.
    """
    if not _PROCEDIMIENTO.fullmatch(procedimiento):
        raise ValueError(f"Procedimiento inválido: {procedimiento}")
    marcas = [f":p{i}" for i in range(len(entradas))]
    variables = [f"@coredb_s{i}" for i in range(salidas)]
    parametros = {f"p{i}": _valor(v) for i, v in enumerate(entradas)}
    try:
        db.execute(
            text(f"CALL {procedimiento}({', '.join(marcas + variables)})"), parametros
        )
        if not variables:
            return ()
        return tuple(db.execute(text(f"SELECT {', '.join(variables)}")).one())
    except DBAPIError as exc:
        if ErrorBaseDatos.es_reintentable(exc):
            raise
        raise ErrorBaseDatos.desde(exc) from exc
