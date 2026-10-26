"""Catálogos de solo lectura para llenar los formularios del frontend."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from CORE.dependencies import db_session
from CORE.models.catalogos import Agencia, ProductoAhorro
from CORE.schemas.catalogos import AgenciaRespuesta, ProductoAhorroRespuesta

router = APIRouter(prefix="/catalogos", tags=["Catálogos"])


@router.get("/agencias", response_model=list[AgenciaRespuesta])
def listar_agencias(db: Session = Depends(db_session)):
    """Agencias activas (para elegir dónde se abre la cuenta)."""
    agencias = db.scalars(
        select(Agencia).where(Agencia.activa.is_(True)).order_by(Agencia.nombre)
    ).all()
    return [
        AgenciaRespuesta(
            id_agencia=a.id_agencia, nombre=a.nombre, direccion=a.direccion
        )
        for a in agencias
    ]


@router.get("/productos-ahorro", response_model=list[ProductoAhorroRespuesta])
def listar_productos_ahorro(db: Session = Depends(db_session)):
    """Productos de ahorro activos (los únicos que admite CREAR_CUENTA)."""
    productos = db.scalars(
        select(ProductoAhorro)
        .where(ProductoAhorro.activo.is_(True))
        .order_by(ProductoAhorro.nombre)
    ).all()
    return [
        ProductoAhorroRespuesta(
            id_producto_ahorro=p.id_producto_ahorro,
            nombre=p.nombre,
            moneda=p.moneda,
            tasa_tea=p.tasa_tea,
        )
        for p in productos
    ]
