"""Crea o alinea el usuario de servicio de un módulo con un secreto dado. Para el arranque.

Uso, desde backend/, con las variables de conexión de COREDB:
    CORE_DB_SERVICIO_SECRETO=<secreto> python -m COREDB.scripts.crear_servicio \
        --modulo EVALUACION --username svc-evaluacion --nombre "Evaluación"

A diferencia de `POST /coredb/usuarios/servicios`, que genera el secreto y lo entrega una
vez, aquí el secreto lo pone el despliegue (el .env de compose o el Secret de Kubernetes),
para que el módulo lo lea de su propio entorno. Se conecta con las credenciales de la
aplicación y escribe por los mismos procedimientos que la API:

- si el usuario no existe, lo crea (core.crear_usuario_servicio);
- si existe y el secreto ya sirve, no cambia nada;
- si existe con otro secreto, lo reemplaza (core.renovar_credencial).

Se niega si el nombre es de una persona. Nunca imprime el secreto.
"""

import argparse
import os
import sys
import uuid

from COREDB.database import get_session_factory, llamar
from COREDB.errores import ErrorCoreDb
from COREDB.models import Usuario
from COREDB.services.hashing import ALGORITMO_BCRYPT, bcrypt_admite, hash_bcrypt, verify_password
from COREDB.services.usuarios import VERSION_HASH_BCRYPT
from COREDB.transacciones import con_reintentos

VARIABLE_SECRETO = "CORE_DB_SERVICIO_SECRETO"
LONGITUD_MINIMA = 32
ACTOR = "arranque"


def alinear(modulo: str, username: str, nombre: str, secreto: str) -> int:
    """Devuelve el código de salida: 0 si el usuario quedó con ese secreto, 1 si no."""
    with get_session_factory()() as db:
        usuario = db.query(Usuario).filter(Usuario.username == username).one_or_none()
        try:
            if usuario is None:
                con_reintentos(db, lambda: llamar(
                    db, "core.crear_usuario_servicio", uuid.uuid4(), username, nombre, modulo,
                    hash_bcrypt(secreto), ALGORITMO_BCRYPT, VERSION_HASH_BCRYPT, ACTOR,
                ), nombre="crear_usuario_servicio")
                print(f"Usuario de servicio {username} ({modulo}) creado.")
                return 0
            if usuario.rol != "SERVICIO" or usuario.modulo != modulo:
                print(f"{username} no es un usuario de servicio del módulo {modulo}: no se cambia.",
                      file=sys.stderr)
                return 1
            if verify_password(secreto, usuario.hash_password, usuario.algoritmo_hash):
                print(f"El usuario de servicio {username} ya existe con ese secreto.")
                return 0
            id_usuario = usuario.id_usuario
            con_reintentos(db, lambda: llamar(
                db, "core.renovar_credencial", id_usuario, hash_bcrypt(secreto), ALGORITMO_BCRYPT,
                VERSION_HASH_BCRYPT, ACTOR, salidas=1,
            ), nombre="renovar_credencial")
            print(f"Usuario de servicio {username}: secreto reemplazado por el del despliegue.")
            return 0
        except ErrorCoreDb as exc:
            print(f"No se preparó el usuario de servicio {username}: {exc.code}.", file=sys.stderr)
            return 1


def principal(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--modulo", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--nombre", required=True)
    opciones = parser.parse_args(argumentos)
    secreto = os.environ.get(VARIABLE_SECRETO, "")
    if len(secreto) < LONGITUD_MINIMA or not bcrypt_admite(secreto):
        print(f"{VARIABLE_SECRETO} debe tener entre {LONGITUD_MINIMA} y 72 caracteres ASCII.",
              file=sys.stderr)
        return 1
    return alinear(opciones.modulo.upper(), opciones.username, opciones.nombre, secreto)


if __name__ == "__main__":
    sys.exit(principal())
