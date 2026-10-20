"""Schemas de usuarios, roles, permisos, auditoría y reportes."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import Field

from CORE.schemas.common import CoreModel


class UsuarioCrear(CoreModel):
    username: str = Field(min_length=3, max_length=40)
    nombre: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8)
    rol: str
    id_empleado: str | None = None
    activo: bool = True
    actor: str = "sistema"
    correlation_id: str | None = None


class RolAsignar(CoreModel):
    rol: str
    actor: str = "sistema"
    correlation_id: str | None = None


class UsuarioRespuesta(CoreModel):
    id_usuario: str
    username: str
    nombre: str
    rol: str
    id_empleado: str | None
    activo: bool
    creado_en: datetime


class CatalogoPermisosRespuesta(CoreModel):
    acciones: list[str]
    permisos: dict[str, list[str]]


class PermisoAsignar(CoreModel):
    rol: str
    accion: str
    actor: str = "sistema"


class AuditoriaFiltros(CoreModel):
    desde: date | None = None
    hasta: date | None = None
    modulo: str | None = None
    accion: str | None = None
    actor: str | None = None
    correlation_id: str | None = None
    limite: int = 50
    offset: int = 0


class AuditoriaEventoRespuesta(CoreModel):
    id_evento: str
    modulo: str
    entidad: str
    id_entidad: str
    accion: str
    actor: str
    detalle: dict[str, Any] | None
    correlation_id: str | None
    fecha_hora: datetime


class CuadreContableRespuesta(CoreModel):
    fecha: str
    total_debe: Decimal
    total_haber: Decimal
    diferencia: Decimal
    cuadra: bool
    cantidad_detalles: int


class MovimientoReporteRespuesta(CoreModel):
    id_transaccion: str
    num_cuenta: str
    tipo_operacion: str
    tipo_movimiento: str
    monto: Decimal
    moneda: str
    comision: Decimal
    itf: Decimal
    retencion: Decimal
    saldo_posterior: Decimal
    id_canal: str
    num_cuenta_contraparte: str | None
    idempotency_key: str | None
    fecha_hora: datetime


class LineaAsientoRespuesta(CoreModel):
    cod_cuenta_contable: str
    debe: Decimal
    haber: Decimal
    moneda: str
    tipo_cambio: Decimal
    importe_moneda_base: Decimal


class AsientoReporteRespuesta(CoreModel):
    id_asiento: str
    fecha: datetime
    glosa: str
    estado: str
    total_debe: Decimal
    total_haber: Decimal
    lineas: list[LineaAsientoRespuesta] = []


class ReporteFechas(CoreModel):
    desde: date
    hasta: date
    limite: int = 200
    offset: int = 0
