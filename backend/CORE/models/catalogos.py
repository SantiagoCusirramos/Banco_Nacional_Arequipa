"""Catálogos y parámetros globales del CORE (script 01_catalogos_comunes.sql).

RF-COR-12 (monedas), RF-COR-13 (tipo de cambio), RF-COR-15/16/17
(agencias, operadores/empleados, terminales), RF-COR-26 (parámetros
globales vía límites por canal).
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from CORE.database import Base


class Agencia(Base):
    __tablename__ = "agencia"

    id_agencia: Mapped[str] = mapped_column(String(36), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60), unique=True)
    direccion: Mapped[str] = mapped_column(String(120))
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class Empleado(Base):
    __tablename__ = "empleado"

    id_empleado: Mapped[str] = mapped_column(String(36), primary_key=True)
    codigo_empleado: Mapped[str] = mapped_column(String(20), unique=True)
    nombre_completo: Mapped[str] = mapped_column(String(100))
    cargo: Mapped[str] = mapped_column(String(30))  # ENUM empleado
    id_agencia: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agencia.id_agencia"), nullable=True
    )
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class TipoDocumento(Base):
    __tablename__ = "tipo_documento"

    cod_tipo_documento: Mapped[str] = mapped_column(String(10), primary_key=True)
    descripcion: Mapped[str] = mapped_column(String(50))


class Moneda(Base):
    __tablename__ = "moneda"

    cod_moneda: Mapped[str] = mapped_column(String(3), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(30))
    simbolo: Mapped[str] = mapped_column(String(5))
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class TipoCambio(Base):
    __tablename__ = "tipo_cambio"
    __table_args__ = (
        Index(
            "uk_tc_monedas_fecha",
            "cod_moneda_origen",
            "cod_moneda_destino",
            "fecha",
            unique=True,
        ),
    )

    id_tipo_cambio: Mapped[str] = mapped_column(String(36), primary_key=True)
    cod_moneda_origen: Mapped[str] = mapped_column(
        String(3), ForeignKey("moneda.cod_moneda")
    )
    cod_moneda_destino: Mapped[str] = mapped_column(
        String(3), ForeignKey("moneda.cod_moneda")
    )
    fecha: Mapped[date] = mapped_column(Date)
    tasa: Mapped[Decimal] = mapped_column(Numeric(12, 6))


class Terminal(Base):
    __tablename__ = "terminal"

    id_terminal: Mapped[str] = mapped_column(String(36), primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True)
    tipo: Mapped[str] = mapped_column(String(10))  # ENUM terminal
    ubicacion: Mapped[str | None] = mapped_column(String(120), nullable=True)
    id_agencia: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agencia.id_agencia"), nullable=True
    )
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class Canal(Base):
    __tablename__ = "canal"

    id_canal: Mapped[str] = mapped_column(String(5), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(40), unique=True)
    es_presencial: Mapped[bool] = mapped_column(Boolean)
    validacion_requerida: Mapped[str] = mapped_column(String(20))
    requiere_token_matriz: Mapped[bool] = mapped_column(Boolean, default=False)
    tipo_integracion: Mapped[str] = mapped_column(String(30), default="BUS_SERVICIOS")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class LimiteCanal(Base):
    __tablename__ = "limite_canal"

    id_canal: Mapped[str] = mapped_column(
        String(5), ForeignKey("canal.id_canal"), primary_key=True
    )
    moneda: Mapped[str] = mapped_column(
        String(3), ForeignKey("moneda.cod_moneda"), primary_key=True
    )
    monto_maximo_diario: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )  # NULL = sin limite
    habilitado: Mapped[bool] = mapped_column(Boolean, default=True)
    regla_negocio: Mapped[str] = mapped_column(String(40))


class ProductoAhorro(Base):
    __tablename__ = "producto_ahorro"

    id_producto_ahorro: Mapped[str] = mapped_column(String(36), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60))
    moneda: Mapped[str] = mapped_column(String(3), ForeignKey("moneda.cod_moneda"))
    tasa_tea: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal("0"))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class ProductoCredito(Base):
    __tablename__ = "producto_credito"

    id_producto_credito: Mapped[str] = mapped_column(String(36), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60))
    tasa_tea: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    plazo_min_meses: Mapped[int] = mapped_column(default=1)
    plazo_max_meses: Mapped[int] = mapped_column(default=60)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class PeriodoContable(Base):
    __tablename__ = "periodo_contable"

    id_periodo: Mapped[str] = mapped_column(String(36), primary_key=True)
    anio: Mapped[int] = mapped_column()
    mes: Mapped[int] = mapped_column()
    fecha_inicio: Mapped[date] = mapped_column(Date)
    fecha_fin: Mapped[date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(10), default="ABIERTO")


class PlanCuentaContable(Base):
    __tablename__ = "plan_cuenta_contable"

    cod_cuenta_contable: Mapped[str] = mapped_column(String(20), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    naturaleza: Mapped[str] = mapped_column(String(10))  # DEUDORA | ACREEDORA
    codigo_padre: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("plan_cuenta_contable.cod_cuenta_contable"),
        nullable=True,
    )
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
