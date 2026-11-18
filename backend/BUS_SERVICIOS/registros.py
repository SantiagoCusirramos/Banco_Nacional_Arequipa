"""Registros del Bus sin datos personales (P-1).

Por el Bus pasan búsquedas, documentos, celulares y tokens. Su propia línea solo lleva
metadatos (ver proxy.py); además:
- httpx y httpcore escriben la URL completa de cada reenvío en INFO: quedan en WARNING.
- la línea de acceso de uvicorn conserva la ruta pero no la consulta.
"""

import logging


class SinConsulta(logging.Filter):
    """Quita la consulta de la línea de acceso de uvicorn (cliente, método, ruta, versión, estado)."""

    def filter(self, record):
        if not isinstance(record.args, tuple) or len(record.args) != 5:
            return False  # un formato que no se conoce no se escribe
        cliente, metodo, ruta, version, estado = record.args
        if not isinstance(ruta, str):
            return False
        record.args = (cliente, metodo, ruta.split("?", 1)[0], version, estado)
        return True


def proteger():
    """Aplica las dos reglas y devuelve una función que quita el filtro de acceso."""
    for nombre in ("httpx", "httpcore"):
        logging.getLogger(nombre).setLevel(logging.WARNING)
    acceso = logging.getLogger("uvicorn.access")
    filtro = SinConsulta()
    acceso.addFilter(filtro)
    return lambda: acceso.removeFilter(filtro)
