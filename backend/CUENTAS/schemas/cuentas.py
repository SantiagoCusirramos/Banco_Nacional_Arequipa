from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Canal(str, Enum):
    ATM = "ATM"
    AGE = "AGE"
    VEN = "VEN"
    HB = "HB"
    BD = "BD"


class TitularIn(BaseModel):
    id_cliente: str
    rol_titular: Literal["TITULAR", "MANCOMUNADO", "APODERADO", "TUTOR", "BENEFICIARIO"] = "TITULAR"


class AbrirCuentaIn(BaseModel):
    id_cliente: str
    id_producto_ahorro: str
    id_agencia: str
    regimen: Literal["LIBRE", "PROGRAMADO", "INFANTIL", "CTS", "A_PLAZO"] = "LIBRE"
    titulares: list[TitularIn] | None = None


class OperacionIn(BaseModel):
    monto: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    id_canal: Canal
    moneda: Literal["PEN", "USD"] | None = None
    id_terminal: str | None = None


class TransferenciaIn(OperacionIn):
    num_cuenta_destino: str


class TitularOut(BaseModel):
    id_cliente: str
    rol_titular: str


class CuentaOut(BaseModel):
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
    titulares: list[TitularOut] = []


class MovimientoOut(BaseModel):
    id_transaccion: str
    uuid_transaccion: str
    num_cuenta: str
    tipo_operacion: str
    tipo_movimiento: str
    monto: Decimal
    moneda: str
    saldo_posterior: Decimal
    id_asiento: str
    num_cuenta_contraparte: str | None = None
    idempotency_key: str | None = None
    replay: bool = False


class TransferenciaOut(BaseModel):
    origen: MovimientoOut
    destino: MovimientoOut
    id_asiento: str
    replay: bool = False
