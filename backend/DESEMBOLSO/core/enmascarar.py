"""Enmascarado de datos sensibles en respuestas, bitacora y registros (RT-07)."""


def enmascarar(valor: str | None, visibles: int = 4) -> str | None:
    if not valor:
        return valor
    return "****" + valor[-visibles:]
