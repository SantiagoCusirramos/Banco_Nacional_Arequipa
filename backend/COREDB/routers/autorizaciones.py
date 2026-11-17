"""Autorizaciones de operaciones con tarjeta, su extorno y confirmación (bd-v1.8).

Las reglas (tarjeta operativa y vigente, canal, saldo, tope diario, cajero) las aplica la
base. Una regla que no se cumple no es un error de la petición: la autorización queda
RECHAZADA con su código de respuesta y se devuelve con 201, como la aprobada.
"""

import ipaddress
import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from COREDB.auth import Actor, requiere_permiso
from COREDB.database import db_session, llamar
from COREDB.errores import ErrorCoreDb
from COREDB.models import Autorizacion
from COREDB.transacciones import con_reintentos

router = APIRouter(prefix="/coredb/autorizaciones", tags=["tarjetas"])

Monto = Annotated[Decimal, Field(gt=0, max_digits=15, decimal_places=2)]


class AutorizacionRegistrar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    uuid_autorizacion: uuid.UUID = Field(
        description="Lo genera quien llama (RN-BUS-002). Repetirlo con los mismos datos "
                    "devuelve la autorización ya registrada; con otros datos, 409 BNA-IDEMPOTENCIA.",
    )
    id_tarjeta: uuid.UUID
    num_cuenta: str = Field(min_length=1, max_length=20)
    tipo_operacion: str = Field(min_length=1, max_length=25, pattern=r"^[A-Z_]+$")
    monto: Monto
    id_canal: str | None = Field(default=None, min_length=1, max_length=5)
    id_terminal: str | None = Field(default=None, min_length=1, max_length=30)

    @model_validator(mode="after")
    def _canal_o_terminal(self):
        if (self.id_canal is None) == (self.id_terminal is None):
            raise ValueError("Se indica el canal o la terminal, uno de los dos.")
        return self


class ExtornoRegistrar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: str = Field(min_length=1, max_length=255)


class ConfirmacionRegistrar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    llave_idempotencia: str = Field(min_length=1, max_length=64)
    huella: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    id_canal: str | None = Field(default=None, min_length=1, max_length=5)
    id_terminal: str | None = Field(default=None, min_length=1, max_length=30)

    @model_validator(mode="after")
    def _canal_o_terminal(self):
        if self.id_canal is None and self.id_terminal is None:
            raise ValueError("Se indica el canal o la terminal (o ambos).")
        return self


class AutorizacionRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid_autorizacion: uuid.UUID
    id_tarjeta: uuid.UUID
    num_cuenta: str
    id_canal: str | None
    id_terminal: str | None
    tipo_operacion: str
    monto: Decimal
    estado_autorizacion: str
    codigo_respuesta: str | None = Field(
        description="ISO 8583: 00 aprobada, 51 sin fondos, 54 vencida, 57 no permitida, "
                    "61 excede el tope, 62 restringida, EXT extornada.",
    )
    motivo_rechazo: str | None
    uuid_transaccion: uuid.UUID | None


def ip_origen(request: Request) -> str | None:
    # La base exige una IP válida; el cliente de pruebas no la tiene.
    host = request.client.host if request.client else None
    try:
        return str(ipaddress.ip_address(host)) if host else None
    except ValueError:
        return None


def _obtener(db: Session, uuid_autorizacion: uuid.UUID) -> Autorizacion:
    autorizacion = db.get(Autorizacion, uuid_autorizacion)
    if autorizacion is None:
        raise ErrorCoreDb(
            "AUTORIZACION_NO_ENCONTRADA", f"La autorización {uuid_autorizacion} no existe.", 404
        )
    return autorizacion


@router.post("", response_model=AutorizacionRespuesta, status_code=status.HTTP_201_CREATED,
             responses={409: {"description": "BNA-IDEMPOTENCIA"},
                        422: {"description": "BNA-TARJETA, BNA-MONTO"}})
def autorizar(
    datos: AutorizacionRegistrar,
    request: Request,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("REGISTRAR_MOVIMIENTO")),
):
    """Autoriza la operación o registra su rechazo. Si se aprueba, retiene el monto del saldo
    disponible y lo suma al consumo del día del canal hasta que se contabilice o se extorne."""
    con_reintentos(
        db,
        lambda: llamar(
            db, "tarjetas.autorizar_operacion",
            datos.uuid_autorizacion, datos.id_tarjeta, datos.num_cuenta, datos.id_canal,
            datos.id_terminal, datos.tipo_operacion, datos.monto, ip_origen(request),
            actor.usuario,
            salidas=2,
        ),
        nombre="autorizar_operacion",
    )
    return _obtener(db, datos.uuid_autorizacion)


@router.get("/{uuid_autorizacion}", response_model=AutorizacionRespuesta,
            dependencies=[Depends(requiere_permiso("VER_TARJETA"))])
def ver(uuid_autorizacion: uuid.UUID, db: Session = Depends(db_session)):
    return _obtener(db, uuid_autorizacion)


@router.post("/{uuid_autorizacion}/extorno", response_model=AutorizacionRespuesta,
             responses={404: {"description": "BNA-AUTORIZACION"},
                        409: {"description": "BNA-EXTORNO"}})
def extornar(
    uuid_autorizacion: uuid.UUID,
    datos: ExtornoRegistrar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("REGISTRAR_MOVIMIENTO")),
):
    """Extorna una autorización que aún no tiene movimiento y libera el saldo y el tope
    (RN-ATM-003). Repetirlo responde lo mismo sin cambiar nada."""
    con_reintentos(
        db,
        lambda: llamar(
            db, "tarjetas.extornar_autorizacion",
            uuid_autorizacion, datos.motivo, actor.usuario,
            salidas=1,
        ),
        nombre="extornar_autorizacion",
    )
    return _obtener(db, uuid_autorizacion)


@router.post("/{uuid_autorizacion}/confirmacion", response_model=AutorizacionRespuesta,
              responses={404: {"description": "BNA-AUTORIZACION"},
                         409: {"description": "BNA-CONFIRMACION, BNA-IDEMPOTENCIA"},
                         422: {"description": "BNA-CONFIRMACION"}})
def confirmar(
    uuid_autorizacion: uuid.UUID,
    datos: ConfirmacionRegistrar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("REGISTRAR_MOVIMIENTO")),
):
    """Confirma una autorización retenida: registra el movimiento real y pasa a DISPENSADA.
    La llave de idempotencia es obligatoria; repetirla devuelve el mismo resultado sin
    segundo débito. El canal o terminal deben coincidir con la autorización."""
    con_reintentos(
        db,
        lambda: llamar(
            db, "tarjetas.confirmar_autorizacion",
            uuid_autorizacion, datos.llave_idempotencia, datos.huella, actor.usuario,
            datos.id_canal, datos.id_terminal,
            salidas=2,
        ),
        nombre="confirmar_autorizacion",
    )
    return _obtener(db, uuid_autorizacion)
