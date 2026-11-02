"""Las cuatro tablas del Core simulado."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class TipoDocumento(Base):
    __tablename__ = "tipos_documento"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    descripcion: Mapped[str] = mapped_column(String(60))


class Cliente(Base):
    __tablename__ = "clientes"
    __table_args__ = (UniqueConstraint("tipo_documento_id", "numero_documento", name="uq_cliente_documento"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tipo_documento_id: Mapped[int] = mapped_column(ForeignKey("tipos_documento.id"))
    numero_documento: Mapped[str] = mapped_column(String(20))
    nombres: Mapped[str] = mapped_column(String(100))
    apellidos: Mapped[str] = mapped_column(String(100))
    fecha_nacimiento: Mapped[date] = mapped_column(Date)
    ingreso_mensual: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    direccion: Mapped[str] = mapped_column(String(200))
    correo: Mapped[str] = mapped_column(String(120))
    telefono: Mapped[str] = mapped_column(String(20))
    fecha_registro: Mapped[datetime] = mapped_column(DateTime)


class SolicitudRegistro(Base):
    __tablename__ = "solicitudes_registro"
    __table_args__ = (Index("ix_sol_reg_fecha", "fecha_solicitud"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    modulo_origen: Mapped[str] = mapped_column(String(30))
    tipo_documento: Mapped[str] = mapped_column(String(20))
    numero_documento: Mapped[str] = mapped_column(String(40))
    fecha_solicitud: Mapped[datetime] = mapped_column(DateTime)
    resultado: Mapped[str] = mapped_column(String(80))


class SolicitudValidacion(Base):
    __tablename__ = "solicitudes_validacion"
    __table_args__ = (Index("ix_sol_val_fecha", "fecha_solicitud"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    modulo_origen: Mapped[str] = mapped_column(String(30))
    tipo_documento: Mapped[str] = mapped_column(String(20))
    numero_documento: Mapped[str] = mapped_column(String(40))
    tipo_validacion: Mapped[str] = mapped_column(String(10))  # DOCUMENTO | FACIAL | HUELLA
    fecha_solicitud: Mapped[datetime] = mapped_column(DateTime)
    resultado: Mapped[str] = mapped_column(String(80))
