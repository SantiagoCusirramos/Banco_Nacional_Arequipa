"""Créditos: consulta de la deuda, pago de cuotas con débito, mora, vencimientos y conciliación.

Ver CONTRATO_CREDITOS.md §5. Pagar debita la cuenta del titular y aplica el pago a las cuotas
en una sola transacción de la base; un débito rechazado (saldo, cuenta no operativa, tope)
deja el pago RECHAZADO sin mover dinero.

Las rutas fijas (/conciliacion/pagos, /pagos/{referencia}, /vencimientos) se declaran antes
que las del crédito (/{cod_credito}…), que también coincidirían con ellas.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, Depends, Path, Query, Response, status
from pydantic import Field, PlainSerializer
from sqlalchemy.orm import Session

from COREDB.auth import Actor, requiere_permiso
from COREDB.correlacion import correlacion
from COREDB.database import db_session
from COREDB.routers.creditos_evaluacion import ERRORES_COMUNES, _Peticion, _Respuesta
from COREDB.services import creditos

router = APIRouter(prefix="/coredb/creditos", tags=["créditos: cobranza"])

EstadoCredito = Literal["AL_DIA", "EN_MORA", "CANCELADO"]
# Texto con dos decimales, aunque la base lo devuelva con otra escala (sumas, JSON).
Monto = Annotated[Decimal, PlainSerializer(lambda v: f"{v:.2f}", return_type=str, when_used="json")]
CodCredito = Annotated[str, Path(min_length=1, max_length=20)]
NumeroCuota = Annotated[int, Path(ge=1, le=600)]
NO_ENCONTRADO = {404: {"description": "CREDITO_NO_ENCONTRADO"}}


class PagoRegistrar(_Peticion):
    num_cuenta: str = Field(min_length=1, max_length=20, description="Cuenta de ahorros del titular, en la moneda "
                                                                    "del crédito.")
    monto: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    referencia: str = Field(
        min_length=1, max_length=40, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
        description="Llave del pago: la misma referencia con el mismo contenido devuelve el mismo pago.")
    canal: Literal["VEN", "HB"] = "VEN"


class MoraRegistrar(_Peticion):
    monto_calculado: Decimal = Field(ge=0, max_digits=15, decimal_places=2)


class VencimientosEjecutar(_Peticion):
    fecha: date | None = Field(default=None, description="Vence las cuotas anteriores a esta fecha; por omisión, "
                                                         "hoy (Lima). No puede ser posterior a hoy.")


class CreditoRespuesta(_Respuesta):
    cod_credito: str
    estado: str
    cod_cliente: str
    id_solicitud: uuid.UUID
    id_orden: uuid.UUID
    codigo_orden: str
    moneda: str
    monto_desembolsado: Monto
    fecha_desembolso: datetime
    numero_cuotas: int
    cuotas_pagadas: int
    cuotas_vencidas: int
    saldo_pendiente: Monto
    proximo_vencimiento: date | None = Field(description="La cuota más antigua con saldo; nulo si no queda deuda.")
    mora_vigente: Monto = Field(description="Suma del último cálculo de mora de las cuotas con saldo. No se cobra.")


class CuotaCreditoRespuesta(_Respuesta):
    numero_cuota: int
    fecha_vencimiento: date
    capital: Monto
    interes: Monto
    otros_conceptos: Monto
    cuota_total: Monto
    saldo_pendiente: Monto
    estado: str
    dias_atraso: int
    mora_vigente: Monto


class EventoCreditoRespuesta(_Respuesta):
    accion: str
    resultado: str | None
    numero_cuota: int | None
    actor: str
    correlation_id: uuid.UUID | None
    detalle: dict[str, Any] | None
    fecha_hora: datetime


class CreditoDetalle(CreditoRespuesta):
    cuotas: list[CuotaCreditoRespuesta]
    eventos: list[EventoCreditoRespuesta]


class AplicacionPago(_Respuesta):
    numero_cuota: int
    monto_aplicado: Monto


class PagoRespuesta(_Respuesta):
    id_pago: uuid.UUID
    cod_credito: str
    referencia: str
    estado: Literal["CONFIRMADO", "RECHAZADO", "PENDIENTE"]
    motivo: str | None = Field(description="Si el débito se rechazó: SALDO_INSUFICIENTE, CUENTA_NO_OPERATIVA, "
                                           "TOPE_DIARIO_SUPERADO o CANAL_NO_ADMITIDO.")
    monto: Monto
    monto_aplicado: Monto
    num_cuenta: str | None
    canal: str
    uuid_transaccion: uuid.UUID | None = Field(description="El movimiento DEBITO_CUOTA; nulo si se rechazó.")
    fecha: datetime
    aplicaciones: list[AplicacionPago]


class PagoRegistrado(PagoRespuesta):
    estado_credito: str = Field(description="Estado del crédito al responder.")
    saldo_pendiente: Monto = Field(description="Deuda del crédito al responder.")


class MoraRespuesta(_Respuesta):
    id_mora: uuid.UUID
    cod_credito: str
    numero_cuota: int
    monto_calculado: Monto
    fecha_calculo: datetime
    dias_atraso: int = Field(description="Días entre el vencimiento y la fecha del cálculo (Lima).")
    vigente: bool = Field(description="Solo el último cálculo de la cuota está vigente.")


class VencimientosResultado(_Respuesta):
    fecha: date
    cuotas_vencidas: int
    creditos_actualizados: int


class ConciliacionPagos(_Respuesta):
    fecha: date
    canal: str
    moneda: str
    pagos_confirmados: int
    importe_cobrado: Monto
    importe_aplicado: Monto
    pagos_rechazados: int


# ── Rutas fijas ─────────────────────────────────────────────────────────────


@router.get("/conciliacion/pagos", response_model=list[ConciliacionPagos],
            dependencies=[Depends(requiere_permiso("GENERAR_REPORTES"))], responses=ERRORES_COMUNES)
def conciliacion(fecha: date | None = None, db: Session = Depends(db_session)):
    """Lo cobrado (movimientos DEBITO_CUOTA) frente a lo aplicado a cuotas, por día de
    negocio (Lima), canal y moneda, con los pagos rechazados. Sin `fecha`, todos los días con
    pagos."""
    return creditos.conciliacion_pagos(db, fecha)


@router.get("/pagos/{referencia}", response_model=PagoRespuesta,
            dependencies=[Depends(requiere_permiso("CONSULTAR_DEUDA"))],
            responses={**ERRORES_COMUNES, 404: {"description": "PAGO_NO_ENCONTRADO"}})
def comprobante(referencia: str = Path(min_length=1, max_length=40), db: Session = Depends(db_session)):
    """El pago con esa referencia: su estado, el movimiento y el reparto entre cuotas."""
    return creditos.pago_por_referencia(db, referencia)


@router.post("/vencimientos", response_model=VencimientosResultado,
             responses={**ERRORES_COMUNES, 422: {"description": "FECHA_NO_ADMITIDA"}})
def vencimientos(
    datos: VencimientosEjecutar | None = Body(default=None),
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("REGISTRAR_MORA")),
):
    """Marca VENCIDA cada cuota PENDIENTE o PARCIAL que venció antes de la fecha y deja cada
    crédito no cancelado EN_MORA (con una cuota VENCIDA) o AL_DIA. La base lo corre también
    una vez al día (00:10, Lima); repetirlo el mismo día no cambia nada. Es la tarea diaria de
    `svc-cobranza`."""
    return creditos.actualizar_vencimientos(db, datos.fecha if datos else None, actor=actor.usuario)


@router.get("", response_model=list[CreditoRespuesta],
            dependencies=[Depends(requiere_permiso("CONSULTAR_DEUDA"))], responses=ERRORES_COMUNES)
def listar(
    estado: EstadoCredito | None = None,
    cod_cliente: str | None = Query(default=None, alias="codCliente", min_length=1, max_length=12),
    limite: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(db_session),
):
    """Créditos desembolsados, del más reciente al más antiguo."""
    return creditos.listar_creditos(db, estado=estado, cod_cliente=cod_cliente, limite=limite, offset=offset)


# ── Rutas del crédito ───────────────────────────────────────────────────────


@router.get("/{cod_credito}", response_model=CreditoDetalle,
            dependencies=[Depends(requiere_permiso("CONSULTAR_DEUDA"))],
            responses={**ERRORES_COMUNES, **NO_ENCONTRADO})
def detalle(cod_credito: CodCredito, db: Session = Depends(db_session)):
    """El crédito con sus cuotas (saldo, días de atraso, mora vigente) y su bitácora."""
    return creditos.detalle_credito(db, cod_credito)


@router.get("/{cod_credito}/pagos", response_model=list[PagoRespuesta],
            dependencies=[Depends(requiere_permiso("CONSULTAR_DEUDA"))],
            responses={**ERRORES_COMUNES, **NO_ENCONTRADO})
def pagos(
    cod_credito: CodCredito,
    limite: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(db_session),
):
    """Los pagos del crédito, confirmados y rechazados, del más reciente al más antiguo."""
    return creditos.pagos_del_credito(db, cod_credito, limite=limite, offset=offset)


@router.post("/{cod_credito}/pagos", response_model=PagoRegistrado, status_code=status.HTTP_201_CREATED,
             responses={**ERRORES_COMUNES, **NO_ENCONTRADO,
                        200: {"description": "La misma referencia con el mismo contenido: el mismo pago"},
                        409: {"description": "IDEMPOTENCIA_CONFLICTO"},
                        422: {"description": "PAGO_NO_ADMITIDO, CREDITO_NO_ADMITIDO o CUENTA_NO_ELEGIBLE"}})
def pagar(
    cod_credito: CodCredito,
    datos: PagoRegistrar,
    respuesta: Response,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("REGISTRAR_PAGO")),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """Cobra un pago en una sola operación: debita la cuenta del titular (movimiento
    DEBITO_CUOTA) y lo aplica de la cuota más antigua a la más reciente. Si el débito se
    rechaza (saldo, cuenta no operativa, tope del canal), el pago queda RECHAZADO con su
    `motivo`, sin movimiento y sin tocar las cuotas, y responde 201. La misma referencia con
    el mismo contenido responde 200 con el mismo pago, sin debitar otra vez (también si fue
    RECHAZADO: otro intento lleva otra referencia); con otro contenido u otro crédito, 409. Un
    monto mayor que la deuda total, una cuenta ajena o un crédito cancelado dan 422 sin
    registrar nada."""
    pago, repetido = creditos.registrar_pago(db, cod_credito, datos, correlation_id=correlation_id,
                                             actor=actor.usuario)
    if repetido:
        respuesta.status_code = status.HTTP_200_OK
    return pago


@router.post("/{cod_credito}/cuotas/{numero_cuota}/mora", response_model=MoraRespuesta,
             status_code=status.HTTP_201_CREATED,
             responses={**ERRORES_COMUNES, **NO_ENCONTRADO,
                        422: {"description": "CUOTA_NO_ADMITIDA (no existe, no tiene saldo o aún no vence)"}})
def registrar_mora(
    cod_credito: CodCredito,
    numero_cuota: NumeroCuota,
    datos: MoraRegistrar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("REGISTRAR_MORA")),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """Registra un cálculo de mora de una cuota vencida con saldo. Ninguna fuente define la
    fórmula: la calcula quien llama. Queda vigente el último cálculo; la mora se muestra en la
    deuda, pero no se cobra (decisión 5 del contrato)."""
    return creditos.registrar_mora(db, cod_credito, numero_cuota, monto=datos.monto_calculado,
                                   correlation_id=correlation_id, actor=actor.usuario)


@router.get("/{cod_credito}/cuotas/{numero_cuota}/mora", response_model=list[MoraRespuesta],
            dependencies=[Depends(requiere_permiso("CONSULTAR_DEUDA"))],
            responses={**ERRORES_COMUNES, **NO_ENCONTRADO})
def historial_mora(cod_credito: CodCredito, numero_cuota: NumeroCuota, db: Session = Depends(db_session)):
    """Los cálculos de mora de la cuota, del más reciente al más antiguo."""
    return creditos.historial_mora(db, cod_credito, numero_cuota)
