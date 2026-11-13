from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

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

    @computed_field
    @property
    def numero_enmascarado(self) -> str:
        return f"{self.bin[:4]} {self.bin[4:]}** **** {self.ultimos4}"

    @computed_field
    @property
    def vencimiento_mm_aa(self) -> str:
        # RN-TAR-003: como se imprime en la tarjeta
        return self.fecha_vencimiento.strftime("%m/%y")
