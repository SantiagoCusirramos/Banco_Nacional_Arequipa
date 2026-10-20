"""Schemas de movimientos (REGISTRAR_MOVIMIENTO: depósitos, retiros y
transferencias)."""

from decimal import Decimal

from pydantic import Field

from CORE.schemas.common import CoreModel


class MovimientoRegistrar(CoreModel):
    tipo_operacion: str = Field(pattern="^(DEPOSITO|RETIRO)$")
    num_cuenta: str
    monto: Decimal = Field(gt=0)
    moneda: str | None = None
    id_canal: str
    id_terminal: str | None = None
    num_cuenta_contraparte: str | None = None
    idempotency_key: str | None = Field(default=None, max_length=64)
    comision: Decimal = Decimal("0")
    itf: Decimal = Decimal("0")
    retencion: Decimal = Decimal("0")
    actor: str = "sistema"
    correlation_id: str | None = None


class TransferenciaRegistrar(CoreModel):
    num_cuenta_origen: str
    num_cuenta_destino: str
    monto: Decimal = Field(gt=0)
    moneda: str | None = None
    id_canal: str
    id_terminal: str | None = None
    idempotency_key: str | None = Field(default=None, max_length=64)
    actor: str = "sistema"
    correlation_id: str | None = None


class MovimientoRespuesta(CoreModel):
    id_transaccion: str
    uuid_transaccion: str
    num_cuenta: str
    tipo_operacion: str
    tipo_movimiento: str
    monto: Decimal
    moneda: str
    monto_moneda_base: Decimal
    saldo_posterior: Decimal
    id_asiento: str
    num_cuenta_contraparte: str | None = None
    idempotency_key: str | None = None
    replay: bool = False


class TransferenciaRespuesta(CoreModel):
    origen: MovimientoRespuesta
    destino: MovimientoRespuesta
    id_asiento: str
    replay: bool = False
