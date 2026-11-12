"""Routers de tarjetas — VER/CREAR/BLOQUEAR_TARJETA.

Exigen token y permiso. El actor sale siempre del token: el campo `actor` del
cuerpo se ignora.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from CORE.dependencies import db_session, requiere_permiso
from CORE.models import UsuarioSistema
from CORE.schemas.tarjetas import (
    TarjetaCrear,
    TarjetaEstadoCambiar,
    TarjetaRespuesta,
)
from CORE.services import tarjetassvc

router = APIRouter(prefix="/tarjetas", tags=["Tarjetas"])


@router.get(
    "", response_model=list[TarjetaRespuesta],
    dependencies=[Depends(requiere_permiso("VER_TARJETA"))],
)
def listar_tarjetas(
    id_cliente: str | None = Query(default=None),
    estado: str | None = Query(default=None),
    limite: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(db_session),
):
    tarjetas = tarjetassvc.listar_tarjetas(
        db, id_cliente=id_cliente, estado=estado, limite=limite, offset=offset
    )
    return [TarjetaRespuesta(**tarjetassvc.vista_publica(t)) for t in tarjetas]


@router.get(
    "/{id_tarjeta}", response_model=TarjetaRespuesta,
    dependencies=[Depends(requiere_permiso("VER_TARJETA"))],
)
def ver_tarjeta(id_tarjeta: str, db: Session = Depends(db_session)):
    return TarjetaRespuesta(**tarjetassvc.vista_publica(tarjetassvc.obtener_tarjeta(db, id_tarjeta)))


@router.post("", response_model=TarjetaRespuesta, status_code=status.HTTP_201_CREATED)
def crear_tarjeta(
    payload: TarjetaCrear,
    db: Session = Depends(db_session),
    usuario: UsuarioSistema = Depends(requiere_permiso("CREAR_TARJETA")),
):
    tarjeta = tarjetassvc.emitir_tarjeta(
        db,
        id_cliente=payload.id_cliente,
        num_cuenta=payload.num_cuenta,
        tipo_tarjeta=payload.tipo_tarjeta,
        anios_vigencia=payload.anios_vigencia,
        es_principal=payload.es_principal,
        habilitada_atm=payload.habilitada_atm,
        actor=usuario.username,
        correlation_id=payload.correlation_id,
    )
    return TarjetaRespuesta(**tarjetassvc.vista_publica(tarjeta))


@router.post("/{id_tarjeta}/cambiar-estado", response_model=TarjetaRespuesta)
def cambiar_estado(
    id_tarjeta: str,
    payload: TarjetaEstadoCambiar,
    db: Session = Depends(db_session),
    usuario: UsuarioSistema = Depends(requiere_permiso("BLOQUEAR_TARJETA")),
):
    tarjeta = tarjetassvc.cambiar_estado_tarjeta(
        db,
        id_tarjeta,
        nuevo_estado=payload.estado_nuevo,
        motivo=payload.motivo,
        origen=payload.origen,
        actor=usuario.username,
        correlation_id=payload.correlation_id,
    )
    return TarjetaRespuesta(**tarjetassvc.vista_publica(tarjeta))
