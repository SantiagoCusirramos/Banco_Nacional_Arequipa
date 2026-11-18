"""Piezas comunes: errores y correlación."""
from __future__ import annotations

import contextvars
import re
import uuid

PATRON_CORRELACION = re.compile(r"^[A-Za-z0-9_.:-]{1,100}$")

_correlacion: contextvars.ContextVar[str] = contextvars.ContextVar("correlacion", default="")


class ErrorSeg(Exception):
    """Error con estado HTTP. Se responde como {"error": {"code", "message"}}."""

    def __init__(self, estado: int, codigo: str, mensaje: str):
        super().__init__(mensaje)
        self.estado = estado
        self.codigo = codigo
        self.mensaje = mensaje


def fijar_correlacion(valor: str) -> contextvars.Token:
    return _correlacion.set(valor)


def restaurar_correlacion(token: contextvars.Token) -> None:
    _correlacion.reset(token)


def correlacion_actual() -> str:
    return _correlacion.get() or str(uuid.uuid4())
