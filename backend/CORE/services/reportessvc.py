"""GENERAR_REPORTES — RF-COR-20 a RF-COR-22 (cuadre contable, movimientos
por periodo y cliente, historial de productos y estados)."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from CORE.models import (
    AsientoContable,
    AsientoDetalle,
    AuditoriaEvento,
    CtaTransaccion,
    SolHistorialEstado,
    SolSolicitud,
    TarHistorialEstado,
    TarTarjeta,
)
from CORE.services import contabilidad
from CORE.utils.money import D

CERO = Decimal("0.00")


def reporte_cuadre_contable(db: Session, fecha: date | None = None) -> dict:
    """RF-COR-20: cuadre de partida doble del día (debe = haber)."""
    return contabilidad.cuadre_del_dia(db, fecha or date.today())


def reporte_asientos(
    db: Session, *, desde: date, hasta: date, estado: str | None = None,
    limite: int = 200, offset: int = 0,
) -> list[dict]:
    desde_dt = datetime.combine(desde, datetime.min.time())
    hasta_dt = datetime.combine(hasta, datetime.max.time())
    q = (
        db.query(AsientoContable)
        .filter(AsientoContable.fecha >= desde_dt, AsientoContable.fecha <= hasta_dt)
    )
    if estado:
        q = q.filter(AsientoContable.estado == estado)
    asientos = q.order_by(AsientoContable.fecha).offset(offset).limit(limite).all()

    resultado = []
    for asiento in asientos:
        detalles = (
            db.query(AsientoDetalle)
            .filter(AsientoDetalle.id_asiento == asiento.id_asiento)
            .all()
        )
        resultado.append(
            {
                "id_asiento": asiento.id_asiento,
                "fecha": asiento.fecha,
                "glosa": asiento.glosa,
                "estado": asiento.estado,
                "total_debe": D(sum((d.debe for d in detalles), start=CERO)),
                "total_haber": D(sum((d.haber for d in detalles), start=CERO)),
                "lineas": [
                    {
                        "cod_cuenta_contable": d.cod_cuenta_contable,
                        "debe": d.debe,
                        "haber": d.haber,
                        "moneda": d.moneda,
                        "tipo_cambio": d.tipo_cambio,
                        "importe_moneda_base": d.importe_moneda_base,
                    }
                    for d in detalles
                ],
            }
        )
    return resultado


def reporte_movimientos(
    db: Session, *, num_cuenta: str | None = None, desde: date | None = None,
    hasta: date | None = None, limite: int = 200, offset: int = 0,
) -> list[dict]:
    """RF-COR-21: movimientos de una cuenta o de todo el banco."""
    q = db.query(CtaTransaccion)
    if num_cuenta:
        q = q.filter(CtaTransaccion.num_cuenta == num_cuenta)
    if desde:
        q = q.filter(CtaTransaccion.fecha_hora >= datetime.combine(desde, datetime.min.time()))
    if hasta:
        q = q.filter(CtaTransaccion.fecha_hora <= datetime.combine(hasta, datetime.max.time()))
    movimientos = (
        q.order_by(CtaTransaccion.fecha_hora.desc()).offset(offset).limit(limite).all()
    )
    return [
        {
            "id_transaccion": tx.id_transaccion,
            "num_cuenta": tx.num_cuenta,
            "tipo_operacion": tx.tipo_operacion,
            "tipo_movimiento": tx.tipo_movimiento,
            "monto": tx.monto,
            "moneda": tx.moneda,
            "comision": tx.comision,
            "itf": tx.itf,
            "retencion": tx.retencion,
            "saldo_posterior": tx.saldo_posterior,
            "id_canal": tx.id_canal,
            "num_cuenta_contraparte": tx.num_cuenta_contraparte,
            "idempotency_key": tx.idempotency_key,
            "fecha_hora": tx.fecha_hora,
        }
        for tx in movimientos
    ]


def reporte_historial_cliente(
    db: Session, *, id_cliente: str,
) -> dict:
    """RF-COR-22: historial completo de solicitudes y tarjetas del cliente."""
    solicitudes = (
        db.query(SolSolicitud)
        .filter(SolSolicitud.id_cliente == id_cliente)
        .order_by(SolSolicitud.fecha_registro.desc())
        .all()
    )
    tarjetas = (
        db.query(TarTarjeta)
        .filter(TarTarjeta.id_cliente == id_cliente)
        .order_by(TarTarjeta.fecha_creacion.desc())
        .all()
    )
    return {
        "id_cliente": id_cliente,
        "solicitudes": [
            {
                "id_solicitud": s.id_solicitud,
                "monto_solicitado": s.monto_solicitado,
                "moneda": s.moneda,
                "plazo_meses": s.plazo_meses,
                "estado_solicitud": s.estado_solicitud,
                "fecha_registro": s.fecha_registro,
                "historial": [
                    {
                        "estado_anterior": h.estado_anterior,
                        "estado_nuevo": h.estado_nuevo,
                        "motivo": h.motivo,
                        "fecha_hora": h.fecha_hora,
                    }
                    for h in (
                        db.query(SolHistorialEstado)
                        .filter(SolHistorialEstado.id_solicitud == s.id_solicitud)
                        .order_by(SolHistorialEstado.fecha_hora)
                        .all()
                    )
                ],
            }
            for s in solicitudes
        ],
        "tarjetas": [
            {
                "id_tarjeta": t.id_tarjeta,
                "bin": t.bin,
                "ultimos4": t.ultimos4,
                "tipo_tarjeta": t.tipo_tarjeta,
                "estado": t.estado,
                "fecha_emision": t.fecha_emision,
                "historial": [
                    {
                        "estado_anterior": h.estado_anterior,
                        "estado_nuevo": h.estado_nuevo,
                        "motivo": h.motivo,
                        "fecha_hora": h.fecha_hora,
                    }
                    for h in (
                        db.query(TarHistorialEstado)
                        .filter(TarHistorialEstado.id_tarjeta == t.id_tarjeta)
                        .order_by(TarHistorialEstado.fecha_hora)
                        .all()
                    )
                ],
            }
            for t in tarjetas
        ],
    }


def reporte_auditoria(
    db: Session, *, desde: date | None = None, hasta: date | None = None,
    modulo: str | None = None, accion: str | None = None,
    actor: str | None = None, correlation_id: str | None = None,
    limite: int = 200, offset: int = 0,
) -> list[dict]:
    """RF-COR-19: consulta del log de auditoría (solo lectura)."""
    q = db.query(AuditoriaEvento)
    if desde:
        q = q.filter(AuditoriaEvento.fecha_hora >= datetime.combine(desde, datetime.min.time()))
    if hasta:
        q = q.filter(AuditoriaEvento.fecha_hora <= datetime.combine(hasta, datetime.max.time()))
    if modulo:
        q = q.filter(AuditoriaEvento.modulo == modulo)
    if accion:
        q = q.filter(AuditoriaEvento.accion == accion)
    if actor:
        q = q.filter(AuditoriaEvento.actor == actor)
    if correlation_id:
        q = q.filter(AuditoriaEvento.correlation_id == correlation_id)
    eventos = q.order_by(AuditoriaEvento.fecha_hora.desc()).offset(offset).limit(limite).all()
    return [
        {
            "id_evento": e.id_evento,
            "modulo": e.modulo,
            "entidad": e.entidad,
            "id_entidad": e.id_entidad,
            "accion": e.accion,
            "actor": e.actor,
            "detalle": e.detalle,
            "correlation_id": e.correlation_id,
            "fecha_hora": e.fecha_hora,
        }
        for e in eventos
    ]
