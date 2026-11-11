import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from COREDB.auth import Actor, requiere_permiso
from COREDB.database import db_session
from COREDB.errores import ErrorCoreDb
from COREDB.models import Movimiento
from COREDB.routers.cuentas import obtener as obtener_cuenta
from COREDB.services import movimientos

router = APIRouter(prefix="/coredb/movimientos", tags=["movimientos"])

Monto = Annotated[Decimal, Field(gt=0, max_digits=15, decimal_places=2)]


class _Operacion(BaseModel):
    monto: Monto
    glosa: str = Field(min_length=1, max_length=200)
    id_canal: str = Field(min_length=1, max_length=5)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=64)
    correlation_id: uuid.UUID = Field(default_factory=uuid.uuid4)


class MovimientoRegistrar(_Operacion):
    num_cuenta: str = Field(min_length=1, max_length=20)
    tipo: Literal["DEPOSITO", "RETIRO"]


class TransferenciaRegistrar(_Operacion):
    origen: str = Field(min_length=1, max_length=20)
    destino: str = Field(min_length=1, max_length=20)


class MovimientoRespuesta(BaseModel):
    uuid_transaccion: uuid.UUID
    repetido: bool


class TransferenciaRespuesta(BaseModel):
    uuid_debito: uuid.UUID
    uuid_abono: uuid.UUID
    repetido: bool


@router.post("", response_model=MovimientoRespuesta, status_code=status.HTTP_201_CREATED)
def registrar(
    datos: MovimientoRegistrar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("REGISTRAR_MOVIMIENTO")),
):
    return movimientos.registrar(db, **datos.model_dump(), actor=actor.usuario)


@router.post(
    "/transferencias",
    response_model=TransferenciaRespuesta,
    status_code=status.HTTP_201_CREATED,
)
def transferir(
    datos: TransferenciaRegistrar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("REGISTRAR_MOVIMIENTO")),
):
    return movimientos.transferir(db, **datos.model_dump(), actor=actor.usuario)


class MovimientoDetalle(BaseModel):
    """Un movimiento aplicado a una cuenta. `naturaleza` es D (débito) o C (crédito)."""

    model_config = ConfigDict(from_attributes=True)

    uuid_transaccion: uuid.UUID
    num_cuenta: str
    tipo_operacion: str
    naturaleza: Literal["D", "C", "N"]
    monto: Decimal
    moneda: str
    glosa: str
    id_canal: str | None
    estado_transaccion: str
    fecha_hora: datetime


@router.get("/cuenta/{num_cuenta}", response_model=list[MovimientoDetalle],
            dependencies=[Depends(requiere_permiso("VER_CUENTA"))],
            responses={404: {"description": "CUENTA_NO_ENCONTRADA"}})
def de_una_cuenta(
    num_cuenta: str,
    limite: int = Query(default=50, ge=1, le=200),
    antes_de: datetime | None = Query(
        default=None, description="Solo movimientos anteriores a esta fecha y hora (para paginar)."
    ),
    db: Session = Depends(db_session),
):
    """Los movimientos de una cuenta, del más reciente al más antiguo. Una transferencia
    aparece como TRANSFERENCIA_ENVIADA en la cuenta de origen y TRANSFERENCIA_RECIBIDA
    en la de destino."""
    obtener_cuenta(db, num_cuenta)
    consulta = db.query(Movimiento).filter(Movimiento.num_cuenta == num_cuenta)
    if antes_de is not None:
        # La base guarda UTC sin zona.
        if antes_de.tzinfo is not None:
            antes_de = antes_de.astimezone(timezone.utc).replace(tzinfo=None)
        consulta = consulta.filter(Movimiento.fecha_hora < antes_de)
    return (
        consulta.order_by(Movimiento.fecha_hora.desc(), Movimiento.uuid_transaccion)
        .limit(limite)
        .all()
    )


@router.get("/{uuid_transaccion}", response_model=MovimientoDetalle,
            dependencies=[Depends(requiere_permiso("VER_CUENTA"))],
            responses={404: {"description": "MOVIMIENTO_NO_ENCONTRADO"}})
def ver(uuid_transaccion: uuid.UUID, db: Session = Depends(db_session)):
    movimiento = db.get(Movimiento, uuid_transaccion)
    if movimiento is None:
        raise ErrorCoreDb("MOVIMIENTO_NO_ENCONTRADO", "El movimiento no existe.", 404)
    return movimiento
