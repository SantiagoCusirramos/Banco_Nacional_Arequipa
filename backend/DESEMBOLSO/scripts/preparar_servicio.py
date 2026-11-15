"""Deja listo el usuario de servicio de Desembolso en COREDB y guarda su secreto, y termina.

Sigue backend/COREDB/README.md ("Usuarios de servicio"): un administrador crea el usuario con
POST /coredb/usuarios/servicios y el secreto, que COREDB muestra una sola vez, se guarda donde el
módulo lo lee. Lo ejecuta `desembolso-init` en compose.yaml, igual que Cobranza con el suyo.

    python -m DESEMBOLSO.scripts.preparar_servicio

Variables: COREDB_URL, BNA_ADMIN_USUARIO, BNA_ADMIN_PASSWORD, DESEMBOLSO_SVC_USUARIO
(svc-desembolso) y DESEMBOLSO_SVC_ARCHIVO (/datos/servicio.json).

Si el archivo ya tiene un secreto que COREDB acepta, no cambia nada. Si el usuario existe pero el
secreto no sirve (por ejemplo tras `./bna reset`), lo renueva. Si no existe, lo crea.
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid

import httpx

MODULO = "DESEMBOLSO"
NOMBRE = "Módulo Desembolso"


def _entorno(nombre: str, por_omision: str | None = None) -> str:
    valor = os.environ.get(nombre, por_omision)
    if not valor:
        print(f"Falta la variable {nombre}.", file=sys.stderr)
        sys.exit(1)
    return valor


def _login(http: httpx.Client, usuario: str, clave: str) -> str | None:
    r = http.post("/coredb/auth/login", json={"username": usuario, "password": clave},
                  headers={"X-Correlation-ID": str(uuid.uuid4())})
    return r.json()["access_token"] if r.status_code == 200 else None


def _leer(archivo: str) -> tuple[str | None, str | None]:
    try:
        with open(archivo, encoding="utf-8") as f:
            datos = json.load(f)
        return datos.get("username"), datos.get("secreto")
    except (OSError, ValueError):
        return None, None


def _guardar(archivo: str, usuario: str, secreto: str) -> None:
    os.makedirs(os.path.dirname(archivo) or ".", exist_ok=True)
    temporal = f"{archivo}.tmp"
    descriptor = os.open(temporal, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as f:
        json.dump({"username": usuario, "secreto": secreto}, f)
    os.replace(temporal, archivo)


def _esperar(http: httpx.Client, intentos: int = 60) -> None:
    for _ in range(intentos):
        try:
            if http.get("/coredb/salud").status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(2)
    print("COREDB no responde.", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    coredb = _entorno("COREDB_URL").rstrip("/")
    admin = _entorno("BNA_ADMIN_USUARIO", "admin")
    admin_clave = _entorno("BNA_ADMIN_PASSWORD")
    usuario = _entorno("DESEMBOLSO_SVC_USUARIO", "svc-desembolso")
    archivo = _entorno("DESEMBOLSO_SVC_ARCHIVO", "/datos/servicio.json")
    with httpx.Client(base_url=coredb, timeout=10) as http:
        _esperar(http)
        guardado_usuario, guardado_secreto = _leer(archivo)
        if guardado_usuario == usuario and guardado_secreto and _login(http, usuario, guardado_secreto):
            print(f"El usuario de servicio {usuario} ya está listo.")
            return 0
        token = _login(http, admin, admin_clave)
        if not token:
            print("El administrador de COREDB no pudo iniciar sesión.", file=sys.stderr)
            return 1
        cabeceras = {"Authorization": f"Bearer {token}", "X-Correlation-ID": str(uuid.uuid4())}
        r = http.get("/coredb/usuarios", params={"limite": 200}, headers=cabeceras)
        r.raise_for_status()
        existente = next((u for u in r.json() if u["username"] == usuario), None)
        if existente is None:
            r = http.post("/coredb/usuarios/servicios", headers=cabeceras,
                          json={"modulo": MODULO, "username": usuario, "nombre": NOMBRE})
            accion = "creado"
        else:
            r = http.post(f"/coredb/usuarios/{existente['id_usuario']}/credencial", headers=cabeceras)
            accion = "renovado"
        if r.status_code not in (200, 201):
            print(f"COREDB respondió {r.status_code}: {r.text}", file=sys.stderr)
            return 1
        _guardar(archivo, usuario, r.json()["secreto"])
        print(f"Usuario de servicio {usuario} {accion}.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
