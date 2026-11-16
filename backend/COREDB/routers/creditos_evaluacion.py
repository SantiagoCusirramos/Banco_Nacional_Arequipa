"""Créditos: expediente de SOL, evaluación, decisión del analista y aprobaciones.

Ver CONTRATO_CREDITOS.md §3. Los nombres de los campos van en camelCase, como en el
contrato con SOL y los módulos de créditos.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel
from sqlalchemy.orm import Session

from COREDB.auth import Actor, requiere_permiso
from COREDB.correlacion import correlacion
from COREDB.database import db_session
from COREDB.errores import ErrorCoreDb
from COREDB.services import creditos

router = APIRouter(prefix="/coredb/creditos", tags=["créditos: evaluación"])

ERRORES_COMUNES = {401: {"description": "Sin token o token no válido"},
                   403: {"description": "PERMISO_DENEGADO"}}
Importe = Annotated[Decimal, Field(ge=0, max_digits=15, decimal_places=2)]
CodCliente = Annotated[str, Field(min_length=1, max_length=12, pattern=r"^[A-Za-z0-9]+$")]
EstadoSolicitud = Literal["REGISTRADA", "EN_EVALUACION", "APROBADA", "RECHAZADA", "DESEMBOLSADA"]


class _Respuesta(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class _Peticion(BaseModel):
    # camelCase obligatorio; un campo desconocido (también su nombre en snake_case) se rechaza.
    model_config = ConfigDict(alias_generator=to_camel, extra="forbid", str_strip_whitespace=True)


# ── Expediente ──────────────────────────────────────────────────────────────


class CuotaExpediente(_Peticion):
    numero_cuota: int = Field(ge=1, le=600)
    fecha_vencimiento: date
    saldo_inicial: Importe
    amortizacion: Importe
    interes: Importe
    cuota_total: Importe
    saldo_final: Importe


class CalendarioExpediente(_Peticion):
    metodo: str = Field(min_length=1, max_length=20, description="FRANCES, ALEMAN o AMERICANO.")
    tasa: Decimal = Field(ge=0, max_digits=7, decimal_places=4, description="Fracción: 0.2200 es 22 %.")
    cuotas: list[CuotaExpediente] = Field(min_length=1, max_length=600)

    @field_validator("metodo")
    @classmethod
    def _mayusculas(cls, valor: str) -> str:
        return valor.upper()


class ExpedienteRegistrar(_Peticion):
    id_solicitud: uuid.UUID
    version_solicitud: int = Field(ge=1, le=32767)
    cod_cliente: CodCliente
    monto_solicitado: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    moneda: str = Field(pattern=r"^[A-Z]{3}$")
    plazo_meses: int = Field(ge=1, le=600)
    condicion_pago_doble: bool = False
    destino: str | None = Field(default=None, max_length=255,
                                description="Forma parte de la huella del expediente; no se guarda.")
    calendario: CalendarioExpediente


class AcuseSolicitud(_Respuesta):
    id_solicitud: uuid.UUID
    version_solicitud: int
    ronda: int
    id_evaluacion: uuid.UUID = Field(description="Id determinista de la evaluación de esta ronda.")
    estado: str


@router.post("/solicitudes", response_model=AcuseSolicitud, status_code=status.HTTP_201_CREATED,
             responses={**ERRORES_COMUNES, 200: {"description": "El mismo expediente ya se había recibido"},
                        409: {"description": "IDEMPOTENCIA_CONFLICTO"},
                        422: {"description": "CLIENTE_NO_HABILITADO, CALENDARIO_INVALIDO o SOLICITUD_NO_ADMITIDA"}})
def registrar_solicitud(
    datos: ExpedienteRegistrar,
    respuesta: Response,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("CREAR_SOLICITUD_CREDITO")),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """Registra una versión del expediente de SOL (CR-INT-02) con su calendario PRELIMINAR.

    Una versión nueva abre otra ronda y solo se acepta mientras la ronda vigente no esté
    evaluada. La misma versión con el mismo contenido responde 200 con el mismo acuse; con
    otro contenido, 409. El `idEvaluacion` del acuse es el que tendrá la evaluación."""
    acuse = creditos.registrar_solicitud(db, datos, correlation_id=correlation_id, actor=actor.usuario)
    if acuse.pop("repetido"):
        respuesta.status_code = status.HTTP_200_OK
    return acuse


# ── Bandeja y detalle ───────────────────────────────────────────────────────


class SolicitudResumen(_Respuesta):
    id_solicitud: uuid.UUID
    version_solicitud: int
    ronda: int | None
    cod_cliente: str
    monto_solicitado: Decimal
    moneda: str
    plazo_meses: int
    condicion_pago_doble: bool
    estado: str
    fecha_creacion: datetime
    numero_cuotas: int | None
    total_cuotas: Decimal | None
    primer_vencimiento: date | None


class CuotaRespuesta(_Respuesta):
    numero_cuota: int
    fecha_vencimiento: date
    capital: Decimal
    interes: Decimal
    otros_conceptos: Decimal
    cuota_total: Decimal
    saldo_capital: Decimal
    saldo_pendiente: Decimal
    estado_cuota: str


class CalendarioRespuesta(_Respuesta):
    id_calendario: uuid.UUID
    tipo: Literal["PRELIMINAR", "OFICIAL"]
    metodo: str
    tasa: Decimal
    cuotas: list[CuotaRespuesta]


class EvaluacionRespuesta(_Respuesta):
    id_evaluacion: uuid.UUID
    ronda: int
    fecha_evaluacion: datetime
    score: Decimal
    limite: Decimal
    regla: str
    resultado_regla: str
    ingreso_mensual: Decimal
    deuda_mensual: Decimal
    resultado_verificacion: str
    decision: str | None
    comentario: str | None
    fecha_decision: datetime | None
    id_analista: str | None
    resultado: str = Field(description="La decisión del analista si la hay; si no, el de la regla.")
    es_ultima: bool


class HistorialRespuesta(_Respuesta):
    estado: str
    fecha_hora: datetime
    actor: str
    motivo: str | None


class SolicitudDetalle(SolicitudResumen):
    calendario: CalendarioRespuesta | None
    evaluaciones: list[EvaluacionRespuesta]
    historial: list[HistorialRespuesta]


@router.get("/solicitudes", response_model=list[SolicitudResumen],
            dependencies=[Depends(requiere_permiso("VER_CREDITO"))], responses=ERRORES_COMUNES)
def bandeja(
    estado: EstadoSolicitud | None = None,
    cod_cliente: str | None = Query(default=None, alias="codCliente", min_length=1, max_length=12),
    limite: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(db_session),
):
    """Solicitudes, de la más reciente a la más antigua, sin datos personales del cliente."""
    return creditos.listar_solicitudes(db, estado=estado, cod_cliente=cod_cliente, limite=limite, offset=offset)


@router.get("/solicitudes/{id_solicitud}", response_model=SolicitudDetalle,
            dependencies=[Depends(requiere_permiso("VER_CREDITO"))],
            responses={**ERRORES_COMUNES, 404: {"description": "SOLICITUD_NO_ENCONTRADA"}})
def detalle(id_solicitud: uuid.UUID, db: Session = Depends(db_session)):
    """La solicitud con su calendario vigente (el PRELIMINAR de SOL o, ya desembolsada, el
    OFICIAL), sus evaluaciones por ronda y su historial de estados."""
    return creditos.solicitud(db, id_solicitud)


# ── Evaluación ──────────────────────────────────────────────────────────────


class EvaluacionRegistrar(_Peticion):
    version_solicitud: int = Field(ge=1, le=32767)
    ingreso_mensual: Importe
    deuda_mensual: Importe
    riesgo: Literal["BUENO", "REGULAR", "ALTO"]
    verificada: bool


class ResultadoEvaluacion(_Respuesta):
    id_evaluacion: uuid.UUID
    id_solicitud: uuid.UUID
    resultado: Literal["APROBADO", "OBSERVADO", "RECHAZADO"]
    regla: str
    score: int
    limite: Decimal
    ratio: Decimal | None = Field(description="Monto / límite; null si no hay capacidad de pago.")
    estado_solicitud: str


@router.post("/solicitudes/{id_solicitud}/evaluaciones", response_model=ResultadoEvaluacion,
             responses={**ERRORES_COMUNES, 404: {"description": "SOLICITUD_NO_ENCONTRADA"},
                        422: {"description": "SITUACION_NO_VERIFICADA, SOLICITUD_NO_ADMITIDA o "
                                             "EVALUACION_NO_ADMITIDA"}})
def evaluar(
    id_solicitud: uuid.UUID,
    datos: EvaluacionRegistrar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("EVALUAR_CREDITO")),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """Corre RN-EVA-002-P sobre la ronda vigente: COREDB calcula el score y el límite, y la
    base elige la regla con sus umbrales. APROBADO deja la solicitud APROBADA, RECHAZADO la
    deja RECHAZADA y OBSERVADO la deja EN_EVALUACION para el analista. Una ronda se evalúa una
    sola vez: si se pierde la respuesta, el resultado está en el detalle de la solicitud."""
    if not datos.verificada:
        raise ErrorCoreDb("SITUACION_NO_VERIFICADA", "La situación financiera no está verificada.")
    return creditos.evaluar(
        db, id_solicitud, version_solicitud=datos.version_solicitud, ingreso_mensual=datos.ingreso_mensual,
        deuda_mensual=datos.deuda_mensual, riesgo=datos.riesgo, correlation_id=correlation_id,
        actor=actor.usuario,
    )


class DecisionRegistrar(_Peticion):
    decision: Literal["APROBADO", "RECHAZADO"]
    comentario: str = Field(min_length=10, max_length=500)


class DecisionRegistrada(_Respuesta):
    id_evaluacion: uuid.UUID
    id_solicitud: uuid.UUID
    decision: str
    estado_solicitud: str


@router.post("/evaluaciones/{id_evaluacion}/decision", response_model=DecisionRegistrada,
             responses={**ERRORES_COMUNES, 404: {"description": "EVALUACION_NO_ENCONTRADA"},
                        422: {"description": "ANALISTA_REQUERIDO o EVALUACION_NO_ADMITIDA"}})
def decidir(
    id_evaluacion: uuid.UUID,
    datos: DecisionRegistrar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("APROBAR_CREDITO")),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """El analista decide, una sola vez, una evaluación OBSERVADO de la ronda vigente. El
    usuario del token debe estar ligado a un empleado registrado como analista."""
    return creditos.decidir(
        db, id_evaluacion, decision=datos.decision, comentario=datos.comentario, id_usuario=actor.id_usuario,
        correlation_id=correlation_id, actor=actor.usuario,
    )


class RevocacionRegistrar(_Peticion):
    motivo: str = Field(min_length=1, max_length=255)


class RevocacionRegistrada(_Respuesta):
    id_solicitud: uuid.UUID
    estado_solicitud: str


@router.post("/solicitudes/{id_solicitud}/revocacion", response_model=RevocacionRegistrada,
             responses={**ERRORES_COMUNES, 404: {"description": "SOLICITUD_NO_ENCONTRADA"},
                        422: {"description": "SOLICITUD_NO_ADMITIDA"}})
def revocar(
    id_solicitud: uuid.UUID,
    datos: RevocacionRegistrar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("APROBAR_CREDITO")),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """Revoca una aprobación sin desembolso: la solicitud queda RECHAZADA con el motivo y sus
    órdenes abiertas, RECHAZADA."""
    return creditos.revocar(db, id_solicitud, motivo=datos.motivo, correlation_id=correlation_id,
                            actor=actor.usuario)


# ── Aprobaciones y analistas ────────────────────────────────────────────────


class AprobacionRespuesta(_Respuesta):
    id_evaluacion: uuid.UUID
    id_solicitud: uuid.UUID
    cod_cliente: str
    ronda: int
    monto: Decimal
    moneda: str
    plazo_meses: int
    limite_aprobado: Decimal
    fecha_aprobacion: datetime
    vigente_hasta: datetime
    id_calendario: uuid.UUID | None = Field(description="El calendario PRELIMINAR vigente, sin cambios.")


@router.get("/aprobaciones", response_model=list[AprobacionRespuesta],
            dependencies=[Depends(requiere_permiso("VER_CREDITO"))], responses=ERRORES_COMUNES)
def aprobaciones(
    cod_cliente: str | None = Query(default=None, alias="codCliente", min_length=1, max_length=12),
    id_solicitud: uuid.UUID | None = Query(default=None, alias="idSolicitud"),
    db: Session = Depends(db_session),
):
    """Aprobaciones que todavía admiten un desembolso: la última ronda, aprobada por la regla o
    por el analista, dentro de su vigencia y sin orden confirmada. El calendario está en
    `GET /coredb/creditos/solicitudes/{idSolicitud}`."""
    return creditos.aprobaciones(db, cod_cliente=cod_cliente, id_solicitud=id_solicitud)


class AnalistaRegistrar(_Peticion):
    id_empleado: uuid.UUID


class AnalistaRegistrado(_Respuesta):
    id_analista: str


@router.post("/analistas", response_model=AnalistaRegistrado, status_code=status.HTTP_201_CREATED,
             responses={**ERRORES_COMUNES, 409: {"description": "ANALISTA_DUPLICADO"},
                        422: {"description": "EMPLEADO_NO_HABILITADO"}})
def registrar_analista(
    datos: AnalistaRegistrar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("CREAR_USUARIO")),
):
    """Registra a un empleado activo como analista de crédito. Para decidir, el usuario del
    analista debe estar ligado a ese empleado (`id_empleado` de `POST /coredb/usuarios`)."""
    return AnalistaRegistrado(id_analista=creditos.registrar_analista(db, datos.id_empleado, actor=actor.usuario))
