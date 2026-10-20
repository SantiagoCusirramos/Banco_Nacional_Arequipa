"""Routers del ciclo de crédito — CREAR_SOLICITUD_CREDITO,
EVALUAR_CREDITO, APROBAR_CREDITO, VER_CREDITO, REGISTRAR_PAGO,
CONSULTAR_DEUDA."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from CORE.dependencies import db_session
from CORE.schemas.creditos import (
    DecisionPedir,
    DeudaRespuesta,
    EvaluacionPedir,
    EvaluacionRespuesta,
    PagoRegistrar,
    PagoRespuesta,
    SolicitudCrear,
    SolicitudRespuesta,
)
from CORE.services import creditossvc

router = APIRouter(prefix="/creditos", tags=["Creditos"])


@router.post(
    "/solicitudes",
    response_model=SolicitudRespuesta,
    status_code=status.HTTP_201_CREATED,
)
def crear_solicitud(payload: SolicitudCrear, db: Session = Depends(db_session)):
    solicitud = creditossvc.crear_solicitud(
        db,
        id_cliente=payload.id_cliente,
        id_producto_credito=payload.id_producto_credito,
        monto_solicitado=payload.monto_solicitado,
        moneda=payload.moneda,
        plazo_meses=payload.plazo_meses,
        destino_credito=payload.destino_credito,
        id_asesor=payload.id_asesor,
        id_agencia=payload.id_agencia,
        id_caso=payload.id_caso,
        fiadores=[f.model_dump() for f in payload.fiadores],
        garantias=[g.model_dump() for g in payload.garantias],
        actor=payload.actor,
        correlation_id=payload.correlation_id,
    )
    return SolicitudRespuesta(**creditossvc.ver_credito(db, solicitud.id_solicitud))


@router.get("/solicitudes/{id_solicitud}", response_model=SolicitudRespuesta)
def ver_solicitud(id_solicitud: str, db: Session = Depends(db_session)):
    return SolicitudRespuesta(**creditossvc.ver_credito(db, id_solicitud))


@router.post(
    "/solicitudes/{id_solicitud}/evaluar",
    response_model=EvaluacionRespuesta,
    status_code=status.HTTP_201_CREATED,
)
def evaluar_solicitud(
    id_solicitud: str, payload: EvaluacionPedir, db: Session = Depends(db_session)
):
    situacion = payload.situacion.model_dump() if payload.situacion else None
    evaluacion = creditossvc.evaluar_credito(
        db,
        id_solicitud=id_solicitud,
        situacion=situacion,
        dias_mayor_mora=payload.dias_mayor_mora,
        actor=payload.actor,
        correlation_id=payload.correlation_id,
    )
    return EvaluacionRespuesta(
        id_evaluacion=evaluacion.id_evaluacion,
        id_solicitud=evaluacion.id_solicitud,
        puntaje=evaluacion.puntaje,
        resultado=evaluacion.resultado,
        monto_maximo_sugerido=evaluacion.monto_maximo_sugerido,
        nivel_riesgo=evaluacion.nivel_riesgo,
        detalle_reglas=evaluacion.detalle_reglas,
        fecha_evaluacion=evaluacion.fecha_evaluacion,
    )


@router.post(
    "/solicitudes/{id_solicitud}/decision",
    response_model=SolicitudRespuesta,
)
def decidir_solicitud(
    id_solicitud: str, payload: DecisionPedir, db: Session = Depends(db_session)
):
    solicitud, _ = creditossvc.aprobar_credito(
        db,
        id_solicitud=id_solicitud,
        decision=payload.decision,
        id_analista=payload.id_analista,
        monto_aprobado=payload.monto_aprobado,
        plazo_aprobado=payload.plazo_aprobado,
        observacion=payload.observacion,
        actor=payload.actor,
        correlation_id=payload.correlation_id,
    )
    return SolicitudRespuesta(**creditossvc.ver_credito(db, solicitud.id_solicitud))


@router.get("/deuda", response_model=list[DeudaRespuesta])
def consultar_deuda(
    id_credito: str | None = Query(default=None),
    id_cliente: str | None = Query(default=None),
    db: Session = Depends(db_session),
):
    deudas = creditossvc.consultar_deuda(db, id_credito=id_credito, id_cliente=id_cliente)
    return [DeudaRespuesta(**d) for d in deudas]


@router.post("/pagos", response_model=PagoRespuesta, status_code=status.HTTP_201_CREATED)
def registrar_pago(payload: PagoRegistrar, db: Session = Depends(db_session)):
    res = creditossvc.registrar_pago(
        db,
        id_credito=payload.id_credito,
        monto=payload.monto,
        id_canal_pago=payload.id_canal_pago,
        num_cuenta=payload.num_cuenta,
        num_operacion=payload.num_operacion,
        id_cobrador=payload.id_cobrador,
        actor=payload.actor,
        correlation_id=payload.correlation_id,
    )
    return PagoRespuesta(**res)
