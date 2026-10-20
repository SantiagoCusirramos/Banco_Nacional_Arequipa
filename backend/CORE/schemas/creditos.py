"""Schemas del ciclo de crédito (solicitud, evaluación, aprobación,
pago y deuda)."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from CORE.schemas.common import CoreModel


class FiadorInput(CoreModel):
    id_cliente: str | None = None
    cod_tipo_documento: str | None = None
    numero_documento: str | None = None
    nombre_completo: str
    telefono: str | None = None
    ingreso_mensual: Decimal | None = None
    tipo_fiador: str = "PERSONAL"


class GarantiaInput(CoreModel):
    tipo_garantia: str = "SIN_GARANTIA"
    descripcion: str | None = None
    valor_tasacion: Decimal | None = None
    entidad_registro: str | None = None
    partida_registral: str | None = None
    fecha_tasacion: date | None = None


class SolicitudCrear(CoreModel):
    id_cliente: str
    id_producto_credito: str
    monto_solicitado: Decimal = Field(gt=0)
    moneda: str = "PEN"
    plazo_meses: int = Field(gt=0)
    destino_credito: str | None = Field(default=None, max_length=120)
    id_asesor: str | None = None
    id_agencia: str | None = None
    id_caso: str | None = None
    fiadores: list[FiadorInput] = []
    garantias: list[GarantiaInput] = []
    actor: str = "sistema"
    correlation_id: str | None = None


class SituacionFinancieraInput(CoreModel):
    ingresos_mensuales: Decimal = Field(ge=0)
    egresos_mensuales: Decimal = Field(ge=0)
    patrimonio: Decimal | None = None
    cuota_otros_creditos: Decimal = Field(default=Decimal("0"), ge=0)


class EvaluacionPedir(CoreModel):
    situacion: SituacionFinancieraInput | None = None
    dias_mayor_mora: int | None = None
    actor: str = "sistema"
    correlation_id: str | None = None


class EvaluacionRespuesta(CoreModel):
    id_evaluacion: str
    id_solicitud: str
    puntaje: int
    resultado: str
    monto_maximo_sugerido: Decimal | None
    nivel_riesgo: str
    detalle_reglas: dict | None
    fecha_evaluacion: datetime


class DecisionPedir(CoreModel):
    decision: str = "APROBAR"
    id_analista: str | None = None
    monto_aprobado: Decimal | None = None
    plazo_aprobado: int | None = None
    observacion: str | None = Field(default=None, max_length=300)
    actor: str = "sistema"
    correlation_id: str | None = None


class CuotaCalendarioRespuesta(CoreModel):
    numero_cuota: int
    fecha_vencimiento: date
    cuota_total: Decimal
    saldo_final: Decimal


class CalendarioRespuesta(CoreModel):
    version: int
    tasa_tea: Decimal
    numero_cuotas: int
    monto_financiado: Decimal
    estado: str
    cuotas: list[CuotaCalendarioRespuesta] = []


class SolicitudRespuesta(CoreModel):
    id_solicitud: str
    id_cliente: str
    id_producto_credito: str
    monto_solicitado: Decimal
    moneda: str
    plazo_meses: int
    destino_credito: str | None
    estado_solicitud: str
    fecha_registro: datetime
    fiadores: list[dict] = []
    garantias: list[dict] = []
    historial: list[dict] = []
    calendario: CalendarioRespuesta | None = None
    credito_desembolsado: dict | None = None


class CuotaCobranzaRespuesta(CoreModel):
    numero_cuota: int
    fecha_vencimiento: date
    capital: Decimal
    interes: Decimal
    cuota_total: Decimal
    monto_pagado: Decimal
    estado_cuota: str


class ProximaCuotaRespuesta(CoreModel):
    numero_cuota: int
    fecha_vencimiento: date
    cuota_total: Decimal
    monto_pagado: Decimal
    estado_cuota: str


class DeudaRespuesta(CoreModel):
    id_credito: str
    id_solicitud: str
    id_cliente: str
    monto_aprobado: Decimal
    moneda: str
    tasa_tea: Decimal
    plazo_meses: int
    saldo_capital: Decimal
    saldo_mora: Decimal
    saldo_total: Decimal
    estado_credito: str
    estado_riesgo: str
    dias_mora: int
    proxima_cuota: ProximaCuotaRespuesta | None
    cuotas: list[CuotaCobranzaRespuesta] = []


class PagoRegistrar(CoreModel):
    id_credito: str
    monto: Decimal = Field(gt=0)
    id_canal_pago: str
    num_cuenta: str | None = None
    num_operacion: str = Field(min_length=1, max_length=30)
    id_cobrador: str | None = None
    actor: str = "sistema"
    correlation_id: str | None = None


class PagoRespuesta(CoreModel):
    id_pago: str
    id_credito: str
    monto: Decimal
    monto_aplicado: Decimal
    monto_no_aplicado: Decimal
    num_operacion: str
    estado_pago: str
    aplicaciones: list[dict] = []
    saldo_capital_restante: Decimal
    estado_credito: str
