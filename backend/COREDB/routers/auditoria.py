"""GET /coredb/auditoria: la bitácora general, de solo lectura."""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from COREDB.auth import requiere_permiso
from COREDB.database import db_session
from COREDB.models import EventoAuditoria

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
    db: Session = Depends(db_session),
):
    """Los eventos de la bitácora, del más reciente al más antiguo. Cada operación de la
    API deja el suyo con el usuario que la hizo. El detalle no lleva datos personales."""
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
    return consulta.order_by(EventoAuditoria.id_evento.desc()).limit(limite).all()
