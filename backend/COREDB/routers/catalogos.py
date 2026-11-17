import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, field_validator
from pydantic.alias_generators import to_camel
from sqlalchemy.orm import Session

from COREDB.auth import actor_actual
from COREDB.database import db_session
from COREDB.models import Agencia, Moneda, ProductoAhorro, ProductoCredito, TipoCambio
from COREDB.services import clientes, creditos

# Cualquier usuario autenticado lee los catálogos.
router = APIRouter(prefix="/coredb/catalogos", tags=["catálogos"], dependencies=[Depends(actor_actual)])


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


class TipoDocumentoRespuesta(BaseModel):
    codigo: str
    descripcion: str
    longitud_min: int
    longitud_max: int
    es_alfanumerico: bool


class EstadoClienteRespuesta(BaseModel):
    codigo: str
    descripcion: str
    permite_operar: bool


class CatalogosClientesRespuesta(BaseModel):
    tipos_documento: list[TipoDocumentoRespuesta]
    estados_cliente: list[EstadoClienteRespuesta]


@router.get("/clientes", response_model=CatalogosClientesRespuesta)
def catalogos_de_clientes(db: Session = Depends(db_session)):
    """Tipos de documento con sus reglas y estados de cliente. Conviene que el módulo
    Clientes lea de aquí las reglas de documento en lugar de fijarlas en su código."""
    return clientes.catalogos(db)


class _CatalogoCredito(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CodigoCredito(_CatalogoCredito):
    codigo: str
    descripcion: str


class EstadoCredito(CodigoCredito):
    es_final: bool


class ReglaEvaluacion(_CatalogoCredito):
    id_regla: str
    codigo_rn: str
    descripcion: str
    ratio_min: Decimal | None
    ratio_max: Decimal | None
    resultado: str

    @field_validator("ratio_min", "ratio_max")
    @classmethod
    def _dos_decimales(cls, valor: Decimal | None) -> Decimal | None:
        # DECIMAL(7,2) en la tabla; dentro de un JSON de MySQL 80.00 llega como 80.0.
        return None if valor is None else valor.quantize(Decimal("0.01"))


class CatalogosCreditoRespuesta(_CatalogoCredito):
    estados_solicitud: list[EstadoCredito]
    reglas: list[ReglaEvaluacion]
    metodos_amortizacion: list[CodigoCredito]
    tipos_validacion: list[CodigoCredito]
    estados_orden: list[EstadoCredito]
    estados_cuota: list[CodigoCredito]
    estados_credito: list[CodigoCredito]
    canales_desembolso: list[str]
    vigencia_aprobacion_dias: int


@router.get("/creditos", response_model=CatalogosCreditoRespuesta)
def catalogos_de_creditos(db: Session = Depends(db_session)):
    """Estados, reglas de RN-EVA-002-P con sus umbrales (ratio monto / límite, en %), métodos
    de amortización, tipos de validación del desembolso, canales y vigencia de una aprobación.
    Campos en camelCase, como el resto de créditos (CONTRATO_CREDITOS.md)."""
    return creditos.catalogos(db)
