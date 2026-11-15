"""Crea o completa la base de Evaluación en db-aux, y termina. No borra datos.

Tablas, triggers y el usuario de la aplicación con permisos mínimos (EVALUACION/esquema.py).
Lo ejecuta `evaluacion-init` en compose.yaml antes de levantar Evaluación. Como es idempotente,
sirve también sobre un volumen de db-aux ya creado.

    python -m EVALUACION.scripts.preparar_base          # aplica el esquema
    python -m EVALUACION.scripts.preparar_base --sql    # solo imprime el SQL

Variables: EVALUACION_DB_HOST (db-aux), EVALUACION_DB_PORT (3306), AUX_DB_ROOT_PASSWORD,
EVALUACION_DB_PASSWORD, EVALUACION_DB_NAME (bna_evaluacion), EVALUACION_DB_USER (evaluacion_user).
"""
from __future__ import annotations

import os
import sys
import time

import pymysql

from EVALUACION import esquema


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
    base = os.environ.get("EVALUACION_DB_NAME", esquema.BASE)
    usuario = os.environ.get("EVALUACION_DB_USER", esquema.USUARIO)
    if "--sql" in sys.argv[1:]:
        print(";\n\n".join(esquema.sentencias(base, usuario)) + ";")
        return 0
    raiz = os.environ.get("AUX_DB_ROOT_PASSWORD")
    clave = os.environ.get("EVALUACION_DB_PASSWORD")
    if not raiz or not clave:
        print("Faltan AUX_DB_ROOT_PASSWORD o EVALUACION_DB_PASSWORD.", file=sys.stderr)
        return 1
    conexion = _conectar(os.environ.get("EVALUACION_DB_HOST", "db-aux"),
                         int(os.environ.get("EVALUACION_DB_PORT", "3306")), raiz)
    with conexion.cursor() as cursor:
        esquema.instalar(cursor, base, usuario, clave)
    conexion.close()
    print(f"Base {base} y usuario {usuario} listos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
