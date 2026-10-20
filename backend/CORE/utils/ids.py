"""Generación de identificadores UUID v7 (RFC 9562).

El esquema del BNA almacena todos los IDs como CHAR(36) con UUID v7
(ordenables por tiempo). La aplicación —CORE— genera los v7; la base
solo los genera en triggers/procedimientos (ver fn_uuid_v7).

Python 3.14+ trae uuid.uuid7 en la librería estándar; en versiones
anteriores se usa esta implementación equivalente.
"""

import time
import uuid

try:  # Python 3.14+
    from uuid import uuid7 as _stdlib_uuid7
except ImportError:  # pragma: no cover - cubierto en 3.11/3.12
    _stdlib_uuid7 = None


def _uuid7_manual() -> uuid.UUID:
    ms = int(time.time() * 1000)
    rand = uuid.uuid4().bytes  # 16 bytes de entropía
    b = bytearray(16)
    b[0:6] = ms.to_bytes(6, "big")
    b[6] = ((ms >> 40) & 0x0F) | 0x70  # version 7
    b[7] = rand[7] & 0x3F | 0x80       # variant RFC 4122
    b[8:16] = rand[8:16]
    return uuid.UUID(bytes=bytes(b))


def new_uuid7() -> str:
    """Devuelve un UUID v7 como string con formato canónico (CHAR(36))."""
    if _stdlib_uuid7 is not None:
        return str(_stdlib_uuid7())
    return str(_uuid7_manual())
