"""Piezas comunes: errores de negocio, correlación, fechas UTC y formato de montos."""
from __future__ import annotations

import contextvars
import re
import uuid
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

CENTIMO = Decimal("0.01")
CUATRO_DECIMALES = Decimal("0.0001")
PATRON_CORRELACION = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")

_correlacion: contextvars.ContextVar[str] = contextvars.ContextVar("correlacion", default="")


class ErrorEva(Exception):
    """Error de negocio con estado HTTP. Se responde como {"error": {"code", "message"}}."""

    def __init__(self, estado: int, codigo: str, mensaje: str, detalle: dict | None = None):
        super().__init__(mensaje)
        self.estado = estado
        self.codigo = codigo
        self.mensaje = mensaje
        self.detalle = detalle


def correlacion_valida(valor: str | None) -> str:
    """La del llamante si cumple el formato de SOL; si no, una nueva."""
    if valor and PATRON_CORRELACION.fullmatch(valor):
        return valor
    return str(uuid.uuid4())


def fijar_correlacion(valor: str) -> contextvars.Token:
    return _correlacion.set(valor)


def restaurar_correlacion(token: contextvars.Token) -> None:
    _correlacion.reset(token)


def correlacion_actual() -> str:
    return _correlacion.get() or str(uuid.uuid4())


def utc_ahora() -> datetime:
    """Instante UTC sin zona, como lo guarda la base (time_zone = '+00:00')."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def a_utc(fecha: datetime) -> datetime:
    """Convierte una fecha con zona al formato de la base (UTC sin zona)."""
    if fecha.tzinfo is None:
        return fecha
    return fecha.astimezone(timezone.utc).replace(tzinfo=None)


def iso(fecha: datetime | None) -> str | None:
    if fecha is None:
        return None
    return fecha.replace(tzinfo=timezone.utc).isoformat()


def dinero(valor: Decimal | None) -> str | None:
    """Texto decimal con dos cifras ("500.00"), como el resto del producto. Nunca float."""
    if valor is None:
        return None
    return format(Decimal(valor).quantize(CENTIMO, rounding=ROUND_HALF_UP), "f")


def tasa(valor: Decimal) -> str:
    """Fracción con cuatro decimales, como la política de SOL: "0.2200" es 22 %."""
    return format(Decimal(valor).quantize(CUATRO_DECIMALES, rounding=ROUND_HALF_UP), "f")


def enmascarar(documento: str) -> str:
    return "****" + documento[-4:] if len(documento) > 4 else "****"
