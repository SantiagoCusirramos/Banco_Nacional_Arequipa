#!/usr/bin/env python3
"""Overlay del clúster de Infraestructura: las claves sin objetos Secret.

En k8s/base cada clave llega como variable de entorno desde el Secret `bna-secretos`. En el
clúster de Infraestructura no hay Secrets: el Job `bna-arranque` deja el .env en el PVC
`bna-secretos` y cada pod lo lee así:

  1. Un contenedor de inicio `secretos` (el primero) monta el PVC en solo lectura y copia a un
     emptyDir en memoria (`/secretos`) solo las claves que usa ese pod, un archivo por
     contenedor: `/secretos/env` para el principal y `/secretos/<nombre>` para cada contenedor
     de inicio. La lista sale de los `secretKeyRef` de k8s/base.
  2. Cada contenedor que usaba una clave pierde esas variables y arranca con
     `sh -c 'set -a; . /secretos/<archivo>; set +a; exec <orden>'`. El código de los módulos
     no cambia: reciben las mismas variables que con el Secret.

Este script escribe esos cambios en k8s/overlays/infraestructura/secretos.yaml, a partir de
k8s/base. Uso:

  python3 scripts/overlay_infraestructura.py generar     # reescribe secretos.yaml
  python3 scripts/overlay_infraestructura.py comprobar   # sale con 1 si no está al día
  python3 scripts/overlay_infraestructura.py revisar MANIFIESTOS.yaml [--registro R]
      # revisa la salida de `kubectl kustomize k8s/overlays/infraestructura`: ningún Secret
      # ni secretKeyRef, nombres con el prefijo bna-, direcciones hacia los Services con
      # prefijo e imágenes del registro.

Requiere PyYAML. Pruebas: scripts/test_overlay_infraestructura.py.
"""
import argparse
import re
import shlex
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = Path("k8s/overlays/infraestructura/secretos.yaml")
SECRET = "bna-secretos"
PREFIJO = "bna-"
REGISTRO = "ghcr.io/miguelpro324/"
# El Job bna-arranque escribe el .env (0600) con este usuario; el copiador lo lee con el mismo.
UID_SECRETOS = 10001
IMAGEN_COPIADOR = "bna/backend:local"
# Orden de la imagen, para los contenedores que no la declaran en k8s/base.
ORDEN_DE_IMAGEN = {
    "bna/frontend": ["npm", "start"],
    "bna/billetera": ["node", "server.js"],
    "bna/core-db": ["docker-entrypoint.sh", "mysqld"],
}
VARIABLE_K8S = re.compile(r"\$\(([A-Za-z_][A-Za-z0-9_]*)\)")
CABECERA = """\
# GENERADO por scripts/overlay_infraestructura.py a partir de k8s/base: no editar a mano.
# Para regenerarlo: python3 scripts/overlay_infraestructura.py generar
#
# Por cada Deployment que usa claves: el contenedor de inicio `secretos` copia del PVC
# bna-secretos solo las claves del pod (BNA_CLAVES: archivo, variable, clave del .env), y cada
# contenedor deja de leerlas del Secret y las carga de /secretos antes de su orden.
"""


class NoSoportado(Exception):
    """k8s/base usa claves de una forma que este script no sabe convertir."""


def envoltura(archivo):
    return f"set -a; . /secretos/{archivo}; set +a; "


def _orden_original(contenedor):
    if contenedor.get("args"):
        raise NoSoportado(f"{contenedor['name']}: args no está soportado; use command")
    if contenedor.get("command"):
        return list(contenedor["command"])
    imagen = contenedor["image"].rsplit(":", 1)[0]
    if imagen not in ORDEN_DE_IMAGEN:
        raise NoSoportado(f"{contenedor['name']}: {imagen} no declara command y su orden no está en ORDEN_DE_IMAGEN")
    return list(ORDEN_DE_IMAGEN[imagen])


def _a_shell(argumento, variables):
    """Un argumento como palabra de shell; $(VAR) de una clave pasa a "${VAR}"."""
    partes, inicio = [], 0
    for m in VARIABLE_K8S.finditer(argumento):
        if m.group(1) not in variables:
            continue
        if m.start() > inicio:
            partes.append(shlex.quote(argumento[inicio:m.start()]))
        partes.append(f'"${{{m.group(1)}}}"')
        inicio = m.end()
    if inicio < len(argumento) or not partes:
        partes.append(shlex.quote(argumento[inicio:]))
    return "".join(partes)


def _orden_envuelta(orden, archivo, variables):
    if any(m.group(1) in variables for a in orden for m in VARIABLE_K8S.finditer(a)):
        # Kubernetes ya no puede expandir $(VAR): lo hace el shell, después de cargar el archivo.
        return ["sh", "-c", envoltura(archivo) + "exec " + " ".join(_a_shell(a, variables) for a in orden)]
    return ["sh", "-c", envoltura(archivo) + 'exec "$0" "$@"', *orden]


def _sonda(sonda, archivo):
    orden = sonda["exec"]["command"]
    if len(orden) == 3 and orden[0] in ("sh", "/bin/sh") and orden[1] == "-c":
        return {"exec": {"command": ["sh", "-c", envoltura(archivo) + orden[2]]}}
    return {"exec": {"command": ["sh", "-c", envoltura(archivo) + 'exec "$0" "$@"', *orden]}}


def _claves(contenedor):
    """[(variable, clave del .env)] de las variables que vienen del Secret."""
    claves = []
    for origen in contenedor.get("envFrom") or []:
        if "secretRef" in origen:
            raise NoSoportado(f"{contenedor['name']}: envFrom con secretRef no está soportado")
    for variable in contenedor.get("env") or []:
        referencia = (variable.get("valueFrom") or {}).get("secretKeyRef")
        if referencia is None:
            continue
        if referencia.get("name") != SECRET:
            raise NoSoportado(f"{contenedor['name']}.{variable['name']}: Secret {referencia.get('name')}, "
                              f"se esperaba {SECRET}")
        claves.append((variable["name"], referencia["key"]))
    nombres = {v for v, _ in claves}
    for variable in contenedor.get("env") or []:
        if any(m.group(1) in nombres for m in VARIABLE_K8S.finditer(str(variable.get("value", "")))):
            raise NoSoportado(f"{contenedor['name']}.{variable['name']}: usa $(...) de una clave del Secret")
    return claves


def _contenedor(contenedor, archivo, claves):
    variables = {v for v, _ in claves}
    if contenedor.get("lifecycle"):
        raise NoSoportado(f"{contenedor['name']}: lifecycle no está soportado")
    parche = {
        "name": contenedor["name"],
        "command": _orden_envuelta(_orden_original(contenedor), archivo, variables),
        "env": [{"name": v, "$patch": "delete"} for v, _ in claves],
        "volumeMounts": [{"name": "secretos", "mountPath": "/secretos", "readOnly": True}],
    }
    for nombre in ("startupProbe", "readinessProbe", "livenessProbe"):
        if "exec" in (contenedor.get(nombre) or {}):
            parche[nombre] = _sonda(contenedor[nombre], archivo)
    return parche


def _copiador(lineas):
    return {
        "name": "secretos",
        "image": IMAGEN_COPIADOR,
        "command": ["sh", "/scripts/copiar.sh"],
        "env": [{"name": "BNA_CLAVES", "value": "\n".join(lineas) + "\n"}],
        "volumeMounts": [
            {"name": "bna-secretos", "mountPath": "/bna-secretos", "readOnly": True},
            {"name": "secretos", "mountPath": "/secretos"},
            {"name": "scripts-secretos", "mountPath": "/scripts", "readOnly": True},
        ],
        "resources": {"requests": {"cpu": "10m", "memory": "16Mi"},
                      "limits": {"cpu": "100m", "memory": "64Mi"}},
        "securityContext": {
            "runAsUser": UID_SECRETOS, "runAsGroup": UID_SECRETOS, "runAsNonRoot": True,
            "allowPrivilegeEscalation": False, "readOnlyRootFilesystem": True,
            "capabilities": {"drop": ["ALL"]},
        },
    }


def parche(deployment):
    """Parche estratégico de un Deployment de k8s/base, o None si no usa claves."""
    spec = deployment["spec"]["template"]["spec"]
    for volumen in spec.get("volumes") or []:
        if "secret" in volumen or "secret" in str(volumen.get("projected", "")):
            raise NoSoportado(f"{deployment['metadata']['name']}: volumen {volumen['name']} con un Secret")
    iniciales, principales, lineas = [], [], []
    for lista, salida, es_inicio in ((spec.get("initContainers") or [], iniciales, True),
                                     (spec.get("containers") or [], principales, False)):
        for contenedor in lista:
            claves = _claves(contenedor)
            if not claves:
                if es_inicio:
                    # Solo el nombre: kustomize ordena la lista como el último parche que la nombra.
                    salida.append({"name": contenedor["name"]})
                continue
            archivo = contenedor["name"] if es_inicio else "env"
            lineas += [f"{archivo} {variable} {clave}" for variable, clave in claves]
            salida.append(_contenedor(contenedor, archivo, claves))
    if not lineas:
        return None
    if len(principales) > 1:
        raise NoSoportado(f"{deployment['metadata']['name']}: más de un contenedor principal con claves")
    plantilla = {
        "initContainers": [_copiador(lineas), *iniciales],
        "containers": principales,
        "volumes": [
            {"name": "secretos", "emptyDir": {"medium": "Memory", "sizeLimit": "1Mi"}},
            {"name": "bna-secretos", "persistentVolumeClaim": {"claimName": "secretos", "readOnly": True}},
            {"name": "scripts-secretos", "configMap": {"name": "bna-scripts-secretos", "defaultMode": 0o555}},
        ],
    }
    seguridad = spec.get("securityContext") or {}
    if "fsGroup" not in seguridad:
        grupo = seguridad.get("runAsGroup", seguridad.get("runAsUser", UID_SECRETOS))
        plantilla = {"securityContext": {"fsGroup": grupo}, **plantilla}
    return {
        "apiVersion": deployment["apiVersion"],
        "kind": "Deployment",
        "metadata": {"name": deployment["metadata"]["name"]},
        "spec": {"template": {"spec": plantilla}},
    }


def documentos_base(raiz):
    base = Path(raiz) / "k8s" / "base"
    recursos = yaml.safe_load((base / "kustomization.yaml").read_text())["resources"]
    for recurso in recursos:
        for documento in yaml.safe_load_all((base / recurso).read_text()):
            if isinstance(documento, dict) and documento.get("kind"):
                yield documento


class _Dumper(yaml.SafeDumper):
    pass


def _texto(dumper, valor):
    estilo = "|" if "\n" in valor else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", valor, style=estilo)


_Dumper.add_representer(str, _texto)


def generar(raiz=RAIZ):
    parches = [p for d in documentos_base(raiz) if d["kind"] == "Deployment" for p in [parche(d)] if p]
    cuerpo = yaml.dump_all(parches, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=200)
    return CABECERA + cuerpo


# ── Revisión de los manifiestos generados ─────────────────────────────────────

def _cadenas(valor):
    if isinstance(valor, str):
        yield valor
    elif isinstance(valor, dict):
        for v in valor.values():
            yield from _cadenas(v)
    elif isinstance(valor, list):
        for v in valor:
            yield from _cadenas(v)


def _tiene_secreto(valor):
    if isinstance(valor, dict):
        if {"secretKeyRef", "secretRef", "secret"} & set(valor):
            return True
        return any(_tiene_secreto(v) for v in valor.values())
    if isinstance(valor, list):
        return any(_tiene_secreto(v) for v in valor)
    return False


_NOMBRE_ETIQUETA = re.compile(r"^([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9]$")
_PREFIJO_ETIQUETA = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$")


def _etiqueta_valida(clave, valor):
    prefijo, _, nombre = str(clave).rpartition("/")
    if prefijo and (len(prefijo) > 253 or not _PREFIJO_ETIQUETA.match(prefijo)):
        return False
    if len(nombre) > 63 or not _NOMBRE_ETIQUETA.match(nombre):
        return False
    valor = "" if valor is None else str(valor)
    return valor == "" or (len(valor) <= 63 and bool(_NOMBRE_ETIQUETA.match(valor)))


def _etiquetas(doc):
    """Todas las etiquetas de un objeto: las suyas, las de su plantilla y las de su selector."""
    spec = doc.get("spec") or {}
    yield from ((doc.get("metadata") or {}).get("labels") or {}).items()
    yield from (((spec.get("template") or {}).get("metadata") or {}).get("labels") or {}).items()
    selector = spec.get("selector") or {}
    yield from (selector.get("matchLabels") or selector if isinstance(selector, dict) else {}).items()


def revisar(documentos, servicios, registro=REGISTRO):
    """Problemas en los manifiestos ya generados del overlay (lista vacía si no hay)."""
    hallados = []
    sin_prefijo = re.compile(r"(?:://|^|[\"'])(" + "|".join(sorted(map(re.escape, servicios))) + r")(?=[:/\"']|$)")
    for doc in documentos:
        if not isinstance(doc, dict):
            continue
        tipo, nombre = doc.get("kind"), (doc.get("metadata") or {}).get("name", "?")
        if tipo == "Secret":
            hallados.append(f"Secret {nombre}: el overlay no debe crear Secrets.")
        if not nombre.startswith(PREFIJO):
            hallados.append(f"{tipo} {nombre}: el nombre debe empezar con {PREFIJO}.")
        for clave, valor in _etiquetas(doc):
            if not isinstance(valor, dict) and not _etiqueta_valida(clave, valor):
                hallados.append(f"{tipo} {nombre}: etiqueta no válida {clave}={valor}.")
        if _tiene_secreto(doc.get("spec") or {}):
            hallados.append(f"{tipo} {nombre}: lee un Secret (secretKeyRef, secretRef o volumen).")
        textos = list(_cadenas(doc.get("data") or {})) if tipo == "ConfigMap" else []
        plantilla = ((doc.get("spec") or {}).get("template") or {}).get("spec") or {}
        contenedores = (plantilla.get("initContainers") or []) + (plantilla.get("containers") or [])
        for c in contenedores:
            textos += list(_cadenas(c.get("command") or [])) + list(_cadenas(c.get("args") or []))
            textos += [str(v.get("value", "")) for v in c.get("env") or []]
            if not str(c.get("image", "")).startswith(registro):
                hallados.append(f"{tipo} {nombre}: la imagen {c.get('image')} no es de {registro}.")
        for texto in textos:
            for linea in texto.splitlines() or [texto]:
                m = sin_prefijo.search(linea.strip())
                if m:
                    hallados.append(f"{tipo} {nombre}: apunta al Service {m.group(1)} sin el prefijo {PREFIJO} "
                                    f"({linea.strip()[:80]!r}).")
        usa_archivos = any("/secretos/" in t for c in contenedores for t in _cadenas(c.get("command") or []))
        iniciales = plantilla.get("initContainers") or []
        if usa_archivos and (not iniciales or iniciales[0].get("name") != "secretos"):
            hallados.append(f"{tipo} {nombre}: carga /secretos pero su primer contenedor de inicio no es secretos.")
    return hallados


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="orden", required=True)
    sub.add_parser("generar")
    sub.add_parser("comprobar")
    p = sub.add_parser("revisar")
    p.add_argument("manifiestos")
    p.add_argument("--registro", default=REGISTRO)
    args = parser.parse_args(argv)
    if args.orden == "generar":
        (RAIZ / SALIDA).write_text(generar())
        print(f"{SALIDA} generado.")
        return 0
    if args.orden == "comprobar":
        if generar() != (RAIZ / SALIDA).read_text():
            print(f"{SALIDA} no corresponde a k8s/base: python3 scripts/overlay_infraestructura.py generar",
                  file=sys.stderr)
            return 1
        print(f"{SALIDA} al día.")
        return 0
    servicios = {d["metadata"]["name"] for d in documentos_base(RAIZ) if d["kind"] == "Service"}
    with open(args.manifiestos, encoding="utf-8") as archivo:
        hallados = revisar(list(yaml.safe_load_all(archivo)), servicios, args.registro)
    for h in hallados:
        print(h, file=sys.stderr)
    if hallados:
        return 1
    print("Manifiestos del overlay de Infraestructura: sin Secrets, con prefijo y del registro.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
