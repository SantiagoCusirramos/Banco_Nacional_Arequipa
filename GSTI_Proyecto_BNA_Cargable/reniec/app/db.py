"""SQLite persistente de RENIEC (independiente del Core)."""
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

RUTA_BD = os.getenv("RENIEC_DB_PATH", "/data/reniec.db")
Path(RUTA_BD).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(f"sqlite:///{RUTA_BD}", connect_args={"check_same_thread": False, "timeout": 15})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


@event.listens_for(engine, "connect")
def _pragmas(con, _):
    cur = con.cursor()
    cur.execute("PRAGMA foreign_keys=ON")  # para que al borrar un ciudadano se borren sus plantillas
    cur.execute("PRAGMA journal_mode=WAL")
    cur.close()


class Base(DeclarativeBase):
    pass


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iniciar_bd() -> None:
    from . import models  # noqa: F401

    Base.metadata.create_all(engine)
