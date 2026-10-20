"""Routers de movimientos — REGISTRAR_MOVIMIENTO (depósito/retiro y
transferencia)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from CORE.dependencies import db_session
from CORE.schemas.movimientos import (
    MovimientoRegistrar,
    MovimientoRespuesta,
    TransferenciaRegistrar,
    TransferenciaRespuesta,
)
from CORE.services import movimientos as svc

router = APIRouter(prefix="/movimientos", tags=["Movimientos"])


def _a_respuesta(res) -> MovimientoRespuesta:
    return MovimientoRespuesta(
        id_transaccion=res.id_transaccion,
        uuid_transaccion=res.uuid_transaccion,
        num_cuenta=res.num_cuenta,
        tipo_operacion=res.tipo_operacion,
        tipo_movimiento=res.tipo_movimiento,
        monto=res.monto,
        moneda=res.moneda,
        monto_moneda_base=res.monto_moneda_base,
        saldo_posterior=res.saldo_posterior,
        id_asiento=res.id_asiento,
        num_cuenta_contraparte=res.num_cuenta_contraparte,
        idempotency_key=res.idempotency_key,
        replay=res.replay,
    )


@router.post("", response_model=MovimientoRespuesta, status_code=status.HTTP_201_CREATED)
def registrar_movimiento(payload: MovimientoRegistrar, db: Session = Depends(db_session)):
    res = svc.registrar_movimiento(
        db,
        tipo_operacion=payload.tipo_operacion,
        num_cuenta=payload.num_cuenta,
        monto=payload.monto,
        moneda=payload.moneda,
        id_canal=payload.id_canal,
        id_terminal=payload.id_terminal,
        num_cuenta_contraparte=payload.num_cuenta_contraparte,
        idempotency_key=payload.idempotency_key,
        actor=payload.actor,
        correlation_id=payload.correlation_id,
        comision=payload.comision,
        itf=payload.itf,
        retencion=payload.retencion,
    )
    return _a_respuesta(res)


@router.post(
    "/transferencias",
    response_model=TransferenciaRespuesta,
    status_code=status.HTTP_201_CREATED,
)
def transferir(payload: TransferenciaRegistrar, db: Session = Depends(db_session)):
    res = svc.transferir_cuentas(
        db,
        num_cuenta_origen=payload.num_cuenta_origen,
        num_cuenta_destino=payload.num_cuenta_destino,
        monto=payload.monto,
        moneda=payload.moneda,
        id_canal=payload.id_canal,
        id_terminal=payload.id_terminal,
        idempotency_key=payload.idempotency_key,
        actor=payload.actor,
        correlation_id=payload.correlation_id,
    )
    return TransferenciaRespuesta(
        origen=_a_respuesta(res.origen),
        destino=_a_respuesta(res.destino),
        id_asiento=res.id_asiento,
        replay=res.replay,
    )
