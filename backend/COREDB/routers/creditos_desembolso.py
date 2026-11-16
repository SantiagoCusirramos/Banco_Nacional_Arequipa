"""Créditos: órdenes de desembolso, validaciones, confirmación con abono y conciliación.

Ver CONTRATO_CREDITOS.md §4. Confirmar una orden abona la cuenta, crea el crédito con su
calendario OFICIAL y deja la solicitud DESEMBOLSADA en una sola transacción de la base.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, Query, Response, status
from pydantic import AwareDatetime, Field
from sqlalchemy.orm import Session

from COREDB.auth import Actor, requiere_permiso
from COREDB.correlacion import correlacion
from COREDB.database import db_session
from COREDB.routers.creditos_evaluacion import ERRORES_COMUNES, _Peticion, _Respuesta
from COREDB.services import creditos

router = APIRouter(prefix="/coredb/creditos", tags=["créditos: desembolso"])

EstadoOrden = Literal["PREPARADA", "VALIDADA", "EN_PROCESO", "POR_VERIFICAR", "CONFIRMADA", "RECHAZADA",
                      "REVERTIDA"]
NumCuenta = Field(min_length=1, max_length=20)
NO_ENCONTRADA = {404: {"description": "ORDEN_NO_ENCONTRADA"}}


class OrdenPreparar(_Peticion):
    id_evaluacion: uuid.UUID = Field(description="La aprobación: `idEvaluacion` de `GET /coredb/creditos/aprobaciones`.")
    num_cuenta: str = NumCuenta
    canal: Literal["VEN", "HB"] = "VEN"
    id_agencia: str | None = Field(default=None, min_length=1, max_length=10)


class CuentaCambiar(_Peticion):
    num_cuenta: str = NumCuenta


class ValidacionOrdenRegistrar(_Peticion):
    tipo: Literal["IDENTIDAD", "AUTORIZACION", "ANTIFRAUDE"] = Field(
        description="La validación CUENTA la registra COREDB al elegir la cuenta.")
    resultado: Literal["APROBADA", "RECHAZADA"]
    referencia_evidencia: str = Field(
        min_length=1, max_length=100,
        description="En IDENTIDAD aprobada, el `id_validacion` de `POST /coredb/clientes/validaciones/documento`, "
                    "aprobado hoy para el titular.")
    detalle: str | None = Field(default=None, max_length=255)
    vence_en: AwareDatetime | None = None


class RechazoRegistrar(_Peticion):
    motivo: str = Field(min_length=1, max_length=255)


class OrdenRespuesta(_Respuesta):
    id_orden: uuid.UUID
    codigo_orden: str
    estado: str
    motivo_rechazo: str | None
    importe: Decimal
    moneda: str
    num_cuenta: str
    canal: str
    id_agencia: str | None
    id_evaluacion: uuid.UUID
    id_solicitud: uuid.UUID
    cod_cliente: str
    usuario_preparacion: str
    usuario_confirmacion: str | None
    uuid_transaccion_abono: uuid.UUID | None
    cod_credito: str | None
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class ValidacionOrdenRespuesta(_Respuesta):
    id_validacion: uuid.UUID
    tipo: str
    resultado: str
    referencia_evidencia: str
    detalle: str | None
    vence_en: datetime | None
    fecha: datetime


class EventoOrdenRespuesta(_Respuesta):
    accion: str
    resultado: str | None
    actor: str
    correlation_id: uuid.UUID | None
    detalle: dict[str, Any] | None
    fecha_hora: datetime


class OrdenDetalle(OrdenRespuesta):
    validaciones: list[ValidacionOrdenRespuesta]
    eventos: list[EventoOrdenRespuesta]


class OrdenConfirmada(_Respuesta):
    id_orden: uuid.UUID
    codigo_orden: str
    estado: str
    cod_credito: str
    uuid_transaccion_abono: uuid.UUID
    fecha_efectiva: datetime = Field(description="Fecha y hora del abono.")


class ConciliacionDesembolso(_Respuesta):
    fecha: date
    moneda: str
    ordenes_confirmadas: int
    importe_ordenes: Decimal
    importe_abonado: Decimal
    ordenes_sin_abono: int


@router.post("/ordenes", response_model=OrdenRespuesta, status_code=status.HTTP_201_CREATED,
             responses={**ERRORES_COMUNES, 200: {"description": "La misma llave con el mismo contenido"},
                        409: {"description": "IDEMPOTENCIA_CONFLICTO"},
                        422: {"description": "APROBACION_NO_VIGENTE, CALENDARIO_INVALIDO, ORDEN_NO_ADMITIDA o "
                                             "CUENTA_NO_ELEGIBLE"}})
def preparar(
    datos: OrdenPreparar,
    respuesta: Response,
    llave: uuid.UUID = Header(alias="X-Idempotency-Key"),
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("DESEMBOLSAR_CREDITO")),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """Prepara la orden de desembolso de una aprobación vigente, con la cuenta elegida. El
    importe es el monto solicitado. Se rechaza si la aprobación venció, si su primera cuota
    ya venció o si ya tiene una orden abierta. La misma llave con el mismo contenido responde
    200 con la misma orden; con otro contenido, 409."""
    orden, repetido = creditos.preparar_orden(db, datos, llave=llave, correlation_id=correlation_id,
                                              actor=actor.usuario)
    if repetido:
        respuesta.status_code = status.HTTP_200_OK
    return orden


@router.get("/ordenes", response_model=list[OrdenRespuesta],
            dependencies=[Depends(requiere_permiso("VER_CREDITO"))], responses=ERRORES_COMUNES)
def monitor(
    estado: EstadoOrden | None = None,
    cod_cliente: str | None = Query(default=None, alias="codCliente", min_length=1, max_length=12),
    id_solicitud: uuid.UUID | None = Query(default=None, alias="idSolicitud"),
    limite: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(db_session),
):
    """Órdenes de desembolso, de la más reciente a la más antigua."""
    return creditos.listar_ordenes(db, estado=estado, cod_cliente=cod_cliente, id_solicitud=id_solicitud,
                                   limite=limite, offset=offset)


@router.get("/ordenes/{id_orden}", response_model=OrdenDetalle,
            dependencies=[Depends(requiere_permiso("VER_CREDITO"))],
            responses={**ERRORES_COMUNES, **NO_ENCONTRADA})
def detalle(id_orden: uuid.UUID, db: Session = Depends(db_session)):
    """La orden con sus validaciones y su bitácora."""
    return creditos.detalle_orden(db, id_orden)


@router.put("/ordenes/{id_orden}/cuenta", response_model=OrdenRespuesta,
            responses={**ERRORES_COMUNES, **NO_ENCONTRADA,
                       422: {"description": "ORDEN_NO_ADMITIDA o CUENTA_NO_ELEGIBLE"}})
def cambiar_cuenta(
    id_orden: uuid.UUID,
    datos: CuentaCambiar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("DESEMBOLSAR_CREDITO")),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """Cambia la cuenta de una orden PREPARADA o VALIDADA y registra otra validación CUENTA.
    El estado se recalcula: con la identidad ya aprobada, la orden sigue VALIDADA."""
    return creditos.cambiar_cuenta(db, id_orden, num_cuenta=datos.num_cuenta, correlation_id=correlation_id,
                                   actor=actor.usuario)


@router.post("/ordenes/{id_orden}/validaciones", response_model=OrdenRespuesta,
             status_code=status.HTTP_201_CREATED,
             responses={**ERRORES_COMUNES, **NO_ENCONTRADA,
                        422: {"description": "VALIDACION_NO_ADMITIDA u ORDEN_NO_ADMITIDA"}})
def validar(
    id_orden: uuid.UUID,
    datos: ValidacionOrdenRegistrar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("DESEMBOLSAR_CREDITO")),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """Registra una validación de la orden. Con la última IDENTIDAD y la última CUENTA
    aprobadas, y ninguna última validación rechazada, la orden queda VALIDADA; si no,
    PREPARADA. La identidad se verifica el mismo día del desembolso (fecha de Lima)."""
    return creditos.registrar_validacion(db, id_orden, datos, correlation_id=correlation_id, actor=actor.usuario)


@router.post("/ordenes/{id_orden}/confirmacion", response_model=OrdenConfirmada,
             status_code=status.HTTP_201_CREATED,
             responses={**ERRORES_COMUNES, **NO_ENCONTRADA,
                        200: {"description": "La orden ya estaba confirmada: el mismo crédito y el mismo abono"},
                        422: {"description": "ORDEN_NO_ADMITIDA, APROBACION_NO_VIGENTE, VALIDACION_NO_ADMITIDA "
                                             "o CUENTA_NO_ELEGIBLE"}})
def confirmar(
    id_orden: uuid.UUID,
    respuesta: Response,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("DESEMBOLSAR_CREDITO")),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """Confirma una orden VALIDADA en una sola operación: abona la cuenta (movimiento
    DESEMBOLSO), crea el crédito AL_DIA con su calendario OFICIAL, copia del PRELIMINAR, y
    deja la solicitud DESEMBOLSADA. Confirmar otra vez responde 200 con el mismo crédito y el
    mismo abono, sin abonar de nuevo: si se pierde la respuesta, se repite la llamada."""
    confirmada, repetido = creditos.confirmar_orden(db, id_orden, correlation_id=correlation_id,
                                                    actor=actor.usuario)
    if repetido:
        respuesta.status_code = status.HTTP_200_OK
    return confirmada


@router.post("/ordenes/{id_orden}/rechazo", response_model=OrdenRespuesta,
             responses={**ERRORES_COMUNES, **NO_ENCONTRADA, 422: {"description": "ORDEN_NO_ADMITIDA"}})
def rechazar(
    id_orden: uuid.UUID,
    datos: RechazoRegistrar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("DESEMBOLSAR_CREDITO")),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """Rechaza una orden PREPARADA o VALIDADA con su motivo. La aprobación sigue vigente y
    admite otra orden."""
    return creditos.rechazar_orden(db, id_orden, motivo=datos.motivo, correlation_id=correlation_id,
                                   actor=actor.usuario)


@router.get("/conciliacion/desembolsos", response_model=list[ConciliacionDesembolso],
            dependencies=[Depends(requiere_permiso("GENERAR_REPORTES"))], responses=ERRORES_COMUNES)
def conciliacion(fecha: date | None = None, db: Session = Depends(db_session)):
    """Órdenes confirmadas frente a lo abonado en las cuentas, por día de negocio (Lima) y
    moneda. Sin `fecha`, los últimos días con desembolsos."""
    return creditos.conciliacion_desembolsos(db, fecha)
