"""Conexión a la base de datos unificada `bna` (MySQL 8 / InnoDB).

SQLAlchemy 2.0 con sesión síncrona vía pymysql. CORE es el único
módulo con acceso a esta BD (RNF-22 / RES-02).
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from CORE.config import get_settings


class Base(DeclarativeBase):
    """Base declarativa de todos los modelos del esquema `bna`."""


_engine = None
_SessionFactory: sessionmaker[Session] | None = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_settings().database_url,
            pool_pre_ping=True,
            pool_recycle=1800,
            future=True,
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(
            bind=get_engine(), autoflush=False, expire_on_commit=False,
            future=True,
        )
    return _SessionFactory


def get_db() -> Generator[Session, None, None]:
    """Dependencia FastAPI: una sesión por petición."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def reset_engine() -> None:
    """Permite reconectar (tests o cambio de configuración)."""
    global _engine, _SessionFactory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionFactory = None
