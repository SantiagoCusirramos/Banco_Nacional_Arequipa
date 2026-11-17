"""Arranque del Bus de Servicios: uvicorn BUS_SERVICIOS.main:app --port 8018.

La configuración sale del entorno (ver README.md). Si falta algo, no arranca."""

import logging
import os

from BUS_SERVICIOS.config import cargar
from BUS_SERVICIOS.proxy import crear_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = crear_app(cargar(os.environ))
