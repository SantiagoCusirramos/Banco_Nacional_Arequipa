#!/usr/bin/env python3
"""Crea el archivo .env con claves aleatorias (solo librería estándar).  Uso: python scripts/generar_env.py [--forzar]"""
import secrets
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
destino = RAIZ / ".env"
if destino.exists() and "--forzar" not in sys.argv:
    sys.exit(f"{destino} ya existe. Use --forzar para reemplazarlo (se perderán sus claves actuales).")

claves = {k: secrets.token_urlsafe(18) for k in (
    "MYSQL_ROOT_PASSWORD", "MYSQL_PASSWORD", "BUS_TOKEN", "CLIENTES_TOKEN", "CORE_TOKEN", "RENIEC_SERVICE_TOKEN",
    "RENIEC_ADMIN_PASSWORD", "CLIENTES_PANEL_PASSWORD")}  # token_urlsafe solo usa letras, números, - y _

lineas = []
for linea in (RAIZ / ".env.example").read_text(encoding="utf-8").splitlines():
    nombre = linea.split("=", 1)[0].strip()
    if nombre in claves and "=" in linea:
        linea = f"{nombre}={claves[nombre]}"
    lineas.append(linea)
destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
destino.chmod(0o600)
print(f"Creado {destino}\n")
print("Acceso a las interfaces (guárdelo):")
print(f"  Panel de Clientes  http://localhost:8001   usuario: panel   clave: {claves['CLIENTES_PANEL_PASSWORD']}")
print(f"  Admin de RENIEC    http://localhost:8002   usuario: admin   clave: {claves['RENIEC_ADMIN_PASSWORD']}")
