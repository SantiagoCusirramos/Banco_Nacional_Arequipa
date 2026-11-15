"""Contratos de entrada.

CR-INT-02 sigue el sobre que arma SOL (`SOL.integrations.evaluation_envelope`, versión
CR-INT-02-PROPUESTA-v2): se validan los campos que Evaluación usa y se guarda el sobre completo
tal como llegó. Las peticiones del personal y de Desembolso rechazan campos desconocidos.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

PATRON_OPERACION = r"^[A-Za-z0-9._:-]{8,80}$"
PATRON_CORRELACION = r"^[A-Za-z0-9._:-]{1,100}$"


class _DeSol(BaseModel):
    # Lo que SOL agregue en el futuro se conserva en el sobre guardado, pero no se valida aquí.
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class ClienteSol(_DeSol):
    id_cliente: str = Field(min_length=1, max_length=36)
    cod_tipo_documento: str = Field(default="DNI", min_length=1, max_length=10)
    numero_documento: str = Field(min_length=1, max_length=20)
    nombres: str = Field(min_length=1, max_length=100)
    apellido_paterno: str = Field(min_length=1, max_length=100)
    apellido_materno: str | None = Field(default=None, max_length=100)


class CondicionesSol(_DeSol):
    id_cliente: str = Field(min_length=1, max_length=36)
    monto_solicitado: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    moneda: Literal["PEN", "USD"]
    plazo_meses: int = Field(ge=1, le=600)
    destino_credito: str | None = Field(default=None, max_length=120)
    fecha_base: date


class PoliticaSol(_DeSol):
    version: str = Field(min_length=1, max_length=40)
    producto_nombre: str = Field(min_length=1, max_length=100)
    tea: Decimal = Field(ge=0, le=5)


class CuotaSol(_DeSol):
    numero_cuota: int = Field(ge=1)
    fecha_vencimiento: date
    saldo_inicial: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    amortizacion: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    interes: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    cuota_total: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    saldo_final: Decimal = Field(ge=0, max_digits=15, decimal_places=2)


class CalendarioSol(_DeSol):
    estado: str = Field(min_length=1, max_length=20)
    cuotas: list[CuotaSol] = Field(min_length=1, max_length=600)
    cuota_referencial: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    intereses_totales: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    total_pagar: Decimal = Field(gt=0, max_digits=15, decimal_places=2)


class ExpedienteSol(_DeSol):
    cliente: ClienteSol
    condiciones: CondicionesSol
    politica: PoliticaSol
    calendario: CalendarioSol


class SobreExpediente(_DeSol):
    """CR-INT-02: lo que SOL envía al pulsar «Guardar y enviar»."""

    versionContrato: str = Field(min_length=1, max_length=40)
    idSolicitud: str = Field(min_length=1, max_length=36)
    versionSolicitud: int = Field(ge=1, strict=True)
    idOperacion: str = Field(pattern=PATRON_OPERACION)
    idCorrelacion: str = Field(pattern=PATRON_CORRELACION)
    expediente: ExpedienteSol
    simulado: bool = False
    actorEnvio: str | None = Field(default=None, max_length=60)


class _Estricta(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SituacionIn(_Estricta):
    """Situación financiera del cliente que registra el analista; con ella corre la regla."""

    ingresoMensual: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    deudaMensual: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    riesgo: Literal["BUENO", "REGULAR", "ALTO"]
    verificada: bool
    version: int = Field(ge=1)


class DecisionIn(_Estricta):
    """Decisión del analista sobre un caso EN_REVISION. OBSERVADO pide a SOL que corrija."""

    decision: Literal["APROBADO", "OBSERVADO", "RECHAZADO"]
    observaciones: str = Field(min_length=10, max_length=1000)
    version: int = Field(ge=1)


class RevocacionIn(_Estricta):
    motivo: str = Field(min_length=10, max_length=500)
    version: int = Field(ge=1)


class DesembolsoIn(_Estricta):
    """CR-INT-04: Desembolso informa que la aprobación se usó en una orden confirmada."""

    version: int = Field(ge=1)
    codigoOrden: str = Field(min_length=1, max_length=30, pattern=r"^[A-Za-z0-9._:-]+$")
    fechaDesembolso: AwareDatetime
