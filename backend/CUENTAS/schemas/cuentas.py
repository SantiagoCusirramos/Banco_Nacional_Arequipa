from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# regimenes que acepta COREDB (tabla cuentas.regimen_cuenta)
Regimen = Literal["INDIVIDUAL", "MANCOMUNADA_INDISTINTA", "MANCOMUNADA_CONJUNTA"]


class TitularIn(BaseModel):
    id_cliente: str = Field(min_length=1)
    # COREDB no guarda el rol: lo define el regimen
    rol_titular: str | None = None


class AbrirCuentaIn(BaseModel):
    num_cuenta: str = Field(min_length=1, max_length=20)
    cci: str = Field(min_length=20, max_length=20)
    moneda: Literal["PEN", "USD"] = "PEN"
    regimen: Regimen = "INDIVIDUAL"
    id_agencia: str | None = Field(default=None, max_length=10)
    titulares: list[TitularIn] | None = None
    # atajo para una cuenta individual: se convierte en un titular
    id_cliente: str | None = None
    # se acepta pero COREDB no lo usa
    id_producto_ahorro: str | None = None

    @model_validator(mode="after")
    def _completar_titulares(self):
        if not self.titulares and self.id_cliente:
            self.titulares = [TitularIn(id_cliente=self.id_cliente)]
        if not self.titulares:
            raise ValueError("Se requiere al menos un titular")
        return self


class OperacionIn(BaseModel):
    num_cuenta: str = Field(max_length=20)
    monto: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    glosa: str | None = Field(default=None, min_length=1, max_length=200)
    # se aceptan pero COREDB no los usa
    moneda: Literal["PEN", "USD"] | None = None
    id_terminal: str | None = Field(default=None, max_length=15)


class TransferenciaIn(BaseModel):
    num_cuenta_origen: str = Field(max_length=20)
    num_cuenta_destino: str = Field(max_length=20)
    monto: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    glosa: str | None = Field(default=None, min_length=1, max_length=200)
    moneda: Literal["PEN", "USD"] | None = None
    id_terminal: str | None = Field(default=None, max_length=15)


class CuentaOut(BaseModel):
    num_cuenta: str
    cci: str
    moneda: str
    regimen: str
    estado_cuenta: str
    saldo_contable: Decimal
    saldo_disponible: Decimal
    id_agencia: str | None = None
    # codigos de los clientes titulares, como los devuelve COREDB
    titulares: list[str] = []


class MovimientoOut(BaseModel):
    uuid_transaccion: str
    replay: bool = False


class TransferenciaOut(BaseModel):
    uuid_debito: str
    uuid_abono: str
    replay: bool = False
