"""Modelos SQLAlchemy de las tablas des_* (el esquema lo crea sql/esquema.sql)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, BigInteger, Computed, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.schema import FetchedValue


class Base(DeclarativeBase):
    pass


def _creado():
    return mapped_column(DateTime, server_default=FetchedValue())


def _actualizado():
    return mapped_column(DateTime, server_default=FetchedValue(), server_onupdate=FetchedValue())


class Orden(Base):
    __tablename__ = "des_orden"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    codigo_orden: Mapped[str] = mapped_column(String(24))
    aprobacion_id: Mapped[str] = mapped_column(String(36))
    aprobacion_version: Mapped[int] = mapped_column(Integer)
    credito_id: Mapped[str] = mapped_column(String(36))
    cliente_id: Mapped[str] = mapped_column(String(36))
    cuenta_id: Mapped[str | None] = mapped_column(String(36))
    importe: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    moneda: Mapped[str] = mapped_column(String(3))
    estado: Mapped[str] = mapped_column(String(20), default="PREPARADA")
    motivo_rechazo: Mapped[str | None] = mapped_column(String(255))
    entrega_estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE")
    operacion_financiera_id: Mapped[str | None] = mapped_column(String(40))
    fecha_efectiva: Mapped[datetime | None] = mapped_column(DateTime)
    idempotency_key: Mapped[str] = mapped_column(String(36))
    request_hash: Mapped[str] = mapped_column(String(64))
    canal: Mapped[str] = mapped_column(String(20), default="AGENCIA")
    agencia_id: Mapped[str | None] = mapped_column(String(36))
    usuario_preparacion: Mapped[str] = mapped_column(String(40))
    usuario_confirmacion: Mapped[str | None] = mapped_column(String(40))
    correlation_id: Mapped[str] = mapped_column(String(36))
    version: Mapped[int] = mapped_column(Integer, default=0)
    # Lo envía Solicitud y llega con la aprobación (CR-INT-04); va sin cambios a Cobranza (CR-INT-06).
    solicitud_id: Mapped[str | None] = mapped_column(String(36))
    calendario_pagos: Mapped[list | None] = mapped_column(JSON)
    credito_en_ejecucion: Mapped[str | None] = mapped_column(
        String(36),
        Computed("CASE WHEN estado IN ('EN_PROCESO','POR_VERIFICAR','CONFIRMADA','REVERTIDA') THEN credito_id ELSE NULL END",
                 persisted=True))
    creado_en: Mapped[datetime] = _creado()
    actualizado_en: Mapped[datetime] = _actualizado()

    validaciones: Mapped[list[Validacion]] = relationship(order_by="Validacion.creado_en", lazy="selectin")
    eventos: Mapped[list[EventoEntrega]] = relationship(order_by="EventoEntrega.creado_en", lazy="selectin")


class Validacion(Base):
    __tablename__ = "des_validacion"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    orden_id: Mapped[str] = mapped_column(ForeignKey("des_orden.id"))
    tipo: Mapped[str] = mapped_column(String(20))
    fase: Mapped[str] = mapped_column(String(20), default="PREPARACION")
    proveedor: Mapped[str] = mapped_column(String(40))
    referencia_evidencia: Mapped[str] = mapped_column(String(100))
    resultado: Mapped[str] = mapped_column(String(20))
    detalle: Mapped[str | None] = mapped_column(String(255))
    vence_en: Mapped[datetime | None] = mapped_column(DateTime)
    creado_en: Mapped[datetime] = _creado()


class EventoEntrega(Base):
    __tablename__ = "des_evento_entrega"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    orden_id: Mapped[str] = mapped_column(ForeignKey("des_orden.id"))
    tipo: Mapped[str] = mapped_column(String(60))
    version_esquema: Mapped[str] = mapped_column(String(10), default="v1")
    payload: Mapped[dict] = mapped_column(JSON)
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE")
    intentos: Mapped[int] = mapped_column(SmallInteger, default=0)
    siguiente_intento: Mapped[datetime | None] = mapped_column(DateTime)
    confirmacion_id: Mapped[str | None] = mapped_column(String(60))
    ultimo_error: Mapped[str | None] = mapped_column(String(255))
    creado_en: Mapped[datetime] = _creado()
    actualizado_en: Mapped[datetime] = _actualizado()


class Auditoria(Base):
    __tablename__ = "des_auditoria"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    orden_id: Mapped[str | None] = mapped_column(String(36))
    actor_id: Mapped[str] = mapped_column(String(40))
    accion: Mapped[str] = mapped_column(String(60))
    resultado: Mapped[str] = mapped_column(String(40))
    correlation_id: Mapped[str] = mapped_column(String(36))
    ip: Mapped[str | None] = mapped_column(String(45))
    detalle: Mapped[dict | None] = mapped_column(JSON)
    creado_en: Mapped[datetime] = _creado()


class SolicitudReversion(Base):
    __tablename__ = "des_solicitud_reversion"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    orden_id: Mapped[str] = mapped_column(ForeignKey("des_orden.id"))
    motivo: Mapped[str] = mapped_column(String(255))
    origen: Mapped[str] = mapped_column(String(30), default="SOLICITUD_SERVICIO")
    solicitante_id: Mapped[str] = mapped_column(String(40))
    autorizador_id: Mapped[str | None] = mapped_column(String(40))
    autorizacion_id: Mapped[str | None] = mapped_column(String(60))
    estado: Mapped[str] = mapped_column(String(20), default="SOLICITADA")
    motivo_rechazo: Mapped[str | None] = mapped_column(String(255))
    idempotency_key: Mapped[str] = mapped_column(String(36))
    reversion_financiera_id: Mapped[str | None] = mapped_column(String(40))
    correlation_id: Mapped[str] = mapped_column(String(36))
    orden_reversion_activa: Mapped[str | None] = mapped_column(
        String(36), Computed("CASE WHEN estado <> 'RECHAZADA' THEN orden_id ELSE NULL END", persisted=True))
    creado_en: Mapped[datetime] = _creado()
    actualizado_en: Mapped[datetime] = _actualizado()
