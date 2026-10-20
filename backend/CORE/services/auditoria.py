"""Servicios de auditoría (RF-COR-19 / RGN-20).

Toda operación registrada por CORE deja un evento en
auditoria_evento: canal, marca de tiempo, correlation_id y resultado.
Solo adición: aquí no hay update ni delete.
"""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from CORE.models import AuditoriaEvento
from CORE.utils.ids import new_uuid7


def registrar_evento(
    db: Session,
    *,
    modulo: str,
    entidad: str,
    id_entidad: str,
    accion: str,
    actor: str,
    detalle: dict[str, Any] | None = None,
    correlation_id: str | None = None,
    fecha_hora: datetime | None = None,
) -> AuditoriaEvento:
    evento = AuditoriaEvento(
        id_evento=new_uuid7(),
        modulo=modulo,
        entidad=entidad,
        id_entidad=id_entidad,
        accion=accion,
        actor=actor,
        detalle=detalle,
        correlation_id=correlation_id,
        fecha_hora=fecha_hora or datetime.now(),
    )
    db.add(evento)
    return evento
