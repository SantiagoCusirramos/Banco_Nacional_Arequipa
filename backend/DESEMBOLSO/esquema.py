"""Instala la base del módulo: sql/esquema.sql y el usuario de la aplicación con permisos mínimos.

Lo usan el contenedor de arranque (scripts/preparar_base.py) y las pruebas. Idempotente: no borra datos.
"""
from __future__ import annotations

import re
from pathlib import Path

BASE = "bna_desembolso"
USUARIO = "desembolso_user"
ARCHIVO = Path(__file__).resolve().parent / "sql" / "esquema.sql"

# Sin DELETE en ninguna tabla; bitácora y validaciones solo admiten INSERT (Modelo Referencial, sección 10).
PERMISOS: list[tuple[str, str]] = [
    ("SELECT, INSERT, UPDATE", "des_orden"),
    ("SELECT, INSERT", "des_validacion"),
    ("SELECT, INSERT, UPDATE", "des_evento_entrega"),
    ("SELECT, INSERT", "des_auditoria"),
    ("SELECT, INSERT, UPDATE", "des_solicitud_reversion"),
    ("SELECT, INSERT, UPDATE", "des_correlativo"),
    ("SELECT", "des_v_ordenes_inciertas"),
    ("SELECT", "des_v_entregas_pendientes"),
    ("SELECT", "des_v_conciliacion_diaria"),
]

_NOMBRE = re.compile(r"^[A-Za-z0-9_]{1,64}$")


def _validar(nombre: str) -> str:
    if not _NOMBRE.fullmatch(nombre):
        raise ValueError(f"Nombre no permitido: {nombre!r}")
    return nombre


def sentencias(texto: str) -> list[str]:
    """Separa un script con bloques DELIMITER como lo haría el cliente mysql."""
    delimitador, bloque, salida = ";", [], []
    for linea in texto.splitlines():
        limpia = linea.strip()
        if not bloque and (not limpia or limpia.startswith("--")):
            continue
        if limpia.upper().startswith("DELIMITER "):
            delimitador = limpia.split()[1]
            continue
        bloque.append(linea)
        if limpia.endswith(delimitador):
            sentencia = "\n".join(bloque).strip()[: -len(delimitador)].strip()
            if sentencia:
                salida.append(sentencia)
            bloque = []
    return salida


def instalar(cursor, base: str = BASE, usuario: str = USUARIO, clave: str | None = None, host: str = "%") -> None:
    """Crea o completa la base con un cursor administrativo (PyMySQL). Con `clave`, deja el usuario de la
    aplicación con sus permisos y nada más."""
    base, usuario = _validar(base), _validar(usuario)
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{base}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
    cursor.execute(f"USE `{base}`")
    for sentencia in sentencias(ARCHIVO.read_text(encoding="utf-8")):
        cursor.execute(sentencia)
    if clave is None:
        return
    cuenta = f"'{usuario}'@'{host}'"
    con_parametros = cuenta.replace("%", "%%")   # con parámetros, PyMySQL toma el % del host como formato
    cursor.execute(f"CREATE USER IF NOT EXISTS {con_parametros} IDENTIFIED BY %s", (clave,))
    cursor.execute(f"ALTER USER {con_parametros} IDENTIFIED BY %s", (clave,))
    cursor.execute(f"REVOKE ALL PRIVILEGES, GRANT OPTION FROM {cuenta}")
    for privilegios, objeto in PERMISOS:
        cursor.execute(f"GRANT {privilegios} ON `{base}`.`{objeto}` TO {cuenta}")
