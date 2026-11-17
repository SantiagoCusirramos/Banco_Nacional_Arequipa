"""Cuerpos que recibe Desembolso. Son estrictos (un campo desconocido da 422) y van a COREDB con
los nombres de CONTRATO_CREDITOS.md §4; la verificación del documento, con los de
CONTRATO_CLIENTES.md."""
from __future__ import annotations

import uuid
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

NumCuenta = Field(min_length=1, max_length=20)


class _Estricta(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class IdentidadIn(_Estricta):
    """Verificación del documento en ventanilla: el operador revisó el original y a la persona."""

    tipoDocumento: str = Field(min_length=1, max_length=10)
    numeroDocumento: str = Field(min_length=1, max_length=12)
    identidadVerificada: bool
    motivo: str | None = Field(default=None, max_length=60)

    def a_coredb(self) -> dict:
        return {"tipo_documento": self.tipoDocumento.upper(), "numero_documento": self.numeroDocumento.upper(),
                "identidad_verificada": self.identidadVerificada, "motivo": self.motivo}


class OrdenIn(_Estricta):
    idEvaluacion: uuid.UUID = Field(description="La aprobación: `idEvaluacion` de `GET /api/v1/aprobaciones`.")
    numCuenta: str = NumCuenta
    canal: Literal["VEN", "HB"] = "VEN"
    idAgencia: str | None = Field(default=None, min_length=1, max_length=10)

    def a_coredb(self) -> dict:
        cuerpo = {"idEvaluacion": str(self.idEvaluacion), "numCuenta": self.numCuenta, "canal": self.canal}
        if self.idAgencia:
            cuerpo["idAgencia"] = self.idAgencia
        return cuerpo


class CuentaIn(_Estricta):
    numCuenta: str = NumCuenta


class ValidacionIn(_Estricta):
    """En IDENTIDAD aprobada, `referenciaEvidencia` es el `idValidacion` de `POST /api/v1/identidad`,
    de hoy y del titular. La validación CUENTA la registra COREDB al elegir la cuenta."""

    tipo: Literal["IDENTIDAD", "AUTORIZACION", "ANTIFRAUDE"]
    resultado: Literal["APROBADA", "RECHAZADA"]
    referenciaEvidencia: str = Field(min_length=1, max_length=100)
    detalle: str | None = Field(default=None, max_length=255)
    venceEn: AwareDatetime | None = None

    def a_coredb(self) -> dict:
        cuerpo = self.model_dump(exclude_none=True)
        if self.venceEn:
            cuerpo["venceEn"] = self.venceEn.isoformat()
        return cuerpo


class RechazoIn(_Estricta):
    motivo: str = Field(min_length=1, max_length=255)
