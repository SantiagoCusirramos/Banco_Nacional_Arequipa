"""Piezas comunes: errores de negocio y correlación."""
from __future__ import annotations

import contextvars
import re
import uuid

PATRON_CORRELACION = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")

_correlacion: contextvars.ContextVar[str] = contextvars.ContextVar("correlacion", default="")


class ErrorEva(Exception):
    """Error de negocio con estado HTTP. Se responde como {"error": {"code", "message"}}."""

    def __init__(self, estado: int, codigo: str, mensaje: str):
        super().__init__(mensaje)
        self.estado = estado
        self.codigo = codigo
        self.mensaje = mensaje


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
