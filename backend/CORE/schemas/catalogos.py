"""Schemas de catálogos de solo lectura (agencias y productos de ahorro)."""

from decimal import Decimal

from CORE.schemas.common import CoreModel

class AgenciaRespuesta(CoreModel):
    id_agencia: str
    nombre: str
    direccion: str

class ProductoAhorroRespuesta(CoreModel):
    id_producto_ahorro: str
    nombre: str
    moneda: str
    tasa_tea: Decimal
