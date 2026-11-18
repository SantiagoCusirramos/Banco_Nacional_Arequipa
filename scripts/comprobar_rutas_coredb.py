"""Comprueba que ningún módulo tiene configurada la dirección directa de COREDB.

Fase 2 del Bus de Servicios (Documents/01-stack-tecnologico.md, «Módulos de negocio → CORE:
REST interno vía Bus»): los módulos llegan a COREDB por http://bus:8018/bus/coredb, con su
credencial (BUS_TOKEN → X-Bus-Token). Solo pueden tener la dirección directa:

- `coredb` (es COREDB: su sonda de salud) y `db` (la base, que solo usa COREDB);
- `coredb-init` y los contenedores de arranque del Deployment `coredb`: crean el administrador
  y los usuarios de servicio con los scripts de COREDB, conectados a la base, no por HTTP;
- el Bus (`BUS_URL_COREDB`, en compose y en el ConfigMap `bna-bus`, que solo lee el Bus).

Revisa compose.yaml (variables, órdenes y sondas de cada servicio; redes: solo esos servicios
están en la red `core`, y `coredb` no está en ninguna otra), k8s/base (ConfigMaps y
Deployments), los .env.example y los valores por omisión de la configuración de los módulos.

Uso: python scripts/comprobar_rutas_coredb.py [carpeta del repositorio]. Sale con 1 y lista lo
que encontró. Lo corre `./bna test` (suite "Bus de Servicios, rutas a COREDB"), con PyYAML de la
imagen del backend.
"""
import re
import sys
from pathlib import Path

import yaml

# coredb:<puerto> en cualquier forma, o el puerto de COREDB en la propia máquina.
DIRECTA = re.compile(r"\bcoredb:\d+|\b(?:localhost|127\.0\.0\.1):8012\b", re.IGNORECASE)
BUS_COREDB = "http://bus:8018/bus/coredb"
VARIABLES_COREDB = ("CORE_BASE_URL", "COREDB_URL")

COMPOSE_PERMITIDOS = {"db", "coredb", "coredb-init", "bus"}
RED_COREDB = "core"
K8S_PERMITIDOS = {"coredb", "bus"}
CONFIGMAP_BUS = "bna-bus"
MODULOS = ("CUENTAS", "TARJETAS", "CAPTACION", "EVALUACION", "DESEMBOLSO", "COBRANZA", "ATM", "seguridad")


def _cadenas(valor):
    """Todas las cadenas dentro de un valor de YAML (dicts, listas, escalares)."""
    if isinstance(valor, dict):
        for k, v in valor.items():
            yield from _cadenas(k)
            yield from _cadenas(v)
    elif isinstance(valor, list):
        for v in valor:
            yield from _cadenas(v)
    elif isinstance(valor, str):
        yield valor


def _entorno(servicio):
    """environment de compose como dict, en sus dos formas (mapa o lista KEY=VALOR)."""
    entorno = servicio.get("environment") or {}
    if isinstance(entorno, list):
        return dict(e.split("=", 1) if "=" in e else (e, "") for e in entorno)
    return {k: "" if v is None else str(v) for k, v in entorno.items()}


def _redes(servicio):
    redes = servicio.get("networks")
    if redes is None:
        return ["default"]
    return list(redes) if isinstance(redes, (list, dict)) else [redes]


def _compose(raiz):
    hallados = []
    ruta = raiz / "compose.yaml"
    servicios = (yaml.safe_load(ruta.read_text()) or {}).get("services", {})
    for nombre, servicio in servicios.items():
        servicio = servicio or {}
        redes = _redes(servicio)
        if nombre in COMPOSE_PERMITIDOS:
            if nombre == "coredb" and redes != [RED_COREDB]:
                hallados.append(f"compose.yaml: coredb debe estar solo en la red '{RED_COREDB}' (está en {redes}).")
            continue
        if RED_COREDB in redes:
            hallados.append(f"compose.yaml: {nombre} está en la red '{RED_COREDB}', la de COREDB: solo el Bus llega a ella.")
        for texto in _cadenas({k: v for k, v in servicio.items() if k != "depends_on"}):
            if DIRECTA.search(texto):
                hallados.append(f"compose.yaml: {nombre} tiene la dirección directa de COREDB ({texto!r}).")
        entorno = _entorno(servicio)
        for variable in VARIABLES_COREDB:
            if variable in entorno:
                if not entorno[variable].startswith(BUS_COREDB):
                    hallados.append(f"compose.yaml: {nombre}.{variable} debe ser {BUS_COREDB}.")
                if "BUS_TOKEN" not in entorno:
                    hallados.append(f"compose.yaml: {nombre} llama a COREDB por el Bus sin BUS_TOKEN (su credencial).")
    return hallados


def _documentos_k8s(raiz):
    for ruta in sorted((raiz / "k8s").rglob("*.yaml")):
        for documento in yaml.safe_load_all(ruta.read_text()):
            if isinstance(documento, dict) and documento.get("kind"):
                yield ruta.relative_to(raiz), documento


def _k8s(raiz):
    hallados = []
    for ruta, documento in _documentos_k8s(raiz):
        tipo = documento["kind"]
        nombre = (documento.get("metadata") or {}).get("name", "?")
        if tipo == "ConfigMap":
            if nombre == CONFIGMAP_BUS:
                continue
            for clave, valor in (documento.get("data") or {}).items():
                if DIRECTA.search(str(valor)):
                    hallados.append(f"{ruta}: ConfigMap {nombre}.{clave} tiene la dirección directa de COREDB "
                                    f"(solo en el ConfigMap {CONFIGMAP_BUS}, que lee el Bus).")
                if clave in VARIABLES_COREDB and not str(valor).startswith(BUS_COREDB):
                    hallados.append(f"{ruta}: ConfigMap {nombre}.{clave} debe ser {BUS_COREDB}.")
        elif tipo in {"Deployment", "StatefulSet", "Job", "DaemonSet"}:
            if nombre in K8S_PERMITIDOS:
                continue
            plantilla = (documento.get("spec") or {}).get("template") or {}
            for texto in _cadenas(plantilla):
                if DIRECTA.search(texto):
                    hallados.append(f"{ruta}: {tipo} {nombre} tiene la dirección directa de COREDB ({texto.strip()[:80]!r}).")
            if CONFIGMAP_BUS in _referencias_configmap(plantilla):
                hallados.append(f"{ruta}: {tipo} {nombre} lee el ConfigMap {CONFIGMAP_BUS}, que es solo del Bus.")
    return hallados


def _referencias_configmap(valor):
    referencias = set()
    if isinstance(valor, dict):
        for clave in ("configMapRef", "configMapKeyRef"):
            if isinstance(valor.get(clave), dict):
                referencias.add(valor[clave].get("name"))
        for v in valor.values():
            referencias |= _referencias_configmap(v)
    elif isinstance(valor, list):
        for v in valor:
            referencias |= _referencias_configmap(v)
    return referencias


def _archivos_de_modulos(raiz):
    hallados = []
    for ruta in (raiz / ".env.example", raiz / "backend" / ".env.example",
                 raiz / "backend" / "seguridad" / ".env.example",
                 raiz / "billetera-chaski" / "backend" / ".env.example"):
        if not ruta.exists():
            continue
        for numero, linea in enumerate(ruta.read_text().splitlines(), 1):
            if not linea.lstrip().startswith("#") and DIRECTA.search(linea):
                hallados.append(f"{ruta.relative_to(raiz)}:{numero}: dirección directa de COREDB ({linea.strip()!r}).")
    for modulo in MODULOS:
        ruta = raiz / "backend" / modulo / "config.py"
        if not ruta.exists():
            continue
        for numero, linea in enumerate(ruta.read_text().splitlines(), 1):
            if DIRECTA.search(linea):
                hallados.append(f"backend/{modulo}/config.py:{numero}: valor por omisión con la dirección directa "
                                f"de COREDB ({linea.strip()!r}).")
    return hallados


def problemas(raiz):
    raiz = Path(raiz)
    return _compose(raiz) + _k8s(raiz) + _archivos_de_modulos(raiz)


def main():
    raiz = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent)
    hallados = problemas(raiz)
    for problema in hallados:
        print(problema)
    if hallados:
        sys.exit(1)
    print("Ningún módulo tiene la dirección directa de COREDB.")


if __name__ == "__main__":
    main()
