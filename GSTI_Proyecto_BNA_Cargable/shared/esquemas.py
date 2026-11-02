"""Esquemas Pydantic compartidos: UNA sola definición de las reglas de validación.

Los usan el módulo de Clientes (primera barrera) y el Core (segunda barrera).
"""
import re
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

MODULOS_ORIGEN = ("BANCA_LINEA", "CAJERO_AUTOMATICO", "AGENCIAS", "BILLETERA_DIGITAL", "CUENTAS", "TARJETAS", "CREDITOS", "SEGURIDAD")
ModuloOrigen = Literal["BANCA_LINEA", "CAJERO_AUTOMATICO", "AGENCIAS", "BILLETERA_DIGITAL", "CUENTAS", "TARJETAS", "CREDITOS", "SEGURIDAD"]
TipoDocumento = Literal["DNI", "PASAPORTE", "PTP"]

FORMATO_FACIAL = "ARCFACE_EMBEDDING"
FORMATO_HUELLA = "ISO_19794_2_2005"
DIM_EMBEDDING = 512
MAX_TEMPLATE_HUELLA_B64 = 65536

# str estricto: un número JSON (12345678) se rechaza; los documentos y teléfonos son SIEMPRE cadenas.
Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100, strict=True)]
Cadena = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20, strict=True)]

_FORMATO_DOC = {
    "DNI": (re.compile(r"^\d{8}$"), "El DNI debe tener exactamente 8 dígitos"),
    "PASAPORTE": (re.compile(r"^[A-Z0-9]{6,12}$"), "El pasaporte debe tener 6 a 12 letras o dígitos"),
    "PTP": (re.compile(r"^[A-Z0-9]{6,15}$"), "El PTP debe tener 6 a 15 letras o dígitos"),
}
_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
_FECHA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _fecha_iso(valor):
    """Acepta solo cadenas AAAA-MM-DD (o un date ya construido)."""
    if isinstance(valor, date):
        return valor
    if not isinstance(valor, str) or not _FECHA_ISO.match(valor):
        raise ValueError("La fecha debe tener el formato AAAA-MM-DD")
    return valor


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DocumentoBase(Base):
    modulo_origen: ModuloOrigen
    tipo_documento: TipoDocumento
    numero_documento: Cadena

    @model_validator(mode="after")
    def _validar_documento(self):
        self.numero_documento = self.numero_documento.upper()
        patron, mensaje = _FORMATO_DOC[self.tipo_documento]
        if not patron.match(self.numero_documento):
            raise ValueError(mensaje)
        return self


class ValidarDocumentoIn(DocumentoBase):
    fecha_nacimiento: date

    _f = field_validator("fecha_nacimiento", mode="before")(_fecha_iso)

    @field_validator("fecha_nacimiento")
    @classmethod
    def _rango(cls, v: date):
        if v < date(1900, 1, 1) or v > date.today():
            raise ValueError("La fecha de nacimiento está fuera de rango")
        return v


class DatosCliente(ValidarDocumentoIn):
    nombres: Texto
    apellidos: Texto
    ingreso_mensual: Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
    direccion: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=200, strict=True)]
    correo: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120, strict=True)]
    telefono: Cadena

    @field_validator("correo")
    @classmethod
    def _correo(cls, v: str):
        if not _CORREO.match(v):
            raise ValueError("El correo electrónico no tiene un formato válido")
        return v.lower()

    @field_validator("telefono")
    @classmethod
    def _telefono(cls, v: str):
        limpio = re.sub(r"[\s-]", "", v)
        if not re.match(r"^\+?\d{7,15}$", limpio):
            raise ValueError("El teléfono debe tener de 7 a 15 dígitos (opcionalmente con +)")
        return limpio


class ValidarBiometriaIn(DocumentoBase):
    tipo_documento: Literal["DNI"]  # la biometría solo existe para DNI
    tipo_biometria: Literal["FACIAL", "HUELLA"]
    formato: Literal["ARCFACE_EMBEDDING", "ISO_19794_2_2005"]
    codificacion: Optional[Literal["base64"]] = None
    template: Union[list[float], str]

    @model_validator(mode="after")
    def _coherencia(self):
        if self.tipo_biometria == "FACIAL":
            if self.formato != FORMATO_FACIAL:
                raise ValueError(f"Para FACIAL el formato debe ser {FORMATO_FACIAL}")
            if not isinstance(self.template, list) or len(self.template) != DIM_EMBEDDING:
                raise ValueError(f"El template facial debe ser una lista de {DIM_EMBEDDING} números")
        else:
            if self.formato != FORMATO_HUELLA:
                raise ValueError(f"Para HUELLA el formato debe ser {FORMATO_HUELLA}")
            if self.codificacion != "base64":
                raise ValueError("Para HUELLA la codificación debe ser base64")
            if not isinstance(self.template, str) or not (16 <= len(self.template) <= MAX_TEMPLATE_HUELLA_B64):
                raise ValueError("El template de huella debe ser una cadena Base64 válida")
        return self
