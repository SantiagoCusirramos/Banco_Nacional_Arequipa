"""Cuentas de ahorro, vinculaciones, movimientos y control de topes
(script 03_cuentas.sql).

RF-COR-03..09, RF-COR-18: apertura, saldos, movimientos, topes diarios
y estado de cuenta.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from CORE.database import Base


class CuentaAhorro(Base):
    __tablename__ = "cuenta_ahorro"

    num_cuenta: Mapped[str] = mapped_column(String(20), primary_key=True)
    moneda: Mapped[str] = mapped_column(String(3), ForeignKey("moneda.cod_moneda"))
    regimen: Mapped[str] = mapped_column(String(15))  # ENUM regimen
    saldo_contable: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    saldo_disponible: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    saldo_retenido: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    estado_cuenta: Mapped[str] = mapped_column(String(15), default="ACTIVA")
    fecha_apertura: Mapped[datetime] = mapped_column(DateTime(3))
    id_agencia: Mapped[str] = mapped_column(String(36), ForeignKey("agencia.id_agencia"))
    id_producto_ahorro: Mapped[str] = mapped_column(
        String(36), ForeignKey("producto_ahorro.id_producto_ahorro")
    )


class ClienteCuenta(Base):
    __tablename__ = "cliente_cuenta"

    num_cuenta: Mapped[str] = mapped_column(
        String(20), ForeignKey("cuenta_ahorro.num_cuenta"), primary_key=True
    )
    id_cliente: Mapped[str] = mapped_column(
        String(36), ForeignKey("cliente.id_cliente"), primary_key=True
    )
    rol_titular: Mapped[str] = mapped_column(String(15))  # ENUM rol_titular
    fecha_vinculacion: Mapped[datetime] = mapped_column(DateTime(3))


class CtaTransaccion(Base):
    __tablename__ = "cta_transaccion"

    id_transaccion: Mapped[str] = mapped_column(String(36), primary_key=True)
    uuid_transaccion: Mapped[str] = mapped_column(String(36), unique=True)
    num_cuenta: Mapped[str] = mapped_column(
        String(20), ForeignKey("cuenta_ahorro.num_cuenta")
    )
    num_cuenta_contraparte: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    tipo_operacion: Mapped[str] = mapped_column(String(20))  # ENUM tipo_operacion
    tipo_movimiento: Mapped[str] = mapped_column(String(1))  # D | C
    monto: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    moneda: Mapped[str] = mapped_column(String(3), ForeignKey("moneda.cod_moneda"))
    id_canal: Mapped[str] = mapped_column(String(5), ForeignKey("canal.id_canal"))
    id_terminal: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("terminal.id_terminal"), nullable=True
    )
    saldo_posterior: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    comision: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    itf: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    retencion: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    estado_transaccion: Mapped[str] = mapped_column(String(15), default="APLICADA")
    idempotency_key: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True
    )
    fecha_valor: Mapped[date] = mapped_column(Date)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(3))


class CtaControlTopeDiario(Base):
    __tablename__ = "cta_control_tope_diario"
    __table_args__ = (
        UniqueConstraint(
            "num_cuenta", "id_canal", "fecha_corte",
            name="uk_tope_cuenta_canal_dia",
        ),
    )

    id_tope: Mapped[str] = mapped_column(String(36), primary_key=True)
    num_cuenta: Mapped[str] = mapped_column(
        String(20), ForeignKey("cuenta_ahorro.num_cuenta")
    )
    id_canal: Mapped[str] = mapped_column(String(5), ForeignKey("canal.id_canal"))
    fecha_corte: Mapped[date] = mapped_column(Date)
    monto_acumulado: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), default=Decimal("0")
    )
