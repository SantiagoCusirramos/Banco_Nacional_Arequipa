"""Deja listo el usuario de servicio de Cobranza en COREDB y guarda su secreto, y termina.

Lo ejecuta `cobranza-init` en compose.yaml antes de levantar Cobranza. Sigue el procedimiento
de backend/COREDB/README.md ("Usuarios de servicio"): un administrador crea el usuario con
POST /coredb/usuarios/servicios y el secreto se guarda donde el módulo lo lee.

    python -m COBRANZA.scripts.preparar_servicio

Variables:
    COREDB_URL              p. ej. http://coredb:8012
    BNA_ADMIN_USUARIO       administrador de COREDB (solo lo usa este script)
    BNA_ADMIN_PASSWORD
    COBRANZA_SVC_USUARIO    usuario de servicio (por defecto svc-cobranza)
    COBRANZA_SVC_ARCHIVO    dónde guardar {"username", "secreto"} (por defecto /datos/servicio.json)

Si el archivo ya tiene un secreto que COREDB acepta, no cambia nada. Si el usuario existe pero el
secreto no sirve (p. ej. tras `./bna reset`), lo renueva. Si no existe, lo crea.
"""

import json
import os
import sys
import time
import uuid

import httpx

MODULO = "COBRANZA"
NOMBRE = "Módulo Cobranza"


def _entorno(nombre, por_defecto=None):
    valor = os.environ.get(nombre, por_defecto)
    if not valor:
        print(f"Falta la variable {nombre}.", file=sys.stderr)
        sys.exit(1)
    return valor


def _login(http, coredb, usuario, password):
    r = http.post(f"{coredb}/coredb/auth/login", json={"username": usuario, "password": password},
                  headers={"X-Correlation-ID": str(uuid.uuid4())})
    return r.json()["access_token"] if r.status_code == 200 else None


def _leer(archivo):
    try:
        with open(archivo, encoding="utf-8") as f:
            datos = json.load(f)
        return datos.get("username"), datos.get("secreto")
    except (OSError, ValueError):
        return None, None


def _guardar(archivo, username, secreto):
    os.makedirs(os.path.dirname(archivo) or ".", exist_ok=True)
    temporal = f"{archivo}.tmp"
    descriptor = os.open(temporal, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as f:
        json.dump({"username": username, "secreto": secreto}, f)
    os.replace(temporal, archivo)


def _esperar_coredb(http, coredb, intentos=60):
    for _ in range(intentos):
        try:
            if http.get(f"{coredb}/coredb/salud").status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(2)
    print("COREDB no responde.", file=sys.stderr)
    sys.exit(1)


def main():
    coredb = _entorno("COREDB_URL").rstrip("/")
    admin = _entorno("BNA_ADMIN_USUARIO", "admin")
    admin_password = _entorno("BNA_ADMIN_PASSWORD")
    username = _entorno("COBRANZA_SVC_USUARIO", "svc-cobranza")
    archivo = _entorno("COBRANZA_SVC_ARCHIVO", "/datos/servicio.json")

    with httpx.Client(timeout=10) as http:
        _esperar_coredb(http, coredb)

        guardado_usuario, guardado_secreto = _leer(archivo)
        if guardado_usuario == username and guardado_secreto \
                and _login(http, coredb, username, guardado_secreto):
            print(f"El usuario de servicio {username} ya está listo.")
            return 0

        token = _login(http, coredb, admin, admin_password)
        if not token:
            print("El administrador de COREDB no pudo iniciar sesión.", file=sys.stderr)
            return 1
        cabeceras = {"Authorization": f"Bearer {token}", "X-Correlation-ID": str(uuid.uuid4())}

        r = http.get(f"{coredb}/coredb/usuarios", params={"limite": 200}, headers=cabeceras)
        r.raise_for_status()
        existente = next((u for u in r.json() if u["username"] == username), None)

        if existente is None:
            r = http.post(f"{coredb}/coredb/usuarios/servicios", headers=cabeceras,
                          json={"modulo": MODULO, "username": username, "nombre": NOMBRE})
            accion = "creado"
        else:
            r = http.post(f"{coredb}/coredb/usuarios/{existente['id_usuario']}/credencial",
                          headers=cabeceras)
            accion = "renovado"
        if r.status_code not in (200, 201):
            print(f"COREDB respondió {r.status_code}: {r.text}", file=sys.stderr)
            return 1
        _guardar(archivo, username, r.json()["secreto"])
        print(f"Usuario de servicio {username} {accion}.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
