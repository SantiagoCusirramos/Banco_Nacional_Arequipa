"""Crea el primer ADMINISTRADOR de COREDB. Sin él nadie puede crear usuarios.

Uso, desde backend/, con backend/COREDB/.env completo:
    python -m COREDB.scripts.crear_administrador --username admin --nombre "Nombre"

Pide la contraseña dos veces. Se conecta con las credenciales de la aplicación y crea
el usuario por core.crear_usuario. Se niega si ya hay un administrador activo: los
demás usuarios se crean por la API.

Con --si-falta, que ya exista un administrador no es un error (salida 0): es para un
arranque automático, que se repite. La contraseña se toma entonces de
CORE_DB_ADMIN_INICIAL_PASSWORD.
"""

import argparse
import getpass
import os
import sys

from COREDB.database import get_session_factory
from COREDB.errores import ErrorCoreDb
from COREDB.models import Usuario
from COREDB.services import usuarios

# Solo para pruebas automáticas; en uso normal la contraseña se escribe en la terminal.
VARIABLE_PASSWORD = "CORE_DB_ADMIN_INICIAL_PASSWORD"
ACTOR = "arranque"


YA_EXISTE = "Ya existe un administrador activo: cree los demás usuarios por la API."


def _hay_administrador(db) -> bool:
    return (
        db.query(Usuario).filter(Usuario.rol == "ADMINISTRADOR", Usuario.activo.is_(True)).first()
        is not None
    )


def crear(username: str, nombre: str, password: str) -> int:
    """Devuelve el código de salida: 0 si lo creó, 1 si no."""
    with get_session_factory()() as db:
        if _hay_administrador(db):
            print(YA_EXISTE, file=sys.stderr)
            return 1
        try:
            usuarios.crear(db, username=username, nombre=nombre, password=password,
                           rol="ADMINISTRADOR", id_empleado=None, actor=ACTOR)
        except ErrorCoreDb as exc:
            print(f"No se creó el administrador: {exc.code}.", file=sys.stderr)
            return 1
    print(f"Administrador {username} creado.")
    return 0


def _password() -> str:
    if os.environ.get(VARIABLE_PASSWORD):
        return os.environ[VARIABLE_PASSWORD]
    primera = getpass.getpass("Contraseña: ")
    if primera != getpass.getpass("Repita la contraseña: "):
        raise SystemExit("Las contraseñas no coinciden.")
    return primera


def principal(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--username", required=True)
    parser.add_argument("--nombre", required=True)
    parser.add_argument("--si-falta", action="store_true",
                        help="no fallar si ya existe un administrador activo")
    opciones = parser.parse_args(argumentos)
    with get_session_factory()() as db:
        if _hay_administrador(db):  # antes de pedir la contraseña
            if opciones.si_falta:
                print("Ya existe un administrador activo: no se crea otro.")
                return 0
            print(YA_EXISTE, file=sys.stderr)
            return 1
    password = _password()
    if len(password) < 8:
        print("La contraseña debe tener al menos 8 caracteres.", file=sys.stderr)
        return 1
    return crear(opciones.username, opciones.nombre, password)


if __name__ == "__main__":
    sys.exit(principal())
