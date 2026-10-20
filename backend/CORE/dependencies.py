"""Dependencia de sesión de BD para los routers de CORE."""

from collections.abc import Generator

from sqlalchemy.orm import Session

from CORE.database import get_session_factory


def db_session() -> Generator[Session, None, None]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()
