import uuid
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from COREDB.auth import Actor, actor_actual
from COREDB.database import db_session
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
    actor: Actor = Depends(actor_actual),
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
    actor: Actor = Depends(actor_actual),
):
    return movimientos.transferir(db, **datos.model_dump(), actor=actor.usuario)
