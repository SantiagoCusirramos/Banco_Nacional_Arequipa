"""Base propia de CAPTACION (`bna_captacion` en db-aux). No toca la base integrada."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from CAPTACION.config import settings


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
_fabrica: sessionmaker | None = None


def crear_engine(url) -> Engine:
    if str(url).startswith("sqlite"):
        # Pruebas: una sola conexión en memoria compartida entre hilos.
        return create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800)


def configurar(url=None) -> Engine:
    """Crea el engine; las pruebas lo llaman con SQLite."""
    global _engine, _fabrica
    _engine = crear_engine(url or settings.url_base())
    _fabrica = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def engine() -> Engine:
    return _engine or configurar()


def crear_tablas() -> None:
    from CAPTACION import models  # noqa: F401  (registra las tablas)
    Base.metadata.create_all(engine())


def db_session() -> Iterator[Session]:
    engine()
    with _fabrica() as sesion:
        yield sesion
