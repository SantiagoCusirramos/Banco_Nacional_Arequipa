"""Cuerpos de las peticiones y respuestas de CAPTACION."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TipoDocumento = Literal["DNI", "CE", "PTP", "PASAPORTE"]
Canal = Literal["AGENCIA", "WEB", "MOVIL", "AGENTE", "CAMPANA"]
TipoConsentimiento = Literal["TRATAMIENTO_DATOS", "CONSULTA_BUROS", "TERMINOS", "BIOMETRIA"]
TipoValidacion = Literal["RENIEC", "LISTAS_NEGRAS", "PEP", "BIOMETRIA"]
Central = Literal["SBS", "INFOCORP", "SENTINEL", "EQUIFAX"]
Calificacion = Literal["NORMAL", "CPP", "DEFICIENTE", "DUDOSO", "PERDIDA"]


class _Peticion(BaseModel):
    # Como COREDB: un campo desconocido se rechaza.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ── Solicitante y caso ──────────────────────────────────────────────────────
class SolicitantesBuscar(_Peticion):
    """La búsqueda va en el cuerpo: un documento en la consulta quedaría en los registros de acceso."""
    documento: str | None = Field(default=None, max_length=12)
    limite: int = Field(default=50, ge=1, le=200)


class ReferenciasBuscar(_Peticion):
    """CR-INT-01: búsqueda de SOL. `search` puede ser un documento: va en el cuerpo, nunca en la consulta."""
    search: str = Field(default="", max_length=100)
    limit: int = Field(default=50, ge=1, le=50)


class SolicitanteRegistrar(_Peticion):
    tipo_documento: TipoDocumento
    numero_documento: str = Field(min_length=6, max_length=12)
    nombres: str = Field(min_length=1, max_length=100)
    apellido_paterno: str = Field(min_length=1, max_length=100)
    apellido_materno: str | None = Field(default=None, max_length=100)
    celular: str = Field(pattern=r"^9\d{8}$", description="Nueve dígitos, empieza con 9. Sin +51.")
    correo: str = Field(max_length=150, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    @field_validator("numero_documento")
    @classmethod
    def _mayusculas(cls, valor: str) -> str:
        return valor.upper()

    @field_validator("correo")
    @classmethod
    def _minusculas(cls, valor: str) -> str:
        return valor.lower()

    @field_validator("apellido_materno")
    @classmethod
    def _vacio(cls, valor: str | None) -> str | None:
        return valor or None


class SolicitanteVista(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_solicitante: str
    tipo_documento: str
    numero_documento: str
    nombres: str
    apellido_paterno: str
    apellido_materno: str | None
    celular: str
    correo: str
    cod_cliente: str | None
    creado_en: datetime


class CasoAbrir(_Peticion):
    id_solicitante: str = Field(min_length=36, max_length=36)
    canal: Canal
    id_agencia: str | None = Field(default=None, max_length=10, examples=["AQP01"])
    producto_interes: str | None = Field(default=None, max_length=60, examples=["Crédito personal"])


class CasoVista(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_caso: str
    id_solicitante: str
    canal: str
    id_agencia: str | None
    producto_interes: str | None
    estado: str
    observacion: str | None
    motivo_cierre: str | None
    cod_cliente: str | None
    cliente_nuevo: bool | None
    id_verificacion_captacion: str | None
    fecha_verificacion: date | None
    vigente_hasta: date | None
    creado_por: str
    creado_en: datetime
    cerrado_en: datetime | None


class CasoEstado(_Peticion):
    accion: Literal["OBSERVAR", "LEVANTAR_OBSERVACION", "RECHAZAR", "REVOCAR"]
    motivo: str = Field(min_length=3, max_length=255)


# ── Consentimientos, OTP, validaciones ──────────────────────────────────────
class ConsentimientoItem(_Peticion):
    tipo: TipoConsentimiento
    aceptado: bool
    medio: Literal["DIGITAL", "FISICO", "BIOMETRICO"] = "DIGITAL"


class Consentimientos(_Peticion):
    consentimientos: list[ConsentimientoItem] = Field(min_length=1, max_length=4)


class ConsentimientoVista(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    tipo: str
    aceptado: bool
    medio: str
    version: str | None
    registrado_por: str
    fecha: datetime


class OtpEnviar(_Peticion):
    canal: Literal["SMS", "EMAIL"] = "SMS"


class OtpVerificar(_Peticion):
    canal: Literal["SMS", "EMAIL"] = "SMS"
    codigo: str = Field(pattern=r"^\d{6}$")


class ValidacionesEjecutar(_Peticion):
    tipos: list[TipoValidacion] = Field(default=["RENIEC", "LISTAS_NEGRAS", "PEP"], min_length=1)


class ValidacionManual(_Peticion):
    tipo: TipoValidacion
    resultado: Literal["APROBADO", "OBSERVADO", "RECHAZADO"]
    detalle: str = Field(min_length=3, max_length=200)


class ValidacionVista(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    tipo: str
    resultado: str
    proveedor: str
    detalle: str | None
    registrado_por: str
    fecha: datetime


# ── Centrales y perfil ──────────────────────────────────────────────────────
class ReporteManual(_Peticion):
    calificacion: Calificacion
    deuda_total: Decimal = Field(default=Decimal("0"), ge=0, max_digits=15, decimal_places=2)
    entidades: int = Field(default=0, ge=0, le=99)
    dias_mora: int = Field(default=0, ge=0, le=9999)


class ConsultaPedir(_Peticion):
    central: Central = "SBS"
    reporte: ReporteManual | None = Field(
        default=None, description="Solo si la consulta se hizo fuera del sistema; si no, responde el simulador.")


class ConsultaVista(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    central: str
    calificacion: str
    deuda_total: Decimal
    entidades: int
    dias_mora: int
    fuente: str
    fecha: datetime


class PerfilVista(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    puntaje: int
    calificacion: str
    observacion: str | None
    fecha: datetime
