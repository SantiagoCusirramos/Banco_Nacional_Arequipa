"""Ciclo del crédito: solicitud, evaluación y cobranza
(scripts 06_solicitud.sql, 07_evaluacion.sql, 09_cobranza.sql).

CORE administra estas entidades como puente único con la BD; los
módulos de Solicitud/Evaluación/Desembolso/Cobranza invocan estas
acciones a través del Bus.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from CORE.database import Base


# ---------------------------------------------------------------------
# Solicitud de crédito (06)
# ---------------------------------------------------------------------
class SolSolicitud(Base):
    __tablename__ = "sol_solicitud"

    id_solicitud: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_cliente: Mapped[str] = mapped_column(String(36), ForeignKey("cliente.id_cliente"))
    id_caso: Mapped[str | None] = mapped_column(String(36), nullable=True)
    id_producto_credito: Mapped[str] = mapped_column(
        String(36), ForeignKey("producto_credito.id_producto_credito")
    )
    id_asesor: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("empleado.id_empleado"), nullable=True
    )
    id_agencia: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agencia.id_agencia"), nullable=True
    )
    monto_solicitado: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    moneda: Mapped[str] = mapped_column(String(3), ForeignKey("moneda.cod_moneda"))
    plazo_meses: Mapped[int] = mapped_column()
    destino_credito: Mapped[str | None] = mapped_column(String(120), nullable=True)
    estado_solicitud: Mapped[str] = mapped_column(String(18), default="REGISTRADA")
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(3))


class SolFiador(Base):
    __tablename__ = "sol_fiador"

    id_fiador: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_solicitud: Mapped[str] = mapped_column(
        String(36), ForeignKey("sol_solicitud.id_solicitud")
    )
    id_cliente: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("cliente.id_cliente"), nullable=True
    )
    cod_tipo_documento: Mapped[str | None] = mapped_column(
        String(10), ForeignKey("tipo_documento.cod_tipo_documento"), nullable=True
    )
    numero_documento: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nombre_completo: Mapped[str] = mapped_column(String(140))
    telefono: Mapped[str | None] = mapped_column(String(15), nullable=True)
    ingreso_mensual: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    tipo_fiador: Mapped[str] = mapped_column(String(15))


class SolGarantia(Base):
    __tablename__ = "sol_garantia"

    id_garantia: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_solicitud: Mapped[str] = mapped_column(
        String(36), ForeignKey("sol_solicitud.id_solicitud")
    )
    tipo_garantia: Mapped[str] = mapped_column(String(18))
    descripcion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    valor_tasacion: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    entidad_registro: Mapped[str | None] = mapped_column(String(100), nullable=True)
    partida_registral: Mapped[str | None] = mapped_column(String(40), nullable=True)
    fecha_tasacion: Mapped[date | None] = mapped_column(Date, nullable=True)


class SolHistorialEstado(Base):
    __tablename__ = "sol_historial_estado"

    id_historial: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_solicitud: Mapped[str] = mapped_column(
        String(36), ForeignKey("sol_solicitud.id_solicitud")
    )
    estado_anterior: Mapped[str | None] = mapped_column(String(18), nullable=True)
    estado_nuevo: Mapped[str] = mapped_column(String(18))
    motivo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    id_usuario: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("usuario_sistema.id_usuario"), nullable=True
    )
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(3))


class SolCalendarioVersion(Base):
    __tablename__ = "sol_calendario_version"

    id_calendario: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_solicitud: Mapped[str] = mapped_column(
        String(36), ForeignKey("sol_solicitud.id_solicitud"), unique=True
    )
    version: Mapped[int] = mapped_column()
    tasa_tea: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    numero_cuotas: Mapped[int] = mapped_column()
    monto_financiado: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    estado: Mapped[str] = mapped_column(String(12), default="SIMULADO")
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(3))


class SolCuotaCalendario(Base):
    __tablename__ = "sol_cuota_calendario"

    id_cuota: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_calendario: Mapped[str] = mapped_column(
        String(36), ForeignKey("sol_calendario_version.id_calendario")
    )
    numero_cuota: Mapped[int] = mapped_column()
    fecha_vencimiento: Mapped[date] = mapped_column(Date)
    saldo_inicial: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    amortizacion: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    interes: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    cuota_total: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    saldo_final: Mapped[Decimal] = mapped_column(Numeric(15, 2))


# ---------------------------------------------------------------------
# Evaluación (07)
# ---------------------------------------------------------------------
class EvaRegla(Base):
    __tablename__ = "eva_regla"

    id_regla: Mapped[str] = mapped_column(String(36), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)
    descripcion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    variable: Mapped[str] = mapped_column(String(60))
    operador: Mapped[str] = mapped_column(String(10))  # MAYOR|MENOR|IGUAL|ENTRE|EXCLUYE
    valor_min: Mapped[Decimal | None] = mapped_column(Numeric(15, 4), nullable=True)
    valor_max: Mapped[Decimal | None] = mapped_column(Numeric(15, 4), nullable=True)
    resultado: Mapped[str] = mapped_column(String(10))  # APROBAR|OBSERVAR|RECHAZAR
    peso: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("1"))
    activa: Mapped[bool] = mapped_column(default=True)


class EvaSituacionFinanciera(Base):
    __tablename__ = "eva_situacion_financiera"

    id_situacion: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_solicitud: Mapped[str] = mapped_column(
        String(36), ForeignKey("sol_solicitud.id_solicitud")
    )
    id_cliente: Mapped[str] = mapped_column(String(36), ForeignKey("cliente.id_cliente"))
    ingresos_mensuales: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    egresos_mensuales: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    patrimonio: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    cuota_otros_creditos: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    ratio_capacidad: Mapped[Decimal | None] = mapped_column(
        Numeric(9, 4), nullable=True
    )
    fecha_declaracion: Mapped[datetime] = mapped_column(DateTime(3))


class EvaEvaluacion(Base):
    __tablename__ = "eva_evaluacion"

    id_evaluacion: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_solicitud: Mapped[str] = mapped_column(
        String(36), ForeignKey("sol_solicitud.id_solicitud")
    )
    puntaje: Mapped[int] = mapped_column()
    resultado: Mapped[str] = mapped_column(String(12))
    monto_maximo_sugerido: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    nivel_riesgo: Mapped[str] = mapped_column(String(12))
    detalle_reglas: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fecha_evaluacion: Mapped[datetime] = mapped_column(DateTime(3))


class EvaDecisionAnalista(Base):
    __tablename__ = "eva_decision_analista"

    id_decision: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_evaluacion: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("eva_evaluacion.id_evaluacion"), nullable=True
    )
    id_analista: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("empleado.id_empleado"), nullable=True
    )
    decision: Mapped[str] = mapped_column(String(12))
    monto_aprobado: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    plazo_aprobado: Mapped[int | None] = mapped_column(nullable=True)
    observacion: Mapped[str | None] = mapped_column(String(300), nullable=True)
    fecha_decision: Mapped[datetime] = mapped_column(DateTime(3))


# ---------------------------------------------------------------------
# Cobranza (09)
# ---------------------------------------------------------------------
class CobCanalPago(Base):
    __tablename__ = "canal_pago"

    id_canal_pago: Mapped[str] = mapped_column(String(36), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(40), unique=True)
    tipo: Mapped[str] = mapped_column(String(18))
    activo: Mapped[bool] = mapped_column(default=True)


class CobCredito(Base):
    __tablename__ = "cob_credito"

    id_credito: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_solicitud: Mapped[str] = mapped_column(
        String(36), ForeignKey("sol_solicitud.id_solicitud")
    )
    id_cliente: Mapped[str] = mapped_column(String(36), ForeignKey("cliente.id_cliente"))
    num_cuenta_desembolso: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("cuenta_ahorro.num_cuenta"), nullable=True
    )
    monto_aprobado: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    moneda: Mapped[str] = mapped_column(String(3), ForeignKey("moneda.cod_moneda"))
    tasa_tea: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    plazo_meses: Mapped[int] = mapped_column()
    saldo_capital: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    estado_credito: Mapped[str] = mapped_column(String(12), default="VIGENTE")
    dias_mora: Mapped[int] = mapped_column(default=0)
    fecha_desembolso: Mapped[date | None] = mapped_column(Date, nullable=True)


class CobCuota(Base):
    __tablename__ = "cob_cuota"

    id_cuota_credito: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_credito: Mapped[str] = mapped_column(
        String(36), ForeignKey("cob_credito.id_credito")
    )
    numero_cuota: Mapped[int] = mapped_column()
    fecha_vencimiento: Mapped[date] = mapped_column(Date)
    capital: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    interes: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    seguro: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    cuota_total: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    saldo_capital: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    monto_pagado: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    estado_cuota: Mapped[str] = mapped_column(String(12), default="PENDIENTE")


class CobPago(Base):
    __tablename__ = "cob_pago"

    id_pago: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_credito: Mapped[str] = mapped_column(
        String(36), ForeignKey("cob_credito.id_credito")
    )
    id_canal_pago: Mapped[str] = mapped_column(
        String(36), ForeignKey("canal_pago.id_canal_pago")
    )
    num_cuenta: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("cuenta_ahorro.num_cuenta"), nullable=True
    )
    monto: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    moneda: Mapped[str] = mapped_column(String(3), ForeignKey("moneda.cod_moneda"))
    num_operacion: Mapped[str] = mapped_column(String(30), unique=True)
    id_cobrador: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("empleado.id_empleado"), nullable=True
    )
    estado_pago: Mapped[str] = mapped_column(String(12), default="REGISTRADO")
    fecha_pago: Mapped[datetime] = mapped_column(DateTime(3))


class CobAplicacionPago(Base):
    __tablename__ = "cob_aplicacion_pago"

    id_aplicacion: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_pago: Mapped[str] = mapped_column(String(36), ForeignKey("cob_pago.id_pago"))
    id_cuota_credito: Mapped[str] = mapped_column(
        String(36), ForeignKey("cob_cuota.id_cuota_credito")
    )
    aplica_capital: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    aplica_interes: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    aplica_seguro: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    aplica_mora: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    fecha_aplicacion: Mapped[datetime] = mapped_column(DateTime(3))


class CobMora(Base):
    __tablename__ = "cob_mora"

    id_mora: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_cuota_credito: Mapped[str] = mapped_column(
        String(36), ForeignKey("cob_cuota.id_cuota_credito")
    )
    dias_atraso: Mapped[int] = mapped_column(default=0)
    tasa_mora: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    interes_mora: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    estado_mora: Mapped[str] = mapped_column(String(12), default="PENDIENTE")
    vigente_flag: Mapped[int] = mapped_column(default=1)
    fecha_calculo: Mapped[datetime] = mapped_column(DateTime(3))
