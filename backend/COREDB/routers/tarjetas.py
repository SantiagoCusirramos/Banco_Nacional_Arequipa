import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from COREDB.auth import Actor, requiere_permiso
from COREDB.database import db_session, llamar
from COREDB.errores import ErrorCoreDb
from COREDB.models import EquivalenciaCatalogo, Tarjeta
from COREDB.services import clientes
from COREDB.transacciones import con_reintentos

router = APIRouter(prefix="/coredb/tarjetas", tags=["tarjetas"])


class TarjetaEmitir(BaseModel):
    id_tarjeta: uuid.UUID | None = Field(
        default=None,
        description="Opcional. Con el mismo id, una segunda emisión responde 409 en lugar de "
                    "emitir otra tarjeta: así la repite sin duplicarla quien deriva el id de su "
                    "llave de idempotencia.",
    )
    pan_token: str = Field(min_length=1, max_length=32)
    bin: str = Field(pattern=r"^[0-9]{6}$")
    ultimos4: str = Field(pattern=r"^[0-9]{4}$")
    fecha_emision: date
    fecha_vencimiento: date
    cod_cliente: str = Field(max_length=12)
    num_cuenta: str = Field(max_length=20)


class EstadoCambiar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estado: str = Field(max_length=25)
    motivo: str | None = Field(default=None, max_length=255)


class TarjetaRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_tarjeta: uuid.UUID
    bin: str
    ultimos4: str
    fecha_emision: date
    fecha_vencimiento: date
    estado_tarjeta: str
    cod_cliente: str
    num_cuenta: str | None = Field(
        default=None,
        description="La cuenta principal de la tarjeta, la de su emisión. Null si no tiene.",
    )


def _obtener(db: Session, id_tarjeta: uuid.UUID) -> Tarjeta:
    tarjeta = db.get(Tarjeta, id_tarjeta)
    if tarjeta is None:
        raise ErrorCoreDb("TARJETA_NO_ENCONTRADA", f"La tarjeta {id_tarjeta} no existe.", 404)
    return tarjeta


def _traducir(db: Session, catalogo: str, valor: str) -> str:
    """Un valor sin equivalente exacto se envía tal cual y la base lo rechaza."""
    equivalencia = db.get(EquivalenciaCatalogo, (catalogo, valor))
    return equivalencia.valor_bd if equivalencia else valor


def aplicar_cambio_estado(
    db: Session, id_tarjeta: uuid.UUID, estado: str, motivo: str | None, origen: str, actor: str
) -> None:
    con_reintentos(
        db,
        lambda: llamar(
            db, "tarjetas.cambiar_estado_tarjeta",
            id_tarjeta,
            _traducir(db, "estado_tarjeta", estado),
            motivo,
            origen,
            actor,
            salidas=1,
        ),
        nombre="cambiar_estado_tarjeta",
    )


@router.get("", response_model=list[TarjetaRespuesta],
            dependencies=[Depends(requiere_permiso("VER_TARJETA"))],
            responses={404: {"description": "CLIENTE_NO_ENCONTRADO"}})
def de_un_cliente(
    cod_cliente: str = Query(min_length=1, max_length=12, pattern=r"^[A-Za-z0-9]+$"),
    db: Session = Depends(db_session),
):
    """Las tarjetas del cliente, de la más reciente a la más antigua. No hay una ruta que
    liste todas las tarjetas."""
    clientes.consultar(db, cod_cliente)  # 404 si el cliente no existe
    return (
        db.query(Tarjeta)
        .filter(Tarjeta.cod_cliente == cod_cliente)
        .order_by(Tarjeta.fecha_emision.desc(), Tarjeta.id_tarjeta)
        .all()
    )


@router.get("/{id_tarjeta}", response_model=TarjetaRespuesta,
            dependencies=[Depends(requiere_permiso("VER_TARJETA"))])
def ver(id_tarjeta: uuid.UUID, db: Session = Depends(db_session)):
    return _obtener(db, id_tarjeta)


@router.post("", response_model=TarjetaRespuesta, status_code=status.HTTP_201_CREATED)
def emitir(
    datos: TarjetaEmitir,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("CREAR_TARJETA")),
):
    id_tarjeta = datos.id_tarjeta or uuid.uuid4()
    con_reintentos(
        db,
        lambda: llamar(
            db, "tarjetas.emitir_tarjeta",
            id_tarjeta, datos.pan_token, datos.bin, datos.ultimos4, datos.fecha_emision,
            datos.fecha_vencimiento, datos.cod_cliente, datos.num_cuenta, actor.usuario,
        ),
        nombre="emitir_tarjeta",
    )
    return _obtener(db, id_tarjeta)


@router.post("/{id_tarjeta}/estado", response_model=TarjetaRespuesta)
def cambiar_estado(
    id_tarjeta: uuid.UUID,
    datos: EstadoCambiar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("BLOQUEAR_TARJETA")),
):
    """Cambia el estado de una tarjeta. El origen viene del token, no de la petición. El
    desbloqueo no está disponible: pendiente de un cliente de Seguridad (403 BNA-DESBLOQUEO)."""
    tarjeta = _obtener(db, id_tarjeta)
    aplicar_cambio_estado(
        db, id_tarjeta, datos.estado, datos.motivo, actor.origen, actor.usuario
    )
    db.refresh(tarjeta)
    return tarjeta
