import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from COREDB.auth import Actor, requiere_permiso
from COREDB.database import db_session
from COREDB.errores import ErrorCoreDb
from COREDB.models import CtaTransaccion
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


class MovimientoRespuestaDetalle(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_transaccion: str
    uuid_transaccion: str
    num_cuenta: str
    num_cuenta_contraparte: str | None
    tipo_operacion: str
    tipo_movimiento: str
    monto: Decimal
    moneda: str
    id_canal: str
    saldo_posterior: Decimal
    estado_transaccion: str
    fecha_hora: datetime


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


@router.get("/cuenta/{num_cuenta}", response_model=list[MovimientoRespuestaDetalle],
            dependencies=[Depends(requiere_permiso("VER_CUENTA"))])
def listar_por_cuenta(num_cuenta: str, db: Session = Depends(db_session)):
    return db.query(CtaTransaccion).filter(CtaTransaccion.num_cuenta == num_cuenta).order_by(CtaTransaccion.fecha_hora.desc()).all()


@router.get("/{uuid_transaccion}", response_model=MovimientoRespuestaDetalle,
            dependencies=[Depends(requiere_permiso("VER_CUENTA"))])
def ver_movimiento(uuid_transaccion: str, db: Session = Depends(db_session)):
    mov = db.query(CtaTransaccion).filter(CtaTransaccion.uuid_transaccion == uuid_transaccion).first()
    if not mov:
        raise ErrorCoreDb("MOVIMIENTO_NO_ENCONTRADO", f"El movimiento {uuid_transaccion} no existe.", 404)
    return mov
