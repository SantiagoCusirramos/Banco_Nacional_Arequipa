"""Contratos explícitos: se rechazan campos extra para evitar cambios silenciosos."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Any, Literal
from pydantic import BaseModel, ConfigDict, Field
from .policy import Policy


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


# Mismo límite del identificador de referencia; no presupone UUID institucional.
ReferenceIdentifier = Annotated[str, Field(min_length=1, max_length=36)]


class ApplicationInput(StrictModel):
    id_cliente: str = Field(min_length=1, max_length=36)
    monto_solicitado: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    moneda: str = Field(min_length=3, max_length=3)
    plazo_meses: int = Field(ge=1, le=600, strict=True)
    destino_credito: str = Field(min_length=5, max_length=120)
    fecha_base: date
    pago_doble: bool = False
    garantias: list[Guarantee] = Field(default_factory=list, max_length=10)
    fiadores: list[ReferenceIdentifier] = Field(default_factory=list, max_length=5)
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


# Respuestas AS-IS: se preservan claves y nulos; los opcionales ausentes no se
# añaden al serializar (response_model_exclude_unset en las rutas).
class UserResponse(BaseModel):
    username: str
    nombre: str
    rol: str


class LoginResponse(BaseModel):
    token: str
    usuario: UserResponse


class OkResponse(BaseModel):
    ok: bool


class ClientResponse(BaseModel):
    id_cliente: str
    numero_documento: str
    nombres: str
    apellido_paterno: str
    apellido_materno: str = ""
    estado_cliente: str
    id_caso: str
    id_verificacion: str
    fecha_verificacion: str
    vigente_hasta: str
    estado_habilitante: str
    version_contrato: str
    cod_tipo_documento: str | None = None
    simulado: bool | None = None


class PolicyResponse(Policy):
    integracion: str


class GuaranteeResponse(BaseModel):
    tipo_garantia: str
    descripcion: str
    valor_tasacion: str


class ConditionsResponse(BaseModel):
    id_cliente: str
    monto_solicitado: str
    moneda: str
    plazo_meses: int
    destino_credito: str
    fecha_base: str
    pago_doble: bool
    garantias: list[GuaranteeResponse]
    id_producto_credito: str


class GuarantorResponse(BaseModel):
    id_cliente: str
    identidad: ClientResponse
    validacion: str


class InstallmentResponse(BaseModel):
    numero_cuota: int
    fecha_vencimiento: str
    saldo_inicial: str
    amortizacion: str
    interes: str
    cuota_total: str
    saldo_final: str


class CalendarResponse(BaseModel):
    estado: str
    cuotas: list[InstallmentResponse]
    cuota_referencial: str
    intereses_totales: str
    total_pagar: str


class SnapshotResponse(BaseModel):
    cliente: ClientResponse
    condiciones: ConditionsResponse
    fiadores: list[GuarantorResponse]
    politica: Policy
    calendario: CalendarResponse


class SummaryResponse(BaseModel):
    id: str
    codigo: str
    estado: str
    version: int
    revision: int
    cliente_nombre: str
    documento: str
    monto: str
    moneda: str
    plazo: int
    actualizado: str


class VersionResponse(BaseModel):
    numero: int
    congelada: bool
    expediente: SnapshotResponse


class EventResponse(BaseModel):
    accion: str
    actor: str
    version: int
    estado_anterior: str | None
    estado_nuevo: str
    fecha: str
    correlacion: str


class OutcomeResponse(BaseModel):
    version: int
    decision: str
    observaciones: str
    fecha: str


class DeliveryResponse(BaseModel):
    version: int
    id_operacion: str
    acuse: str
    estado_transporte: str
    id_evaluacion: str | None
    ronda: int | None
    fecha: str


class DetailResponse(SummaryResponse):
    versiones: list[VersionResponse]
    eventos: list[EventResponse]
    resultados: list[OutcomeResponse]
    envios: list[DeliveryResponse]
    pendiente_envio: bool | None = None
    idOperacion: str | None = None
    reintento_reconocido: bool | None = None


class ApplicationPageResponse(BaseModel):
    items: list[SummaryResponse]
    total: int
    limit: int
    offset: int
    estados: dict[str, int]


class EvaluationReceiptResponse(BaseModel):
    recibido: bool
    idOperacion: str
    estado: str | None = None
    reintento_reconocido: bool | None = None


class DisableUserResponse(BaseModel):
    usuario: str
    activo: bool
    sesiones_revocadas: int


class AuditCountResponse(BaseModel):
    estado: str
    cantidad: int


class PendingResponse(BaseModel):
    envios: list[str]
    auditoria: list[AuditCountResponse]


class MetricResponse(BaseModel):
    operacion: str
    muestras: int
    p95_ms: float
    errores_5xx_acumulados: int


class MetricsResponse(BaseModel):
    alcance: str
    unidad: str
    operaciones: list[MetricResponse]


class HealthResponse(BaseModel):
    status: str
    modulo: str
    integracion: str


class ReadyResponse(BaseModel):
    status: str
    base: str


class ValidationIssue(BaseModel):
    loc: list[str | int]
    msg: str
    type: str


class ErrorResponse(BaseModel):
    detail: str | dict[str, Any] | list[ValidationIssue]


def http_errors(*codes):
    return {code: {"model": ErrorResponse} for code in codes}
