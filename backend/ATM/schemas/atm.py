"""Esquemas Pydantic para el módulo ATM."""

from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ── Validar PIN ──────────────────────────────────────────────────────────

class ValidarPinIn(_Entrada):
    id_tarjeta: str = Field(min_length=36, max_length=36)
    pin: str = Field(min_length=4, max_length=6, pattern=r"^\d+$")
    id_terminal: str = Field(min_length=1, max_length=30)


class ValidarPinOut(BaseModel):
    resultado: Literal["EXITOSO", "FALLIDO"]
    intentos_restantes: int


# ── Autorizar Retiro ─────────────────────────────────────────────────────

class AutorizarIn(_Entrada):
    id_tarjeta: str = Field(min_length=36, max_length=36)
    num_cuenta: str = Field(min_length=1, max_length=20)
    moneda: Literal["PEN", "USD"]
    monto: str = Field(pattern=r"^\d+(\.\d{1,2})?$")
    id_canal: str | None = Field(default=None, min_length=1, max_length=5)
    id_terminal: str | None = Field(default=None, min_length=1, max_length=30)
    uuid_transaccion: str = Field(min_length=36, max_length=36)

    @field_validator("monto")
    @classmethod
    def _validar_monto(cls, v: str) -> str:
        try:
            valor = Decimal(v)
        except Exception:
            raise ValueError("monto debe ser un decimal válido")
        if valor <= 0 or valor != int(valor) or int(valor) % 10 != 0:
            raise ValueError("monto debe ser múltiplo de 10")
        return v


from pydantic import computed_field

class AutorizacionOut(BaseModel):
    uuid_autorizacion: str
    id_tarjeta: str
    num_cuenta: str
    id_canal: str | None
    id_terminal: str | None
    tipo_operacion: str
    monto: Decimal
    estado_autorizacion: str
    codigo_respuesta: str | None
    motivo_rechazo: str | None
    uuid_transaccion: str | None = None
    id_contra_asiento: str | None = None
    saldo_disponible: str | None = None

    @computed_field
    @property
    def aprobada(self) -> bool:
        return self.estado_autorizacion == "AUTORIZADA"


# ── Confirmar Dispensación ───────────────────────────────────────────────

class ConfirmarIn(_Entrada):
    uuid_autorizacion: str = Field(min_length=36, max_length=36)
    id_canal: str | None = Field(default=None, min_length=1, max_length=5)
    id_terminal: str | None = Field(default=None, min_length=1, max_length=30)
    resultado: Literal["DISPENSADO", "NO_DISPENSADO"]


# ── Extorno ──────────────────────────────────────────────────────────────

class ExtornarIn(_Entrada):
    uuid_autorizacion: str = Field(min_length=36, max_length=36)
    motivo: str = Field(min_length=3, max_length=255)


# ── Consultar Saldo ──────────────────────────────────────────────────────

class CuentaSaldoOut(BaseModel):
    id_cuenta: str
    num_cuenta_enmascarado: str
    moneda: str
    saldo_disponible: str


class SaldoOut(BaseModel):
    lista_cuentas: list[CuentaSaldoOut]
    uuid_consulta: str
    simulado: bool = False


# ── Consultar Movimientos ────────────────────────────────────────────────

class MovimientoOut(BaseModel):
    uuid_transaccion: str
    tipo_operacion: str
    naturaleza: str
    monto: str
    fecha_hora: str


# ── Estado / Config ──────────────────────────────────────────────────────

class BandejasOut(BaseModel):
    PEN: dict[str, int]
    USD: dict[str, int]


class EstadoOut(BaseModel):
    terminal: str
    bandejas: BandejasOut
    pendientes: list[dict]
    pruebas: dict | None = None


class ConfigOut(BaseModel):
    id_cajero: str
    pruebas: bool