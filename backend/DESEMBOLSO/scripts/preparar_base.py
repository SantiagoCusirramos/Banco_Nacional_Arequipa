"""Crea o completa la base de Desembolso en db-aux, y termina. No borra datos.

Tablas, triggers, vistas (sql/esquema.sql) y el usuario de la aplicación con permisos mínimos. Lo
ejecuta `desembolso-init` en compose.yaml; sirve también sobre un volumen de db-aux ya creado.

    python -m DESEMBOLSO.scripts.preparar_base

Variables: DESEMBOLSO_DB_HOST (db-aux), DESEMBOLSO_DB_PORT (3306), AUX_DB_ROOT_PASSWORD,
DESEMBOLSO_DB_PASSWORD, DESEMBOLSO_DB_NAME (bna_desembolso), DESEMBOLSO_DB_USER (desembolso_user).
"""
from __future__ import annotations

import os
import sys
import time

import pymysql

from DESEMBOLSO import esquema


def _conectar(host: str, puerto: int, clave: str, intentos: int = 60):
    for _ in range(intentos):
        try:
            return pymysql.connect(host=host, port=puerto, user="root", password=clave, autocommit=True,
                                   charset="utf8mb4")
        except pymysql.err.OperationalError:
            time.sleep(2)
    print(f"No se pudo conectar con {host}:{puerto}.", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    raiz = os.environ.get("AUX_DB_ROOT_PASSWORD")
    clave = os.environ.get("DESEMBOLSO_DB_PASSWORD")
    if not raiz or not clave:
        print("Faltan AUX_DB_ROOT_PASSWORD o DESEMBOLSO_DB_PASSWORD.", file=sys.stderr)
        return 1
    base = os.environ.get("DESEMBOLSO_DB_NAME", esquema.BASE)
    usuario = os.environ.get("DESEMBOLSO_DB_USER", esquema.USUARIO)
    conexion = _conectar(os.environ.get("DESEMBOLSO_DB_HOST", "db-aux"),
                         int(os.environ.get("DESEMBOLSO_DB_PORT", "3306")), raiz)
    with conexion.cursor() as cursor:
        esquema.instalar(cursor, base, usuario, clave)
    conexion.close()
    print(f"Base {base} y usuario {usuario} listos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
