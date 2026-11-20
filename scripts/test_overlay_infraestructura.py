"""Pruebas de scripts/overlay_infraestructura.py: el overlay del clúster de Infraestructura no usa Secrets.

Corre en la imagen del backend (tiene PyYAML), con el repositorio montado en REPO (por omisión,
la carpeta padre de este archivo): `./bna test`, suite "Overlay de Infraestructura".
"""
import os
import re
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import overlay_infraestructura as oi  # noqa: E402

REPO = Path(os.environ.get("REPO", Path(__file__).resolve().parent.parent))


def deployment(texto):
    return yaml.safe_load(textwrap.dedent(texto))


DEP = """
apiVersion: apps/v1
kind: Deployment
metadata: {name: cobranza}
spec:
  template:
    spec:
      securityContext: {runAsNonRoot: true, runAsUser: 10001, runAsGroup: 10001}
      initContainers:
        - name: esperar-coredb
          image: bna/backend:local
          command: [python, -c, "print(1)"]
          env:
            - name: COREDB_URL
              valueFrom: { configMapKeyRef: { name: bna-configuracion, key: COREDB_URL } }
            - name: BUS_TOKEN
              valueFrom: { secretKeyRef: { name: bna-secretos, key: BUS_TOKEN_COBRANZA } }
      containers:
        - name: cobranza
          image: bna/backend:local
          command: [uvicorn, COBRANZA.main:app, --port, "8014"]
          env:
            - name: BUS_TOKEN
              valueFrom: { secretKeyRef: { name: bna-secretos, key: BUS_TOKEN_COBRANZA } }
            - name: COBRANZA_COREDB_USUARIO
              value: svc-cobranza
            - name: COBRANZA_COREDB_SECRETO
              valueFrom: { secretKeyRef: { name: bna-secretos, key: COBRANZA_COREDB_SECRETO } }
"""


def contenedor(lista, nombre):
    return next(c for c in lista if c["name"] == nombre)


def test_el_copiador_va_primero_y_lleva_solo_las_claves_del_pod():
    parche = oi.parche(deployment(DEP))
    iniciales = parche["spec"]["template"]["spec"]["initContainers"]
    assert iniciales[0]["name"] == "secretos"
    claves = iniciales[0]["env"][0]
    assert claves["name"] == "BNA_CLAVES"
    assert claves["value"].splitlines() == [
        "esperar-coredb BUS_TOKEN BUS_TOKEN_COBRANZA",
        "env BUS_TOKEN BUS_TOKEN_COBRANZA",
        "env COBRANZA_COREDB_SECRETO COBRANZA_COREDB_SECRETO",
    ]
    montajes = {m["mountPath"]: m.get("readOnly", False) for m in iniciales[0]["volumeMounts"]}
    assert montajes == {"/bna-secretos": True, "/secretos": False, "/scripts": True}
    # Lee el archivo 0600 del Job, que corre con ese usuario.
    assert iniciales[0]["securityContext"]["runAsUser"] == oi.UID_SECRETOS


def test_quita_las_variables_del_secret_y_envuelve_la_orden():
    parche = oi.parche(deployment(DEP))
    principal = contenedor(parche["spec"]["template"]["spec"]["containers"], "cobranza")
    assert principal["command"] == [
        "sh", "-c", 'set -a; . /secretos/env; set +a; exec "$0" "$@"',
        "uvicorn", "COBRANZA.main:app", "--port", "8014",
    ]
    assert principal["env"] == [
        {"name": "BUS_TOKEN", "$patch": "delete"},
        {"name": "COBRANZA_COREDB_SECRETO", "$patch": "delete"},
    ]
    assert principal["volumeMounts"] == [{"name": "secretos", "mountPath": "/secretos", "readOnly": True}]
    inicial = contenedor(parche["spec"]["template"]["spec"]["initContainers"], "esperar-coredb")
    assert inicial["command"][:3] == ["sh", "-c", 'set -a; . /secretos/esperar-coredb; set +a; exec "$0" "$@"']
    assert inicial["command"][3:] == ["python", "-c", "print(1)"]


def test_conserva_el_orden_de_los_contenedores_de_inicio():
    # Kustomize ordena la lista como el último parche que la nombra: los que no usan claves
    # también van, solo con su nombre, para que `secretos` quede primero y el resto como en la base.
    dep = deployment(DEP)
    spec = dep["spec"]["template"]["spec"]
    spec["initContainers"].insert(0, {"name": "esperar-db", "image": "bna/coredb:local", "command": ["true"]})
    iniciales = oi.parche(dep)["spec"]["template"]["spec"]["initContainers"]
    assert [c["name"] for c in iniciales] == ["secretos", "esperar-db", "esperar-coredb"]
    assert iniciales[1] == {"name": "esperar-db"}


def test_volumenes_y_fsgroup():
    spec = oi.parche(deployment(DEP))["spec"]["template"]["spec"]
    volumenes = {v["name"]: v for v in spec["volumes"]}
    assert volumenes["secretos"]["emptyDir"]["medium"] == "Memory"
    assert volumenes["bna-secretos"]["persistentVolumeClaim"] == {"claimName": "secretos", "readOnly": True}
    assert volumenes["scripts-secretos"]["configMap"]["name"] == "bna-scripts-secretos"
    # El grupo del pod puede leer los archivos que deja el copiador (0440).
    assert spec["securityContext"] == {"fsGroup": 10001}


def test_respeta_un_fsgroup_existente():
    dep = deployment(DEP)
    dep["spec"]["template"]["spec"]["securityContext"]["fsGroup"] = 999
    assert "securityContext" not in oi.parche(dep)["spec"]["template"]["spec"]


def test_variable_del_secret_en_la_orden_pasa_a_expansion_del_shell():
    dep = deployment(DEP)
    inicial = dep["spec"]["template"]["spec"]["initContainers"][0]
    inicial["command"] = ["python", "-m", "crear", "--username", "$(BUS_TOKEN)", "--nombre", "Administrador inicial"]
    orden = contenedor(oi.parche(dep)["spec"]["template"]["spec"]["initContainers"], "esperar-coredb")["command"]
    assert orden == ["sh", "-c", "set -a; . /secretos/esperar-coredb; set +a; "
                     "exec python -m crear --username \"${BUS_TOKEN}\" --nombre 'Administrador inicial'"]


def test_sin_orden_usa_la_de_la_imagen():
    dep = deployment(DEP)
    principal = dep["spec"]["template"]["spec"]["containers"][0]
    del principal["command"]
    principal["image"] = "bna/frontend:local"
    orden = oi.parche(dep)["spec"]["template"]["spec"]["containers"][0]["command"]
    assert orden[3:] == ["npm", "start"]
    principal["image"] = "bna/desconocida:local"
    with pytest.raises(oi.NoSoportado, match="bna/desconocida"):
        oi.parche(dep)


def test_sonda_exec_lee_el_archivo():
    dep = deployment(DEP)
    principal = dep["spec"]["template"]["spec"]["containers"][0]
    principal["readinessProbe"] = {"exec": {"command": ["sh", "-c", 'echo "$BUS_TOKEN"']}, "periodSeconds": 5}
    principal["livenessProbe"] = {"tcpSocket": {"port": 1}}
    resultado = oi.parche(dep)["spec"]["template"]["spec"]["containers"][0]
    assert resultado["readinessProbe"] == {"exec": {"command": [
        "sh", "-c", 'set -a; . /secretos/env; set +a; echo "$BUS_TOKEN"']}}
    assert "livenessProbe" not in resultado


@pytest.mark.parametrize("cambio, mensaje", [
    (lambda c: c.update(envFrom=[{"secretRef": {"name": "bna-secretos"}}]), "envFrom"),
    (lambda c: c["env"].append({"name": "X", "valueFrom": {"secretKeyRef": {"name": "otro", "key": "X"}}}), "otro"),
    (lambda c: c.update(args=["--x"]), "args"),
    (lambda c: c["env"].append({"name": "Y", "value": "$(BUS_TOKEN)"}), "Y"),
])
def test_rechaza_lo_que_no_sabe_convertir(cambio, mensaje):
    dep = deployment(DEP)
    cambio(dep["spec"]["template"]["spec"]["containers"][0])
    with pytest.raises(oi.NoSoportado, match=mensaje):
        oi.parche(dep)


def test_volumen_secret_no_se_soporta():
    dep = deployment(DEP)
    dep["spec"]["template"]["spec"]["volumes"] = [{"name": "v", "secret": {"secretName": "bna-secretos"}}]
    with pytest.raises(oi.NoSoportado, match="volumen"):
        oi.parche(dep)


def test_deployment_sin_claves_no_cambia():
    dep = deployment(DEP)
    for c in dep["spec"]["template"]["spec"]["initContainers"] + dep["spec"]["template"]["spec"]["containers"]:
        c["env"] = [e for e in c["env"] if "secretKeyRef" not in (e.get("valueFrom") or {})]
    assert oi.parche(dep) is None


# ── El repositorio ────────────────────────────────────────────────────────────

def test_el_archivo_generado_esta_al_dia():
    assert oi.generar(REPO) == (REPO / oi.SALIDA).read_text(), (
        "k8s/overlays/infraestructura/secretos.yaml no corresponde a k8s/base: "
        "python3 scripts/overlay_infraestructura.py generar")


def test_las_ordenes_de_las_imagenes_coinciden_con_los_dockerfile():
    for imagen, orden in oi.ORDEN_DE_IMAGEN.items():
        if imagen == "bna/core-db":
            continue  # la de mysql:8.4: ENTRYPOINT docker-entrypoint.sh, CMD mysqld
        carpeta = imagen.split("/")[1]
        texto = (REPO / "docker" / carpeta / "Dockerfile").read_text()
        cmd = re.findall(r"^CMD (\[.*\])$", texto, re.MULTILINE)[-1]
        assert yaml.safe_load(cmd) == orden, imagen
        assert "ENTRYPOINT" not in texto, imagen


def test_cada_clave_existe_en_env_example():
    claves = {linea.split("=", 1)[0] for linea in (REPO / ".env.example").read_text().splitlines()
              if re.match(r"[A-Za-z_]\w*=", linea)}
    for documento in yaml.safe_load_all(oi.generar(REPO)):
        copiador = documento["spec"]["template"]["spec"]["initContainers"][0]
        for linea in copiador["env"][0]["value"].splitlines():
            assert linea.split()[2] in claves, linea


# ── Revisión de los manifiestos ya generados (kubectl kustomize) ──────────────

RENDER_BUENO = """
apiVersion: v1
kind: ConfigMap
metadata: {name: bna-configuracion}
data: {CORE_BASE_URL: "http://bna-bus:8018/bus/coredb", CORE_DB_HOST: bna-db}
---
apiVersion: apps/v1
kind: Deployment
metadata: {name: bna-cobranza}
spec:
  template:
    spec:
      initContainers:
        - name: secretos
          image: ghcr.io/miguelpro324/bna-backend:abc
          command: [sh, /scripts/copiar.sh]
      containers:
        - name: cobranza
          image: ghcr.io/miguelpro324/bna-backend:abc
          command: [sh, -c, 'set -a; . /secretos/env; set +a; exec "$0" "$@"', uvicorn]
          env:
            - {name: COREDB_URL, value: "http://bna-bus:8018/bus/coredb"}
---
apiVersion: v1
kind: Service
metadata: {name: bna-cobranza}
"""


def revisar(texto):
    return oi.revisar(list(yaml.safe_load_all(textwrap.dedent(texto))), servicios={"bus", "db", "cobranza"},
                      registro="ghcr.io/miguelpro324/")


def test_revisar_acepta_un_render_correcto():
    assert revisar(RENDER_BUENO) == []


@pytest.mark.parametrize("viejo, nuevo, mensaje", [
    ("kind: Service\nmetadata: {name: bna-cobranza}", "kind: Secret\nmetadata: {name: bna-cobranza}", "Secret"),
    ("{name: COREDB_URL, value: \"http://bna-bus:8018/bus/coredb\"}",
     "{name: X, valueFrom: {secretKeyRef: {name: s, key: X}}}", "secretKeyRef"),
    ("http://bna-bus:8018/bus/coredb\"}", "http://bus:8018/bus/coredb\"}", "bus"),
    ("CORE_DB_HOST: bna-db", "CORE_DB_HOST: db", "db"),
    ("ghcr.io/miguelpro324/bna-backend:abc\n          command: [sh, -c",
     "bna/backend:local\n          command: [sh, -c", "bna/backend:local"),
    ("metadata: {name: bna-cobranza}\nspec", "metadata: {name: cobranza}\nspec", "cobranza"),
    ("metadata: {name: bna-cobranza}\nspec", "metadata: {name: bna-cobranza, labels: {a/b=c: bna}}\nspec", "etiqueta"),
    ("metadata: {name: bna-cobranza}\nspec", "metadata: {name: bna-cobranza, labels: {a/b: \"no valida\"}}\nspec", "etiqueta"),
    ("        - name: secretos\n          image: ghcr.io/miguelpro324/bna-backend:abc\n"
     "          command: [sh, /scripts/copiar.sh]\n", "        - name: x\n          image: ghcr.io/miguelpro324/bna-backend:abc\n", "secretos"),
])
def test_revisar_encuentra(viejo, nuevo, mensaje):
    texto = textwrap.dedent(RENDER_BUENO)
    assert viejo in texto, viejo
    hallados = revisar(texto.replace(viejo, nuevo))
    assert hallados and any(mensaje in h for h in hallados), hallados
