"""Crea la base `bna_cobranza` y su usuario en la base auxiliar (db-aux), y termina.

Lo ejecuta `cobranza-init` en compose.yaml. Cobranza es un laboratorio con base propia, como SOL:
no toca la base integrada. Es idempotente y sirve también sobre un volumen de db-aux ya creado,
por eso no va en docker/db-aux/02_usuarios.sh (que solo corre al inicializar el volumen).
Las tablas las crea Cobranza al arrancar (COBRANZA.db.crear_esquema).

    python -m COBRANZA.scripts.preparar_base

Variables: COBRANZA_DB_HOST (db-aux), AUX_DB_ROOT_PASSWORD, COBRANZA_DB_PASSWORD.
"""

import os
import sys
import time

import pymysql

BASE = "bna_cobranza"
USUARIO = "cobranza_user"


def _conectar(host, password, intentos=60):
    for _ in range(intentos):
        try:
            return pymysql.connect(host=host, port=3306, user="root", password=password, autocommit=True)
        except pymysql.err.OperationalError:
            time.sleep(2)
    print(f"No se pudo conectar con {host}.", file=sys.stderr)
    sys.exit(1)


def main():
    host = os.environ.get("COBRANZA_DB_HOST", "db-aux")
    root = os.environ.get("AUX_DB_ROOT_PASSWORD")
    clave = os.environ.get("COBRANZA_DB_PASSWORD")
    if not root or not clave:
        print("Faltan AUX_DB_ROOT_PASSWORD o COBRANZA_DB_PASSWORD.", file=sys.stderr)
        return 1
    conexion = _conectar(host, root)
    with conexion.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{BASE}` CHARACTER SET utf8mb4")
        # Con parámetros, PyMySQL formatea la consulta con %: el host '%' se escribe '%%'.
        cur.execute(f"CREATE USER IF NOT EXISTS '{USUARIO}'@'%%' IDENTIFIED BY %s", (clave,))
        # Si .env cambió la clave, se alinea: el usuario solo existe para Cobranza.
        cur.execute(f"ALTER USER '{USUARIO}'@'%%' IDENTIFIED BY %s", (clave,))
        cur.execute(f"GRANT ALL PRIVILEGES ON `{BASE}`.* TO '{USUARIO}'@'%'")
    conexion.close()
    print(f"Base {BASE} y usuario {USUARIO} listos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
