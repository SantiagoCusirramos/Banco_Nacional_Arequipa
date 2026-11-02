"""Conexión a MySQL (SQLAlchemy) y creación automática de tablas."""
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from shared.comun import entorno

log = logging.getLogger("core.db")

# Ejemplo: mysql+pymysql://usuario:clave@mysql:3306/bna_core?charset=utf8mb4
DATABASE_URL = entorno("DATABASE_URL")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=1800, pool_size=5, max_overflow=5)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def ahora_utc() -> datetime:
    """Fechas siempre en UTC, sin zona (DATETIME de MySQL)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iniciar_bd(max_espera_seg: int = 90) -> None:
    from . import models  # noqa: F401  (registra las tablas)

    limite = time.time() + max_espera_seg
    while True:
        try:
            with engine.connect() as con:
                con.execute(text("SELECT 1"))
            break
        except Exception as e:  # MySQL todavía arrancando
            if time.time() > limite:
                raise
            log.info("Esperando a la base de datos... (%s)", type(e).__name__)
            time.sleep(2)

    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        existentes = {c for c in db.scalars(select(models.TipoDocumento.codigo))}
        for codigo, desc in (("DNI", "Documento Nacional de Identidad"), ("PASAPORTE", "Pasaporte"), ("PTP", "Permiso Temporal de Permanencia")):
            if codigo not in existentes:
                db.add(models.TipoDocumento(codigo=codigo, descripcion=desc))
        db.commit()
    log.info("Base de datos lista")
