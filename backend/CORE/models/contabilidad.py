"""Partida doble: cabecera y detalle de asientos (script 01).

RGN-01 / RGN-07 / RNF-11: todo asiento es inmutable; las correcciones
se hacen con un asiento de reversión que referencia al original
(asiento_contable.id_asiento_rev).
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from CORE.database import Base


class AsientoContable(Base):
    __tablename__ = "asiento_contable"

    id_asiento: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_periodo: Mapped[str] = mapped_column(
        String(36), ForeignKey("periodo_contable.id_periodo")
    )
    fecha: Mapped[datetime] = mapped_column(DateTime(3))
    glosa: Mapped[str] = mapped_column(String(200))
    estado: Mapped[str] = mapped_column(String(12), default="REGISTRADO")
    id_asiento_rev: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("asiento_contable.id_asiento"), nullable=True
    )


class AsientoDetalle(Base):
    __tablename__ = "asiento_detalle"

    id_detalle: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_asiento: Mapped[str] = mapped_column(
        String(36), ForeignKey("asiento_contable.id_asiento")
    )
    cod_cuenta_contable: Mapped[str] = mapped_column(
        String(20), ForeignKey("plan_cuenta_contable.cod_cuenta_contable")
    )
    debe: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    haber: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    moneda: Mapped[str] = mapped_column(String(3), ForeignKey("moneda.cod_moneda"))
    tipo_cambio: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("1"))
    importe_moneda_base: Mapped[Decimal] = mapped_column(Numeric(15, 2))
