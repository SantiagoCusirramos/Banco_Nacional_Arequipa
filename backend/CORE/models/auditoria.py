"""Log de auditoría de solo adición (script 01, RF-COR-19 / RNF-11).

CORE solo expone inserción y consulta: no existe endpoint de
modificación ni eliminación. El detalle JSON nunca contiene datos
sensibles (claves, PAN, biométricos).
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from CORE.database import Base


class AuditoriaEvento(Base):
    __tablename__ = "auditoria_evento"

    id_evento: Mapped[str] = mapped_column(String(36), primary_key=True)
    modulo: Mapped[str] = mapped_column(String(20))
    entidad: Mapped[str] = mapped_column(String(40))
    id_entidad: Mapped[str] = mapped_column(String(40))
    accion: Mapped[str] = mapped_column(String(40))
    actor: Mapped[str] = mapped_column(String(40))
    detalle: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(3))
