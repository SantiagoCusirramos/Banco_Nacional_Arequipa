"""Schemas de cuentas de ahorro (VER/CREAR/MODIFICAR_CUENTA)."""

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from CORE.schemas.common import CoreModel


class TitularInput(CoreModel):
    id_cliente: str
    rol_titular: str = "TITULAR"


class CuentaCrear(CoreModel):
    id_cliente: str
    id_producto_ahorro: str
    id_agencia: str
    regimen: str = "LIBRE"
    titulares: list[TitularInput] | None = None
    actor: str = "sistema"
    correlation_id: str | None = None


class CuentaModificar(CoreModel):
    estado_cuenta: str | None = None
    actor: str = "sistema"
    correlation_id: str | None = None


class TitularRespuesta(CoreModel):
    id_cliente: str
    rol_titular: str


class CuentaRespuesta(CoreModel):
    num_cuenta: str
    moneda: str
    regimen: str
    estado_cuenta: str
    saldo_contable: Decimal
    saldo_disponible: Decimal
    saldo_retenido: Decimal
    fecha_apertura: datetime
    id_agencia: str
    id_producto_ahorro: str
    titulares: list[TitularRespuesta] = []
