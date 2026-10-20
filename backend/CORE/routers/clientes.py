"""Routers de clientes — VER/CREAR/MODIFICAR_CLIENTE."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from CORE.dependencies import db_session
from CORE.schemas.clientes import (
    ClienteAltaRespuesta,
    ClienteCrear,
    ClienteModificar,
    ClienteRespuesta,
)
from CORE.services import clientessvc

router = APIRouter(prefix="/clientes", tags=["Clientes"])


def _a_respuesta(cliente) -> ClienteRespuesta:
    return ClienteRespuesta(
        id_cliente=cliente.id_cliente,
        cod_tipo_documento=cliente.cod_tipo_documento,
        numero_documento=cliente.numero_documento,
        nombres=cliente.nombres,
        apellido_paterno=cliente.apellido_paterno,
        apellido_materno=cliente.apellido_materno,
        fecha_nacimiento=cliente.fecha_nacimiento,
        numero_celular=cliente.numero_celular,
        correo_electronico=cliente.correo_electronico,
        estado_cliente=cliente.estado_cliente,
        fecha_registro=str(cliente.fecha_registro) if cliente.fecha_registro else None,
    )


@router.get("", response_model=list[ClienteRespuesta])
def ver_clientes(
    documento: str | None = Query(default=None),
    estado: str | None = Query(default=None),
    limite: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(db_session),
):
    clientes = clientessvc.listar_clientes(
        db, documento=documento, estado=estado, limite=limite, offset=offset
    )
    return [_a_respuesta(c) for c in clientes]


@router.get("/{id_cliente}", response_model=ClienteRespuesta)
def ver_cliente(id_cliente: str, db: Session = Depends(db_session)):
    return _a_respuesta(clientessvc.obtener_cliente(db, id_cliente))


@router.post("", response_model=ClienteAltaRespuesta, status_code=status.HTTP_201_CREATED)
def crear_cliente(payload: ClienteCrear, db: Session = Depends(db_session)):
    cliente, duplicado = clientessvc.crear_cliente(
        db,
        cod_tipo_documento=payload.cod_tipo_documento,
        numero_documento=payload.numero_documento,
        nombres=payload.nombres,
        apellido_paterno=payload.apellido_paterno,
        apellido_materno=payload.apellido_materno,
        fecha_nacimiento=payload.fecha_nacimiento,
        numero_celular=payload.numero_celular,
        correo_electronico=payload.correo_electronico,
        actor=payload.actor,
        correlation_id=payload.correlation_id,
    )
    return ClienteAltaRespuesta(cliente=_a_respuesta(cliente), duplicado=duplicado)


@router.patch("/{id_cliente}", response_model=ClienteRespuesta)
def modificar_cliente(
    id_cliente: str, payload: ClienteModificar, db: Session = Depends(db_session)
):
    datos = payload.model_dump(exclude_unset=True)
    actor = datos.pop("actor", "sistema")
    correlation_id = datos.pop("correlation_id", None)
    cliente = clientessvc.modificar_cliente(
        db,
        id_cliente,
        actor=actor,
        correlation_id=correlation_id,
        **datos,
    )
    return _a_respuesta(cliente)
