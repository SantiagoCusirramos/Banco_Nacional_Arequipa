"""Fechas de negocio en hora de Arequipa (UTC-5, sin horario de verano)."""
from datetime import datetime, timedelta, timezone

LIMA = timezone(timedelta(hours=-5))


def ahora_lima() -> datetime:
    return datetime.now(LIMA).replace(tzinfo=None, microsecond=0)


def desde_iso(valor: str | None) -> datetime | None:
    if not valor:
        return None
    fecha = datetime.fromisoformat(valor)
    if fecha.tzinfo is not None:
        fecha = fecha.astimezone(LIMA).replace(tzinfo=None)
    return fecha


def hoy_lima():
    """Fecha de negocio en Arequipa."""
    return datetime.now(LIMA).date()
