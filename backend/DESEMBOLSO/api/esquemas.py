"""Contratos de entrada y salida de la API (documentados en OpenAPI)."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class PrepararOrden(BaseModel):
    aprobacion_id: str = Field(min_length=1, max_length=36, examples=["APR-2026-0001"])


class ValidarIdentidad(BaseModel):
    """Sin módulo Clientes en el producto: el operador verifica el documento original del titular y
    registra su número, que se compara con el de Evaluación. No se intercambia biometría."""
    metodo: Literal["VERIFICACION_PRESENCIAL"] = "VERIFICACION_PRESENCIAL"
    numero_documento: str = Field(min_length=6, max_length=12, pattern=r"^[A-Za-z0-9]+$",
                                  description="Número del documento presentado por el titular")


class SeleccionarCuenta(BaseModel):
    cuenta_id: str = Field(min_length=1, max_length=36)
    version: int = Field(ge=0)


class Confirmar(BaseModel):
    version: int = Field(ge=0, description="Versión de la orden que vio el operador (RT-02)")


class SolicitarReversion(BaseModel):
    motivo: str = Field(min_length=5, max_length=255)
    origen: Literal["SOLICITUD_SERVICIO", "INCIDENTE"] = "SOLICITUD_SERVICIO"


class DecisionReversion(BaseModel):
    aprobar: bool
    motivo: str | None = Field(default=None, max_length=255)


class Conciliar(BaseModel):
    fecha: date
    moneda: Literal["PEN", "USD"] | None = None


class Aprobacion(BaseModel):
    aprobacion_id: str
    version: int
    credito_id: str
    cliente_id: str
    cliente_nombre: str
    cliente_documento: str | None
    producto: str
    importe: str
    moneda: str
    plazo_meses: int | None
    tasa_tea: str | None
    estado: str
    vigente_hasta: str | None


class OrdenBreve(BaseModel):
    id: str
    codigo_orden: str
    estado: str


class CreditoHabilitado(Aprobacion):
    habilitada: bool
    motivo: str | None
    orden_existente: OrdenBreve | None


class ValidacionSalida(BaseModel):
    id: str
    tipo: str
    fase: str
    proveedor: str
    referencia_evidencia: str
    resultado: str
    detalle: str | None
    vence_en: str | None
    creado_en: str | None


class EventoSalida(BaseModel):
    id: str
    tipo: str
    estado: str
    intentos: int
    siguiente_intento: str | None
    confirmacion_id: str | None
    ultimo_error: str | None
    creado_en: str | None


class ReversionSalida(BaseModel):
    id: str
    orden_id: str
    motivo: str
    origen: str
    estado: str
    solicitante_id: str
    autorizador_id: str | None
    motivo_rechazo: str | None
    reversion_financiera_id: str | None
    creado_en: str | None
    actualizado_en: str | None
    codigo_orden: str | None = None


class OrdenResumen(BaseModel):
    id: str
    codigo_orden: str
    estado: str
    entrega_estado: str
    motivo_rechazo: str | None
    aprobacion_id: str
    aprobacion_version: int
    credito_id: str
    cliente_id: str
    cuenta_id: str | None
    importe: str
    moneda: str
    operacion_financiera_id: str | None
    fecha_efectiva: str | None
    idempotency_key: str
    canal: str
    agencia_id: str | None
    usuario_preparacion: str
    usuario_confirmacion: str | None
    correlation_id: str
    version: int
    creado_en: str | None
    actualizado_en: str | None


class Identidad(BaseModel):
    resultado: str
    vence_en: str | None
    detalle: str | None


class Cuota(BaseModel):
    """Una cuota del calendario de Solicitud, como llegó con la aprobación."""
    numeroCuota: int
    fechaVencimiento: str
    amortizacion: str | None = None
    interes: str | None = None
    cuotaTotal: str
    saldoFinal: str | None = None


class OrdenDetalle(OrdenResumen):
    cuenta_enmascarada: str | None
    identidad: Identidad | None
    aprobacion: Aprobacion | None
    solicitud_id: str | None
    calendario: list[Cuota]
    validaciones: list[ValidacionSalida]
    eventos: list[EventoSalida]
    reversiones: list[ReversionSalida]
    acciones: list[str]


class PaginaOrdenes(BaseModel):
    items: list[OrdenResumen]
    total: int
    pagina: int
    tamano: int


class CuentaElegible(BaseModel):
    cuenta_id: str
    numero_enmascarado: str
    producto: str
    moneda: str
    estado: str
    titularidad: str
    elegible: bool
    motivo: str | None


class Constancia(BaseModel):
    codigo_orden: str
    estado: str
    operacion_financiera_id: str | None
    fecha_efectiva: str | None
    credito_id: str
    aprobacion_id: str
    producto: str | None
    plazo_meses: int | None
    tasa_tea: str | None
    cliente_nombre: str | None
    cliente_documento: str | None
    cuenta_enmascarada: str | None
    importe: str
    moneda: str
    agencia: str | None
    usuario_preparacion: str
    usuario_confirmacion: str | None
    entrega_estado: str
    correlation_id: str
    emitida_en: str
    emitida_por: str


class Sesion(BaseModel):
    usuario: str
    nombre: str
    rol: str
    permisos: list[str]
    agencia_id: str | None
    agencia_nombre: str | None
    reversion_habilitada: bool
