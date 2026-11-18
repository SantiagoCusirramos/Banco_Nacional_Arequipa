"""GET /coredb/auditoria: la bitácora general, de solo lectura, y sus sellos (bd-v1.13)."""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from COREDB.auth import Actor, requiere_permiso
from COREDB.database import db_session, llamar
from COREDB.models import EventoAuditoria, SelloAuditoria
from COREDB.permisos import OPERAR_SEGURIDAD
from COREDB.transacciones import con_reintentos

router = APIRouter(prefix="/coredb/auditoria", tags=["auditoría"])


class EventoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_evento: int
    modulo: str
    entidad: str
    id_entidad: str
    accion: str
    actor: str
    correlation_id: uuid.UUID | None
    detalle: dict[str, Any] | None
    fecha_hora: datetime


@router.get("", response_model=list[EventoRespuesta],
            dependencies=[Depends(requiere_permiso("VER_AUDITORIA"))])
def eventos(
    modulo: str | None = Query(default=None, max_length=40),
    entidad: str | None = Query(default=None, max_length=40),
    id_entidad: str | None = Query(default=None, max_length=40),
    accion: str | None = Query(default=None, max_length=60),
    actor: str | None = Query(default=None, max_length=40),
    correlation_id: uuid.UUID | None = None,
    limite: int = Query(default=50, ge=1, le=200),
    antes_de_id: int | None = Query(
        default=None, ge=1, description="Solo eventos con un id menor (para paginar)."
    ),
    despues_de_id: int | None = Query(
        default=None, ge=0,
        description="Solo eventos con un id mayor, del más antiguo al más reciente (para sellar).",
    ),
    db: Session = Depends(db_session),
):
    """Los eventos de la bitácora, del más reciente al más antiguo (con `despues_de_id`, al
    revés). Cada operación de la API deja el suyo con el usuario que la hizo. El detalle no
    lleva datos personales."""
    consulta = db.query(EventoAuditoria)
    filtros = {
        EventoAuditoria.modulo: modulo, EventoAuditoria.entidad: entidad,
        EventoAuditoria.id_entidad: id_entidad, EventoAuditoria.accion: accion,
        EventoAuditoria.actor: actor, EventoAuditoria.correlation_id: correlation_id,
    }
    for columna, valor in filtros.items():
        if valor is not None:
            consulta = consulta.filter(columna == valor)
    if antes_de_id is not None:
        consulta = consulta.filter(EventoAuditoria.id_evento < antes_de_id)
    if despues_de_id is not None:
        consulta = consulta.filter(EventoAuditoria.id_evento > despues_de_id)
        return consulta.order_by(EventoAuditoria.id_evento.asc()).limit(limite).all()
    return consulta.order_by(EventoAuditoria.id_evento.desc()).limit(limite).all()


class SelloCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hasta_evento: int = Field(ge=1, description="Último evento del tramo; el tramo empieza tras el último sello.")
    eventos: int = Field(ge=1, description="Cuántos eventos tiene el tramo, según quien lo selló.")
    hmac: str = Field(pattern=r"^[0-9a-f]{64}$", description="HMAC encadenado del tramo, con la clave de Seguridad.")


class SelloRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_sello: int
    desde_evento: int
    hasta_evento: int
    eventos: int
    hmac: str
    actor: str
    fecha_hora: datetime


@router.get("/sellos", response_model=list[SelloRespuesta],
            dependencies=[Depends(requiere_permiso("VER_AUDITORIA"))])
def sellos(
    despues_de_id: int = Query(default=0, ge=0, description="Solo sellos con un id mayor (para paginar)."),
    limite: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(db_session),
):
    """Los sellos de la bitácora, del más antiguo al más reciente. Cada uno cubre los eventos
    (desde_evento, hasta_evento] y encadena el HMAC del anterior."""
    return (db.query(SelloAuditoria).filter(SelloAuditoria.id_sello > despues_de_id)
            .order_by(SelloAuditoria.id_sello.asc()).limit(limite).all())


@router.post("/sellos", response_model=SelloRespuesta, status_code=status.HTTP_201_CREATED,
             responses={409: {"description": "BNA-SELLO: el tramo no sigue al último sello o no tiene esos eventos"}})
def sellar(
    datos: SelloCrear,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso(OPERAR_SEGURIDAD)),
):
    """Guarda el sello que calculó el módulo Seguridad (solo él, con OPERAR_SEGURIDAD). La base
    comprueba que el tramo sigue al último sello y que tiene los eventos declarados."""
    id_sello, _ = con_reintentos(
        db,
        lambda: llamar(db, "core.sellar_auditoria", datos.hasta_evento, datos.eventos, datos.hmac,
                       actor.usuario, salidas=2),
        nombre="sellar_auditoria",
    )
    db.expire_all()
    return db.get(SelloAuditoria, id_sello)
