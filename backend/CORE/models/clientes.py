"""Maestro de clientes del CORE (script 02_clientes_kyc.sql).

RF-COR-01 / RF-COR-02: el CORE custodia el Customer ID único y
garantiza la no duplicidad por (tipo_documento, numero_documento) — RGN-05.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from CORE.database import Base


class Cliente(Base):
    __tablename__ = "cliente"

    id_cliente: Mapped[str] = mapped_column(String(36), primary_key=True)
    cod_tipo_documento: Mapped[str] = mapped_column(
        String(10), ForeignKey("tipo_documento.cod_tipo_documento")
    )
    numero_documento: Mapped[str] = mapped_column(String(20))
    nombres: Mapped[str] = mapped_column(String(80))
    apellido_paterno: Mapped[str] = mapped_column(String(60))
    apellido_materno: Mapped[str | None] = mapped_column(String(60), nullable=True)
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date, nullable=True)
    numero_celular: Mapped[str] = mapped_column(String(15))
    correo_electronico: Mapped[str | None] = mapped_column(
        String(120), unique=True, nullable=True
    )
    estado_cliente: Mapped[str] = mapped_column(
        String(15), default="ACTIVO"
    )  # ENUM estado_cliente
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(3))
