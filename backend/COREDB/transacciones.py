"""Transacción con reintentos, portada de CORE/services/movimientos.py (Hallazgo #10)."""

import logging
import random
import time
from collections.abc import Callable
from typing import TypeVar

from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from COREDB.errores import ErrorBaseDatos, ErrorCoreDb

logger = logging.getLogger(__name__)

T = TypeVar("T")

MAX_INTENTOS = 5
BACKOFF_BASE_SEGUNDOS = 0.05
BACKOFF_MAX_SEGUNDOS = 1.0


def _espera(intento: int) -> float:
    """Backoff exponencial con jitter, para que dos víctimas no reintenten a la vez."""
    base = min(BACKOFF_MAX_SEGUNDOS, BACKOFF_BASE_SEGUNDOS * (2 ** (intento - 1)))
    return base / 2 + random.uniform(0, base / 2)


def con_reintentos(db: Session, operacion: Callable[[], T], *, nombre: str) -> T:
    """Ejecuta `operacion` y confirma. MySQL revierte toda la transacción víctima de
    un deadlock, por eso es seguro repetirla desde el inicio."""
    for intento in range(1, MAX_INTENTOS + 1):
        try:
            resultado = operacion()
            db.commit()
            return resultado
        except DBAPIError as exc:
            db.rollback()
            if not ErrorBaseDatos.es_reintentable(exc):
                raise
            if intento >= MAX_INTENTOS:
                logger.error("Reintentos agotados en %s.", nombre)
                raise ErrorCoreDb(
                    "CONFLICTO_CONCURRENCIA",
                    "La operación no pudo completarse por concurrencia; reintente.",
                    503,
                ) from exc
            time.sleep(_espera(intento))
    raise AssertionError("inalcanzable")  # pragma: no cover
