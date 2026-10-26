"""Contratos explícitos: se rechazan campos extra para evitar cambios silenciosos."""

from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(StrictModel):
    username: str = Field(min_length=1, max_length=60)
    password: str = Field(min_length=1, max_length=200)


class Guarantee(StrictModel):
    tipo_garantia: Literal[
        "PERSONAL", "HIPOTECARIA", "VEHICULAR", "MOBILIARIA", "FONDOS"
    ]
    descripcion: str = Field(min_length=5, max_length=200)
    valor_tasacion: Decimal = Field(gt=0, max_digits=15, decimal_places=2)


class ApplicationInput(StrictModel):
    id_cliente: str = Field(min_length=1, max_length=36)
    monto_solicitado: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    moneda: str = Field(min_length=3, max_length=3)
    plazo_meses: int = Field(ge=1, le=600, strict=True)
    destino_credito: str = Field(min_length=5, max_length=120)
    fecha_base: date
    pago_doble: bool = False
    garantias: list[Guarantee] = Field(default_factory=list, max_length=10)
    fiadores: list[str] = Field(default_factory=list, max_length=5)
    revision: int | None = Field(default=None, ge=1)


class RevisionInput(StrictModel):
    revision: int = Field(ge=1)


class ResultInput(StrictModel):
    version: int = Field(ge=1)
    decision: Literal["APROBADO", "OBSERVADO", "RECHAZADO"]
    observaciones: str = Field(min_length=5, max_length=1000)


class EvaluationResult(StrictModel):
    """CR-INT-03 propuesto: la ronda pertenece a EVA, no al número de versión."""
    idSolicitud: str = Field(min_length=1, max_length=36)
    versionSolicitud: int = Field(ge=1, strict=True)
    idEvaluacion: str = Field(min_length=1, max_length=80)
    ronda: int = Field(ge=1, strict=True)
    idOperacion: str = Field(pattern=r"^[A-Za-z0-9._:-]{8,80}$")
    idCorrelacion: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,100}$")
    decision: Literal["APROBADO", "OBSERVADO", "RECHAZADO"]
    observaciones: str = Field(min_length=5, max_length=1000)


class DisableUser(StrictModel):
    motivo: str = Field(min_length=5, max_length=200)
