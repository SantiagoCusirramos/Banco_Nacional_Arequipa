import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from COREDB.database import db_session
from COREDB.models import Agencia, Moneda, ProductoAhorro, ProductoCredito, TipoCambio

router = APIRouter(prefix="/coredb/catalogos", tags=["catálogos"])


class _Lectura(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MonedaRespuesta(_Lectura):
    cod_moneda: str
    nombre: str
    simbolo: str
    decimales: int


class AgenciaRespuesta(_Lectura):
    id_agencia: str
    nombre: str


class ProductoAhorroRespuesta(_Lectura):
    id_producto_ahorro: uuid.UUID
    nombre: str
    moneda: str
    tasa_tea: Decimal
    activo: bool


class ProductoCreditoRespuesta(_Lectura):
    id_producto_credito: uuid.UUID
    nombre: str
    tasa_tea: Decimal
    plazo_min_meses: int
    plazo_max_meses: int
    activo: bool


class TipoCambioRespuesta(_Lectura):
    cod_moneda_origen: str
    cod_moneda_destino: str
    fecha: date
    tasa: Decimal


@router.get("/monedas", response_model=list[MonedaRespuesta])
def monedas(db: Session = Depends(db_session)):
    return db.query(Moneda).order_by(Moneda.cod_moneda).all()


@router.get("/agencias", response_model=list[AgenciaRespuesta])
def agencias(db: Session = Depends(db_session)):
    return db.query(Agencia).order_by(Agencia.id_agencia).all()


@router.get("/productos-ahorro", response_model=list[ProductoAhorroRespuesta])
def productos_ahorro(db: Session = Depends(db_session)):
    return db.query(ProductoAhorro).order_by(ProductoAhorro.nombre).all()


@router.get("/productos-credito", response_model=list[ProductoCreditoRespuesta])
def productos_credito(db: Session = Depends(db_session)):
    return db.query(ProductoCredito).order_by(ProductoCredito.nombre).all()


@router.get("/tipos-cambio", response_model=list[TipoCambioRespuesta])
def tipos_cambio(db: Session = Depends(db_session)):
    return db.query(TipoCambio).order_by(TipoCambio.fecha.desc()).limit(200).all()
