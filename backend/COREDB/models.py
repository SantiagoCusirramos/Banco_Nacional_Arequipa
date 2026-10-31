"""Modelos de lectura. Cada uno declara su base; las escrituras van por procedimientos."""

import uuid
from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from COREDB.database import FechaUtc, UuidBinario


class Base(DeclarativeBase):
    pass


class Usuario(Base):
    __tablename__ = "usuario_sistema"
    __table_args__ = {"schema": "core"}

    id_usuario: Mapped[uuid.UUID] = mapped_column(UuidBinario, primary_key=True)
    username: Mapped[str] = mapped_column(String(40))
    nombre: Mapped[str] = mapped_column(String(100))
    rol: Mapped[str] = mapped_column(String(15))
    hash_password: Mapped[str] = mapped_column(String(255))
    algoritmo_hash: Mapped[str] = mapped_column(String(20))
    version_hash: Mapped[str] = mapped_column(String(10))
    id_empleado: Mapped[uuid.UUID | None] = mapped_column(UuidBinario)
    activo: Mapped[bool] = mapped_column()
    creado_en: Mapped[datetime] = mapped_column(FechaUtc)
