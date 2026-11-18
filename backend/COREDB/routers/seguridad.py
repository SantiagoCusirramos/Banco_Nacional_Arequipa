"""Rutas del módulo Seguridad (bd-v1.13): evaluación de una operación con su desafío,
incidentes y desbloqueo de tarjetas. Los sellos de la bitácora están en auditoria.py.

Solo las usa el módulo Seguridad, con su usuario de servicio (OPERAR_SEGURIDAD), y siempre
por una persona: su token va en X-Persona-Token, COREDB comprueba el permiso de ella y la
registra como actor. Seguridad no tiene base propia; lo que guarda está en la base integrada.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from COREDB.auth import PersonaSeguridad, persona_por_seguridad
from COREDB.database import db_session, llamar, sesion_seguridad
from COREDB.errores import ErrorCoreDb
from COREDB.models import IncidenteSeguridad
from COREDB.permisos import GESTIONAR_INCIDENTES
from COREDB.routers.tarjetas import TarjetaRespuesta, _obtener
from COREDB.transacciones import con_reintentos

router = APIRouter(tags=["seguridad"])

Monto = Annotated[Decimal, Field(gt=0, max_digits=15, decimal_places=2)]
Canal = Annotated[str, Field(min_length=1, max_length=5, pattern=r"^[A-Z]+$")]
Cuenta = Annotated[str, Field(min_length=1, max_length=20)]
Hmac = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$",
                            description="HMAC-SHA256 del código en hexadecimal; la clave es de Seguridad.")]


# --------------------------------------------------------------------- evaluación
class EvaluacionPeticion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    uuid_operacion: uuid.UUID = Field(description="Lo genera quien llama (RN-BUS-002); repetirlo "
                                                  "devuelve la misma decisión.")
    num_cuenta: Cuenta
    canal: Canal = Field(description="Un canal de core.canal: ATM, HB, BD, VEN, AGE.")
    monto: Monto
    id_desafio: uuid.UUID | None = None
    hmac_codigo: Hmac | None = None

    @model_validator(mode="after")
    def _desafio_completo(self):
        if (self.id_desafio is None) != (self.hmac_codigo is None):
            raise ValueError("id_desafio y hmac_codigo van juntos")
        return self


class EvaluacionRespuesta(BaseModel):
    uuid_operacion: uuid.UUID
    decision: Literal["AUTORIZADA", "RECHAZADA", "DESAFIO_REQUERIDO", "DESAFIO_RECHAZADO"]
    motivo: Literal["CUENTA", "CANAL", "TOPE"] | None = None
    tope: Decimal | None = Field(description="Tope del día del canal; null si el canal no tiene.")
    consumido: Decimal | None = Field(description="Consumo real del día de la cuenta en el canal.")
    repetida: bool


@router.post("/coredb/seguridad/evaluaciones", response_model=EvaluacionRespuesta,
             responses={404: {"description": "BNA-CUENTA"}, 409: {"description": "BNA-IDEMPOTENCIA"}})
def evaluar(
    datos: EvaluacionPeticion,
    db: Session = Depends(db_session),
    quien: PersonaSeguridad = Depends(persona_por_seguridad("REGISTRAR_MOVIMIENTO")),
):
    """Evalúa una operación contra el tope real del canal y el consumo real del día. No mueve
    dinero. Sobre el 80 % del tope responde DESAFIO_REQUERIDO; con el desafío y el HMAC del
    código, AUTORIZADA o DESAFIO_RECHAZADO (el intento queda contado)."""
    decision, motivo, tope, consumido, repetida = con_reintentos(
        db,
        lambda: llamar(
            db, "core.evaluar_operacion",
            datos.uuid_operacion, datos.num_cuenta, datos.canal, datos.monto,
            datos.id_desafio, datos.hmac_codigo, quien.actor,
            salidas=5,
        ),
        nombre="evaluar_operacion",
    )
    return EvaluacionRespuesta(uuid_operacion=datos.uuid_operacion, decision=decision, motivo=motivo,
                               tope=tope, consumido=consumido, repetida=bool(repetida))


class DesafioPeticion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_desafio: uuid.UUID
    uuid_operacion: uuid.UUID
    num_cuenta: Cuenta
    canal: Canal
    monto: Monto
    hmac_codigo: Hmac


class DesafioRespuesta(BaseModel):
    id_desafio: uuid.UUID
    vence_en: datetime


@router.post("/coredb/seguridad/desafios", response_model=DesafioRespuesta, status_code=status.HTTP_201_CREATED,
             responses={409: {"description": "BNA-DESAFIO: la operación ya tiene una decisión"}})
def crear_desafio(
    datos: DesafioPeticion,
    db: Session = Depends(db_session),
    quien: PersonaSeguridad = Depends(persona_por_seguridad("REGISTRAR_MOVIMIENTO")),
):
    """Guarda el desafío ligado a la operación con el HMAC de su código. Vence a los 120 s y
    tres fallos lo agotan. COREDB nunca recibe el código."""
    (vence_en,) = con_reintentos(
        db,
        lambda: llamar(
            db, "core.crear_desafio",
            datos.id_desafio, datos.uuid_operacion, datos.num_cuenta, datos.canal, datos.monto,
            datos.hmac_codigo, quien.actor,
            salidas=1,
        ),
        nombre="crear_desafio",
    )
    return DesafioRespuesta(id_desafio=datos.id_desafio, vence_en=vence_en)


# --------------------------------------------------------------------- incidentes
class IncidenteCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prioridad: Literal["P1", "P2", "P3", "P4"]
    titulo: str = Field(min_length=8, max_length=200)


class IncidenteAvanzar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estado: Literal["EN_PROGRESO", "RESUELTO", "CERRADO"]
    resolucion: str | None = Field(default=None, min_length=8, max_length=500)


class IncidenteRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_incidente: uuid.UUID
    prioridad: str
    titulo: str
    estado: str
    resolucion: str | None
    abierto_por: str
    creado_en: datetime
    actualizado_en: datetime


def _incidente(db: Session, id_incidente: uuid.UUID) -> IncidenteSeguridad:
    db.expire_all()
    incidente = db.get(IncidenteSeguridad, str(id_incidente))
    if incidente is None:
        raise ErrorCoreDb("INCIDENTE_NO_ENCONTRADO", "El incidente no existe.", 404)
    return incidente


@router.get("/coredb/seguridad/incidentes", response_model=list[IncidenteRespuesta])
def incidentes(
    limite: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(db_session),
    quien: PersonaSeguridad = Depends(persona_por_seguridad("VER_AUDITORIA", GESTIONAR_INCIDENTES)),
):
    """Los incidentes, del más reciente al más antiguo."""
    return (db.query(IncidenteSeguridad).order_by(IncidenteSeguridad.creado_en.desc())
            .limit(limite).all())


@router.post("/coredb/seguridad/incidentes", response_model=IncidenteRespuesta,
             status_code=status.HTTP_201_CREATED)
def abrir_incidente(
    datos: IncidenteCrear,
    db: Session = Depends(db_session),
    quien: PersonaSeguridad = Depends(persona_por_seguridad(GESTIONAR_INCIDENTES)),
):
    id_incidente = uuid.uuid4()
    con_reintentos(
        db,
        lambda: llamar(db, "core.abrir_incidente", id_incidente, datos.prioridad, datos.titulo, quien.actor),
        nombre="abrir_incidente",
    )
    return _incidente(db, id_incidente)


@router.post("/coredb/seguridad/incidentes/{id_incidente}/estado", response_model=IncidenteRespuesta,
             responses={404: {"description": "INCIDENTE_NO_ENCONTRADO"},
                        409: {"description": "BNA-INCIDENTE-TRANSICION"}})
def avanzar_incidente(
    id_incidente: uuid.UUID,
    datos: IncidenteAvanzar,
    db: Session = Depends(db_session),
    quien: PersonaSeguridad = Depends(persona_por_seguridad(GESTIONAR_INCIDENTES)),
):
    """ABIERTO → EN_PROGRESO → RESUELTO (exige la resolución) → CERRADO, sin saltos."""
    _incidente(db, id_incidente)
    db.rollback()
    con_reintentos(
        db,
        lambda: llamar(db, "core.avanzar_incidente", id_incidente, datos.estado, datos.resolucion, quien.actor),
        nombre="avanzar_incidente",
    )
    return _incidente(db, id_incidente)


# --------------------------------------------------------------------- desbloqueo de tarjetas
class DesbloqueoPeticion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: str = Field(min_length=3, max_length=255)


@router.post("/coredb/tarjetas/{id_tarjeta}/desbloqueo", response_model=TarjetaRespuesta,
             responses={404: {"description": "TARJETA_NO_ENCONTRADA"},
                        409: {"description": "TARJETA_NO_BLOQUEADA"},
                        503: {"description": "SEGURIDAD_NO_CONFIGURADA"}})
def desbloquear_tarjeta(
    id_tarjeta: uuid.UUID,
    datos: DesbloqueoPeticion,
    db: Session = Depends(db_session),
    quien: PersonaSeguridad = Depends(persona_por_seguridad("BLOQUEAR_TARJETA")),
):
    """Devuelve a ACTIVA una tarjeta BLOQUEADA o RETENIDA, con origen SEGURIDAD. La base solo lo
    permite al rol bna_seguridad: esta ruta usa esa cuenta y nada más. El actor es la persona."""
    _obtener(db, id_tarjeta)
    db.rollback()  # la lectura de después no debe ver la instantánea de antes del cambio
    sesion = sesion_seguridad()
    try:
        con_reintentos(
            sesion,
            lambda: llamar(sesion, "tarjetas.desbloquear_tarjeta", id_tarjeta, datos.motivo, quien.actor,
                           salidas=1),
            nombre="desbloquear_tarjeta",
        )
    except ErrorCoreDb as exc:
        if exc.code == "BNA-DESBLOQUEO":
            raise ErrorCoreDb("TARJETA_NO_BLOQUEADA", "La tarjeta no está bloqueada.", 409) from None
        raise
    finally:
        sesion.close()
    db.expire_all()
    return _obtener(db, id_tarjeta)
