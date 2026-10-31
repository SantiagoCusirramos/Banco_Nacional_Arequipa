"""Modelos de lectura. Cada uno declara su base; las escrituras van por procedimientos."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, Numeric, String
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


class Moneda(Base):
    __tablename__ = "moneda"
    __table_args__ = {"schema": "core"}

    cod_moneda: Mapped[str] = mapped_column(String(3), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    simbolo: Mapped[str] = mapped_column(String(4))
    decimales: Mapped[int] = mapped_column()


class Agencia(Base):
    __tablename__ = "agencia"
    __table_args__ = {"schema": "core"}

    id_agencia: Mapped[str] = mapped_column(String(10), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))


class ProductoAhorro(Base):
    __tablename__ = "producto_ahorro"
    __table_args__ = {"schema": "core"}

    id_producto_ahorro: Mapped[uuid.UUID] = mapped_column(UuidBinario, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60))
    moneda: Mapped[str] = mapped_column(String(3))
    tasa_tea: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    activo: Mapped[bool] = mapped_column()


class ProductoCredito(Base):
    __tablename__ = "producto_credito"
    __table_args__ = {"schema": "core"}

    id_producto_credito: Mapped[uuid.UUID] = mapped_column(UuidBinario, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60))
    tasa_tea: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    plazo_min_meses: Mapped[int] = mapped_column()
    plazo_max_meses: Mapped[int] = mapped_column()
    activo: Mapped[bool] = mapped_column()


class TipoCambio(Base):
    __tablename__ = "tipo_cambio"
    __table_args__ = {"schema": "core"}

    cod_moneda_origen: Mapped[str] = mapped_column(String(3), primary_key=True)
    cod_moneda_destino: Mapped[str] = mapped_column(String(3), primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, primary_key=True)
    tasa: Mapped[Decimal] = mapped_column(Numeric(12, 6))


class EquivalenciaCatalogo(Base):
    __tablename__ = "equivalencia_catalogo"
    __table_args__ = {"schema": "core"}

    catalogo: Mapped[str] = mapped_column(String(30), primary_key=True)
    valor_api: Mapped[str] = mapped_column(String(30), primary_key=True)
    valor_bd: Mapped[str] = mapped_column(String(30))


class CuentaAhorro(Base):
    __tablename__ = "cuenta_ahorro"
    __table_args__ = {"schema": "cuentas"}

    num_cuenta: Mapped[str] = mapped_column(String(20), primary_key=True)
    cci: Mapped[str] = mapped_column(String(20))
    moneda: Mapped[str] = mapped_column(String(3))
    regimen: Mapped[str] = mapped_column(String(25))
    saldo_contable: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    saldo_disponible: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    estado_cuenta: Mapped[str] = mapped_column(String(25))
    id_agencia: Mapped[str | None] = mapped_column(String(10))


class Tarjeta(Base):
    # La vista no incluye pan_token: bna_api no lee la tabla.
    __tablename__ = "v_tarjeta_api"
    __table_args__ = {"schema": "tarjetas"}

    id_tarjeta: Mapped[uuid.UUID] = mapped_column(UuidBinario, primary_key=True)
    bin: Mapped[str] = mapped_column(String(6))
    ultimos4: Mapped[str] = mapped_column(String(4))
    fecha_emision: Mapped[date] = mapped_column(Date)
    fecha_vencimiento: Mapped[date] = mapped_column(Date)
    estado_tarjeta: Mapped[str] = mapped_column(String(25))
    cod_cliente: Mapped[str] = mapped_column(String(12))
