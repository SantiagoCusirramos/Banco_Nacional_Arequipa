import json
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from COREDB.auth import Actor, requiere_permiso
from COREDB.database import db_session, llamar
from COREDB.errores import ErrorCoreDb
from COREDB.models import CuentaAhorro, Titularidad
from COREDB.services import clientes
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
    titulares: list[str] = Field(description="Códigos de los clientes titulares, en orden.")


def obtener(db: Session, num_cuenta: str) -> CuentaAhorro:
    cuenta = db.get(CuentaAhorro, num_cuenta)
    if cuenta is None:
        raise ErrorCoreDb("CUENTA_NO_ENCONTRADA", f"La cuenta {num_cuenta} no existe.", 404)
    return cuenta


def _con_titulares(db: Session, cuentas: list[CuentaAhorro]) -> list[CuentaRespuesta]:
    titulares: dict[str, list[str]] = {c.num_cuenta: [] for c in cuentas}
    if cuentas:
        filas = (
            db.query(Titularidad)
            .filter(Titularidad.num_cuenta.in_(titulares))
            .order_by(Titularidad.cod_cliente)
        )
        for fila in filas:
            titulares[fila.num_cuenta].append(fila.cod_cliente)
    return [
        CuentaRespuesta.model_validate({
            "num_cuenta": c.num_cuenta, "cci": c.cci, "moneda": c.moneda, "regimen": c.regimen,
            "saldo_contable": c.saldo_contable, "saldo_disponible": c.saldo_disponible,
            "estado_cuenta": c.estado_cuenta, "id_agencia": c.id_agencia,
            "titulares": titulares[c.num_cuenta],
        })
        for c in cuentas
    ]


@router.get("", response_model=list[CuentaRespuesta],
            dependencies=[Depends(requiere_permiso("VER_CUENTA"))],
            responses={404: {"description": "CLIENTE_NO_ENCONTRADO"}})
def de_un_cliente(
    cod_cliente: str = Query(min_length=1, max_length=12, pattern=r"^[A-Za-z0-9]+$"),
    db: Session = Depends(db_session),
):
    """Las cuentas en las que el cliente es titular, por número de cuenta. No hay una
    ruta que liste todas las cuentas."""
    clientes.consultar(db, cod_cliente)  # 404 si el cliente no existe
    cuentas = (
        db.query(CuentaAhorro)
        .join(Titularidad, Titularidad.num_cuenta == CuentaAhorro.num_cuenta)
        .filter(Titularidad.cod_cliente == cod_cliente)
        .order_by(CuentaAhorro.num_cuenta)
        .all()
    )
    return _con_titulares(db, cuentas)


@router.get("/{num_cuenta}", response_model=CuentaRespuesta,
            dependencies=[Depends(requiere_permiso("VER_CUENTA"))])
def ver(num_cuenta: str, db: Session = Depends(db_session)):
    return _con_titulares(db, [obtener(db, num_cuenta)])[0]


@router.post("", response_model=CuentaRespuesta, status_code=status.HTTP_201_CREATED)
def abrir(
    datos: CuentaAbrir,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("CREAR_CUENTA")),
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
    return _con_titulares(db, [obtener(db, datos.num_cuenta)])[0]
