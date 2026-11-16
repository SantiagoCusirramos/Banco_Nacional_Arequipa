import re
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, computed_field, field_validator, model_validator

# Estados que se pueden pedir. COREDB traduce ANULADA a CANCELADA; el desbloqueo
# (de BLOQUEADA a ACTIVA) lo rechaza: es de Seguridad.
EstadoPedible = Literal["ACTIVA", "BLOQUEADA", "RETENIDA", "ANULADA"]


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EmisionIn(_Entrada):
    cod_cliente: str = Field(min_length=1, max_length=12, pattern=r"^[A-Za-z0-9]+$")
    num_cuenta: str = Field(min_length=1, max_length=20)
    # BIN de desarrollo, FISICA. Los reales son un pendiente del emisor (issue #34, pregunta 7).
    bin: str = Field(default="004499", pattern=r"^[0-9]{6}$")
    fecha_emision: date | None = Field(default=None, description="Hoy si no se envía.")
    fecha_vencimiento: date | None = Field(default=None, description="Cuatro años después de la emisión si no se envía.")
    ultimos4: str | None = Field(default=None, pattern=r"^[0-9]{4}$",
                                 description="Los últimos cuatro dígitos del PAN. El PAN nunca se envía.")

    @model_validator(mode="after")
    def _vigencia(self):
        # RN-TAR-003: una tarjeta vence después de emitirse
        if self.fecha_emision and self.fecha_vencimiento and self.fecha_vencimiento <= self.fecha_emision:
            raise ValueError("fecha_vencimiento debe ser posterior a fecha_emision")
        return self


class BloqueoIn(_Entrada):
    motivo: str = Field(min_length=3, max_length=255)


class EstadoIn(_Entrada):
    estado: EstadoPedible
    motivo: str | None = Field(default=None, max_length=255)


class TarjetaOut(BaseModel):
    id_tarjeta: str
    bin: str
    ultimos4: str
    fecha_emision: date
    fecha_vencimiento: date
    estado_tarjeta: str
    cod_cliente: str
    # La cuenta principal, la de la emisión; null si COREDB no la tiene
    num_cuenta: str | None = None

    @computed_field
    @property
    def numero_enmascarado(self) -> str:
        return f"{self.bin[:4]} {self.bin[4:]}** **** {self.ultimos4}"

    @computed_field
    @property
    def vencimiento_mm_aa(self) -> str:
        # RN-TAR-003: como se imprime en la tarjeta
        return self.fecha_vencimiento.strftime("%m/%y")


# Operaciones de débito que una tarjeta autoriza (cuentas.tipo_operacion, naturaleza D).
OperacionTarjeta = Literal["RETIRO", "PAGO", "FONDEO_BILLETERA"]
TipoCredencial = Literal["PIN_ATM", "CLAVE_WEB"]


class _ConCanal(_Entrada):
    id_canal: str | None = Field(default=None, min_length=1, max_length=5,
                                 description="ATM, AGE, VEN, HB o BD. O el canal o la terminal.")
    id_terminal: str | None = Field(default=None, min_length=1, max_length=30)

    @model_validator(mode="after")
    def _canal_o_terminal(self):
        if (self.id_canal is None) == (self.id_terminal is None):
            raise ValueError("Se indica id_canal o id_terminal, uno de los dos")
        return self


class AutorizacionIn(_ConCanal):
    num_cuenta: str = Field(min_length=1, max_length=20)
    tipo_operacion: OperacionTarjeta = "RETIRO"
    monto: Decimal = Field(gt=0, max_digits=15, decimal_places=2)


class ExtornoIn(_Entrada):
    motivo: str = Field(min_length=3, max_length=255)


def _solo_digitos(valor: SecretStr) -> SecretStr:
    # COREDB exige 4 dígitos al PIN y 6 a la clave web (RN-TAR-001). El error no repite el valor.
    if not re.fullmatch(r"[0-9]{4,6}", valor.get_secret_value()):
        raise ValueError("La clave debe tener de 4 a 6 dígitos")
    return valor


class CredencialIn(_Entrada):
    # Nunca se devuelve ni se registra.
    valor: SecretStr

    _digitos = field_validator("valor")(_solo_digitos)


class ValidacionIn(_ConCanal):
    valor: SecretStr

    _digitos = field_validator("valor")(_solo_digitos)


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

    @computed_field
    @property
    def aprobada(self) -> bool:
        return self.estado_autorizacion == "AUTORIZADA"


class ValidacionOut(BaseModel):
    resultado: Literal["EXITOSO", "FALLIDO"]
    intentos_restantes: int
