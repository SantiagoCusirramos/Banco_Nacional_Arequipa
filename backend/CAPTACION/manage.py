"""Preparación de CAPTACION antes de arrancar. Uso: python -m CAPTACION.manage init

Hace tres cosas y termina; se puede repetir sin borrar datos:
1. Crea la base `bna_captacion` y su usuario en la base auxiliar (db-aux), con la
   cuenta root de esa base (AUX_DB_ROOT_PASSWORD). La base integrada no se toca.
2. Crea las tablas de CAPTACION con su propio usuario.
3. Con el administrador de COREDB crea el usuario de servicio de CAPTACION (rol
   SERVICIO, módulo CLIENTES), o le renueva el secreto si ya existe, y escribe el
   secreto en CAP_CORE_SECRETO_ARCHIVO. Es el procedimiento de CONTRATO_CLIENTES.md,
   sección 2: el secreto solo se ve una vez, así que se renueva en cada arranque.
"""

import os
import sys
import time
from pathlib import Path

import httpx
import pymysql

from CAPTACION import database
from CAPTACION.config import settings

ESPERA = int(os.environ.get("CAP_ESPERA_SEGUNDOS", "300"))


def _reintentar(nombre: str, accion):
    limite = time.monotonic() + ESPERA
    while True:
        try:
            return accion()
        except Exception as exc:  # noqa: BLE001 - se reintenta hasta el plazo
            if time.monotonic() > limite:
                raise SystemExit(f"{nombre}: no se pudo completar ({type(exc).__name__}).") from None
            time.sleep(3)


def preparar_base() -> None:
    root = os.environ.get("AUX_DB_ROOT_PASSWORD", "")
    if not root:
        print("Sin AUX_DB_ROOT_PASSWORD: se asume que la base y su usuario ya existen.")
        return
    if not settings.cap_db_password:
        raise SystemExit("Falta CAP_DB_PASSWORD.")

    def crear():
        conexion = pymysql.connect(host=settings.cap_db_host, port=settings.cap_db_port, user="root",
                                   password=root, connect_timeout=5, autocommit=True)
        nombre, usuario = settings.cap_db_name, settings.cap_db_user
        with conexion.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{nombre}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
            # Con parámetros, pymysql formatea con %: el comodín de host va como %%.
            cursor.execute(f"CREATE USER IF NOT EXISTS '{usuario}'@'%%' IDENTIFIED BY %s", (settings.cap_db_password,))
            # La contraseña de .env manda: si cambió, se aplica aquí.
            cursor.execute(f"ALTER USER '{usuario}'@'%%' IDENTIFIED BY %s", (settings.cap_db_password,))
            cursor.execute(f"GRANT ALL PRIVILEGES ON `{nombre}`.* TO '{usuario}'@'%'")
        conexion.close()

    _reintentar("Base de CAPTACION", crear)
    print(f"Base {settings.cap_db_name} y usuario {settings.cap_db_user} listos en {settings.cap_db_host}.")


def crear_tablas() -> None:
    _reintentar("Tablas de CAPTACION", database.crear_tablas)
    print("Tablas de CAPTACION listas.")


def credencial_coredb() -> None:
    if settings.cap_core_secreto:
        print("CAP_CORE_SECRETO viene del entorno: no se renueva.")
        return
    admin = os.environ.get("BNA_ADMIN_USUARIO", "admin")
    clave = os.environ.get("BNA_ADMIN_PASSWORD", "")
    if not clave:
        raise SystemExit("Falta BNA_ADMIN_PASSWORD para crear el usuario de servicio en COREDB.")
    http = httpx.Client(base_url=settings.core_base_url, timeout=10)

    def login():
        resp = http.post("/coredb/auth/login", json={"username": admin, "password": clave})
        resp.raise_for_status()
        return resp.json()["access_token"]

    token = _reintentar("Login del administrador en COREDB", login)
    cabeceras = {"Authorization": f"Bearer {token}"}
    usuario = None
    offset = 0
    while usuario is None:
        pagina = http.get("/coredb/usuarios", params={"limite": 200, "offset": offset}, headers=cabeceras)
        pagina.raise_for_status()
        filas = pagina.json()
        usuario = next((u for u in filas if u["username"] == settings.cap_core_usuario), None)
        if len(filas) < 200:
            break
        offset += 200

    if usuario is None:
        resp = http.post("/coredb/usuarios/servicios", headers=cabeceras, json={
            "modulo": "CLIENTES", "username": settings.cap_core_usuario,
            "nombre": "Módulo Captación de Clientes"})
        accion = "creado"
    else:
        if usuario["rol"] != "SERVICIO" or usuario["modulo"] != "CLIENTES":
            raise SystemExit(f"{settings.cap_core_usuario} existe en COREDB pero no es el usuario de servicio "
                             "de CLIENTES: use otro CAP_CORE_USUARIO.")
        if not usuario["activo"]:
            http.post(f"/coredb/usuarios/{usuario['id_usuario']}/estado", headers=cabeceras,
                      json={"activo": True}).raise_for_status()
        resp = http.post(f"/coredb/usuarios/{usuario['id_usuario']}/credencial", headers=cabeceras)
        accion = "con secreto renovado"
    if resp.status_code != 201 and resp.status_code != 200:
        raise SystemExit(f"COREDB no entregó la credencial ({resp.status_code}).")
    archivo = Path(settings.cap_core_secreto_archivo)
    archivo.parent.mkdir(parents=True, exist_ok=True)
    temporal = archivo.with_suffix(".tmp")
    temporal.write_text(resp.json()["secreto"], encoding="utf-8")
    temporal.chmod(0o600)
    temporal.replace(archivo)
    print(f"Usuario de servicio {settings.cap_core_usuario} {accion} en COREDB.")


def principal(argumentos: list[str]) -> int:
    if argumentos != ["init"]:
        print(__doc__, file=sys.stderr)
        return 2
    preparar_base()
    crear_tablas()
    credencial_coredb()
    return 0


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))
