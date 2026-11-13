"""Configuración del módulo de Clientes. Todas las direcciones y secretos vienen del entorno."""
from shared.comun import entorno

BUS_URL = entorno("BUS_URL").rstrip("/")  # mini-Bus hoy; Bus oficial mañana
BUS_TOKEN = entorno("BUS_TOKEN")  # credencial para llamar al Bus
RENIEC_URL = entorno("RENIEC_URL").rstrip("/")  # RENIEC es externo: Clientes lo llama directamente
RENIEC_SERVICE_TOKEN = entorno("RENIEC_SERVICE_TOKEN")
CLIENTES_TOKEN = entorno("CLIENTES_TOKEN")  # credencial que el Bus presenta para invocar /clientes/*
PANEL_USER = entorno("CLIENTES_PANEL_USER")
PANEL_PASSWORD = entorno("CLIENTES_PANEL_PASSWORD")
RENIEC_TIMEOUT_SEG = float(entorno("RENIEC_TIMEOUT_SEG", "15"))
BUS_TIMEOUT_SEG = float(entorno("BUS_TIMEOUT_SEG", "30"))
