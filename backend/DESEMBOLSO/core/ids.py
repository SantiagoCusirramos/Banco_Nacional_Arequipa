"""Identificadores UUID v7 (ordenables por tiempo), convencion de la base BNA."""
import os
import time
import uuid


def uuid7() -> str:
    milisegundos = time.time_ns() // 1_000_000
    aleatorio = int.from_bytes(os.urandom(10), "big")
    rand_a = (aleatorio >> 62) & 0xFFF
    rand_b = aleatorio & ((1 << 62) - 1)
    valor = (milisegundos & ((1 << 48) - 1)) << 80 | 0x7 << 76 | rand_a << 64 | 0b10 << 62 | rand_b
    return str(uuid.UUID(int=valor))
