"""Tarjetas emitidas (script 04_tarjetas.sql).

Nota de arquitectura: la validación de tarjeta/clave es del módulo
Tarjetas; CORE solo administra el registro (emisión tokenizada,
consulta y bloqueo) siguiendo las acciones VER/CREAR/BLOQUEAR_TARJETA.
RNF-13 / RGN-18: nunca se almacena ni se expone el PAN en claro.
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from CORE.database import Base


class TarTarjeta(Base):
    __tablename__ = "tar_tarjeta"

    id_tarjeta: Mapped[str] = mapped_column(String(36), primary_key=True)
    pan_token: Mapped[str] = mapped_column(String(64), unique=True)
    bin: Mapped[str] = mapped_column(String(6))
    ultimos4: Mapped[str] = mapped_column(String(4))
    id_cliente: Mapped[str] = mapped_column(String(36), ForeignKey("cliente.id_cliente"))
    tipo_tarjeta: Mapped[str] = mapped_column(String(10))  # ENUM tipo_tarjeta
    fecha_emision: Mapped[date] = mapped_column(Date)
    fecha_vencimiento: Mapped[date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(12), default="ACTIVA")
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(3))


class TarTarjetaCuenta(Base):
    __tablename__ = "tar_tarjeta_cuenta"

    id_tarjeta: Mapped[str] = mapped_column(
        String(36), ForeignKey("tar_tarjeta.id_tarjeta"), primary_key=True
    )
    num_cuenta: Mapped[str] = mapped_column(
        String(20), ForeignKey("cuenta_ahorro.num_cuenta"), primary_key=True
    )
    es_principal: Mapped[bool] = mapped_column(default=False)
    habilitada_atm: Mapped[bool] = mapped_column(default=True)
    fecha_vinculacion: Mapped[datetime] = mapped_column(DateTime(3))


class TarHistorialEstado(Base):
    __tablename__ = "tar_historial_estado"

    id_historial: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_tarjeta: Mapped[str] = mapped_column(
        String(36), ForeignKey("tar_tarjeta.id_tarjeta")
    )
    estado_anterior: Mapped[str] = mapped_column(String(12))
    estado_nuevo: Mapped[str] = mapped_column(String(12))
    motivo: Mapped[str] = mapped_column(String(120))
    origen: Mapped[str] = mapped_column(String(12))  # CLIENTE|BANCO|SISTEMA|REGULADOR
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(3))
