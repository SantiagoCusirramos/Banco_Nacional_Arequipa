"""Schemas de clientes (VER/CREAR/MODIFICAR_CLIENTE)."""

from datetime import date

from pydantic import EmailStr, Field

from CORE.schemas.common import CoreModel


class ClienteCrear(CoreModel):
    cod_tipo_documento: str = Field(min_length=1, max_length=10)
    numero_documento: str = Field(min_length=1, max_length=20)
    nombres: str = Field(min_length=1, max_length=100)
    apellido_paterno: str = Field(min_length=1, max_length=100)
    apellido_materno: str | None = Field(default=None, max_length=100)
    fecha_nacimiento: date | None = None
    numero_celular: str = Field(min_length=5, max_length=15)
    correo_electronico: EmailStr | None = None
    actor: str = "sistema"
    correlation_id: str | None = None


class ClienteModificar(CoreModel):
    nombres: str | None = Field(default=None, min_length=1, max_length=100)
    apellido_paterno: str | None = Field(default=None, min_length=1, max_length=100)
    apellido_materno: str | None = Field(default=None, max_length=100)
    numero_celular: str | None = Field(default=None, min_length=5, max_length=15)
    correo_electronico: EmailStr | None = None
    estado_cliente: str | None = Field(default=None, max_length=18)
    actor: str = "sistema"
    correlation_id: str | None = None


class ClienteRespuesta(CoreModel):
    id_cliente: str
    cod_tipo_documento: str
    numero_documento: str
    nombres: str
    apellido_paterno: str
    apellido_materno: str | None
    fecha_nacimiento: date | None
    numero_celular: str
    correo_electronico: str | None
    estado_cliente: str
    fecha_registro: str | None = None


class ClienteAltaRespuesta(CoreModel):
    cliente: ClienteRespuesta
    duplicado: bool
