import json
from decimal import Decimal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from COREDB.auth import Actor, actor_actual
from COREDB.database import db_session, llamar
from COREDB.errores import ErrorCoreDb
from COREDB.models import CuentaAhorro
from COREDB.transacciones import con_reintentos

router = APIRouter(prefix="/coredb/cuentas", tags=["cuentas"])


class CuentaAbrir(BaseModel):
    num_cuenta: str = Field(min_length=1, max_length=20)
    cci: str = Field(min_length=20, max_length=20)
    moneda: str = Field(min_length=3, max_length=3)
    regimen: str = Field(max_length=25)
    id_agencia: str | None = Field(default=None, max_length=10)
    titulares: list[str] = Field(min_length=1)


class CuentaRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    num_cuenta: str
    cci: str
    moneda: str
    regimen: str
    saldo_contable: Decimal
    saldo_disponible: Decimal
    estado_cuenta: str
    id_agencia: str | None


def _obtener(db: Session, num_cuenta: str) -> CuentaAhorro:
    cuenta = db.get(CuentaAhorro, num_cuenta)
    if cuenta is None:
        raise ErrorCoreDb("CUENTA_NO_ENCONTRADA", f"La cuenta {num_cuenta} no existe.", 404)
    return cuenta


@router.get("/{num_cuenta}", response_model=CuentaRespuesta)
def ver(num_cuenta: str, db: Session = Depends(db_session)):
    return _obtener(db, num_cuenta)


@router.post("", response_model=CuentaRespuesta, status_code=status.HTTP_201_CREATED)
def abrir(
    datos: CuentaAbrir,
    db: Session = Depends(db_session),
    actor: Actor = Depends(actor_actual),
):
    con_reintentos(
        db,
        lambda: llamar(
            db, "cuentas.abrir_cuenta",
            datos.num_cuenta, datos.cci, datos.moneda, datos.regimen, datos.id_agencia,
            json.dumps(datos.titulares), actor.usuario,
        ),
        nombre="abrir_cuenta",
    )
    return _obtener(db, datos.num_cuenta)
