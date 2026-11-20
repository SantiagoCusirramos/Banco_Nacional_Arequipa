"""Pruebas de scripts/comprobar_rutas_coredb.py: ningún módulo tiene la dirección directa de COREDB.

Corre en la imagen del backend (tiene PyYAML), con el repositorio montado en REPO (por omisión,
la carpeta padre de este archivo): `./bna test`, suite "Bus de Servicios, rutas a COREDB".
"""
import os
import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comprobar_rutas_coredb import problemas  # noqa: E402

REPO = Path(os.environ.get("REPO", Path(__file__).resolve().parent.parent))

COMPOSE_BUENO = """
x-backend: &backend
  image: bna/backend:local
services:
  db:
    image: mysql
    networks: [core]
  coredb:
    image: bna/coredb:local
    networks: [core]
    healthcheck:
      test: [CMD, python, -c, 'u.urlopen("http://127.0.0.1:8012/coredb/salud")']
  coredb-init:
    image: bna/coredb:local
    networks: [core]
  bus:
    <<: *backend
    environment:
      BUS_URL_COREDB: http://coredb:8012
      BUS_URL_CUENTAS: http://cuentas:8001
    networks: [default, canales, core]
  cuentas:
    <<: *backend
    environment:
      CORE_BASE_URL: http://bus:8018/bus/coredb
      BUS_TOKEN: ${BUS_TOKEN_CUENTAS:?falta}
  evaluacion:
    <<: *backend
    environment:
      - COREDB_URL=http://bus:8018/bus/coredb
      - BUS_TOKEN=${BUS_TOKEN_EVALUACION:?falta}
  frontend:
    image: bna/frontend:local
    environment:
      COREDB_URL: http://bus:8018/bus/coredb
      BUS_TOKEN: ${BUS_TOKEN_FRONTEND:?falta}
    networks: [canales]
networks:
  core: {}
  canales: {}
"""

CONFIGMAPS_BUENOS = """
apiVersion: v1
kind: ConfigMap
metadata: { name: bna-configuracion }
data:
  CORE_BASE_URL: http://bus:8018/bus/coredb
  COREDB_URL: http://bus:8018/bus/coredb
---
apiVersion: v1
kind: ConfigMap
metadata: { name: bna-bus }
data:
  BUS_URL_COREDB: http://coredb:8012
"""

DEPLOYMENT_MODULO = """
apiVersion: apps/v1
kind: Deployment
metadata: { name: cuentas }
spec:
  template:
    spec:
      initContainers:
        - name: esperar-coredb
          image: bna/backend:local
          command: [python, -c, 'u.urlopen(u.Request("http://bus:8018/bus/coredb/coredb/salud"))']
      containers:
        - name: cuentas
          image: bna/backend:local
          envFrom:
            - configMapRef: { name: bna-configuracion }
          env:
            - name: BUS_TOKEN
              valueFrom: { secretKeyRef: { name: bna-secretos, key: BUS_TOKEN_CUENTAS } }
"""

DEPLOYMENT_BUS = """
apiVersion: apps/v1
kind: Deployment
metadata: { name: bus }
spec:
  template:
    spec:
      containers:
        - name: bus
          envFrom:
            - configMapRef: { name: bna-configuracion }
            - configMapRef: { name: bna-bus }
"""

DEPLOYMENT_COREDB = """
apiVersion: apps/v1
kind: Deployment
metadata: { name: coredb }
spec:
  template:
    spec:
      containers:
        - name: coredb
          command: [uvicorn, COREDB.main:app, --port, "8012"]
          readinessProbe: { exec: { command: [python, -c, 'u.urlopen("http://127.0.0.1:8012/coredb/salud")'] } }
"""

CONFIG_MODULO = 'core_base_url: str = "http://localhost:8018/bus/coredb"\n'


def _repo(tmp_path, *, compose=COMPOSE_BUENO, configmaps=CONFIGMAPS_BUENOS, modulo=DEPLOYMENT_MODULO,
          env_ejemplo="BUS_TOKEN_CUENTAS=\nBNA_PUERTO_COREDB=8012\n", config_modulo=CONFIG_MODULO):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "compose.yaml").write_text(textwrap.dedent(compose))
    base = tmp_path / "k8s" / "base"
    base.mkdir(parents=True)
    (base / "configuracion.yaml").write_text(configmaps)
    (base / "cuentas.yaml").write_text(modulo)
    (base / "bus.yaml").write_text(DEPLOYMENT_BUS)
    (base / "coredb.yaml").write_text(DEPLOYMENT_COREDB)
    (base / "kustomization.yaml").write_text("resources: [configuracion.yaml]\n")
    (tmp_path / ".env.example").write_text(env_ejemplo)
    (tmp_path / "backend" / "CUENTAS").mkdir(parents=True)
    (tmp_path / "backend" / "CUENTAS" / "config.py").write_text(config_modulo)
    (tmp_path / "backend" / ".env.example").write_text("CORE_BASE_URL=http://localhost:8018/bus/coredb\n")
    return tmp_path


def test_configuracion_correcta_no_tiene_problemas(tmp_path):
    assert problemas(_repo(tmp_path)) == []


@pytest.mark.parametrize("direccion", ["http://coredb:8012", "http://coredb:8012/coredb", "http://localhost:8012",
                                       "http://127.0.0.1:8012"])
def test_un_modulo_con_la_direccion_directa_en_compose(tmp_path, direccion):
    compose = COMPOSE_BUENO.replace("CORE_BASE_URL: http://bus:8018/bus/coredb", f"CORE_BASE_URL: {direccion}")
    hallados = problemas(_repo(tmp_path, compose=compose))
    assert any("compose.yaml" in p and "cuentas" in p for p in hallados), hallados


def test_un_modulo_con_la_direccion_directa_en_formato_lista(tmp_path):
    compose = COMPOSE_BUENO.replace("- COREDB_URL=http://bus:8018/bus/coredb", "- COREDB_URL=http://coredb:8012")
    hallados = problemas(_repo(tmp_path, compose=compose))
    assert any("evaluacion" in p for p in hallados), hallados


def test_un_modulo_que_llama_a_coredb_sin_credencial_del_bus(tmp_path):
    compose = COMPOSE_BUENO.replace("      BUS_TOKEN: ${BUS_TOKEN_CUENTAS:?falta}\n", "")
    hallados = problemas(_repo(tmp_path, compose=compose))
    assert any("cuentas" in p and "BUS_TOKEN" in p for p in hallados), hallados


def test_un_modulo_en_la_red_de_coredb(tmp_path):
    compose = COMPOSE_BUENO.replace("      BUS_TOKEN: ${BUS_TOKEN_CUENTAS:?falta}\n",
                                    "      BUS_TOKEN: ${BUS_TOKEN_CUENTAS:?falta}\n    networks: [default, core]\n")
    hallados = problemas(_repo(tmp_path, compose=compose))
    assert any("cuentas" in p and "core" in p for p in hallados), hallados


def test_coredb_alcanzable_fuera_de_su_red(tmp_path):
    compose = COMPOSE_BUENO.replace("    image: bna/coredb:local\n    networks: [core]\n    healthcheck",
                                    "    image: bna/coredb:local\n    networks: [core, default]\n    healthcheck")
    hallados = problemas(_repo(tmp_path, compose=compose))
    assert any("coredb" in p and "default" in p for p in hallados), hallados


def test_la_direccion_directa_en_el_configmap_compartido(tmp_path):
    configmaps = CONFIGMAPS_BUENOS.replace("  COREDB_URL: http://bus:8018/bus/coredb", "  COREDB_URL: http://coredb:8012")
    hallados = problemas(_repo(tmp_path, configmaps=configmaps))
    assert any("bna-configuracion" in p and "COREDB_URL" in p for p in hallados), hallados


def test_el_bus_con_el_prefijo_del_overlay_de_infraestructura(tmp_path):
    # k8s/overlays/infraestructura llama bna-<servicio> a cada Service.
    configmaps = CONFIGMAPS_BUENOS.replace("http://bus:8018/bus/coredb", "http://bna-bus:8018/bus/coredb")
    assert problemas(_repo(tmp_path / "bien", configmaps=configmaps)) == []
    configmaps = CONFIGMAPS_BUENOS.replace("  COREDB_URL: http://bus:8018/bus/coredb", "  COREDB_URL: http://bna-coredb:8012")
    hallados = problemas(_repo(tmp_path / "mal", configmaps=configmaps))
    assert any("bna-configuracion" in p and "COREDB_URL" in p for p in hallados), hallados


def test_un_deployment_de_modulo_con_la_direccion_directa(tmp_path):
    modulo = DEPLOYMENT_MODULO.replace("http://bus:8018/bus/coredb/coredb/salud", "http://coredb:8012/coredb/salud")
    hallados = problemas(_repo(tmp_path, modulo=modulo))
    assert any("cuentas" in p and "k8s" in p for p in hallados), hallados


def test_un_deployment_de_modulo_que_lee_el_configmap_del_bus(tmp_path):
    modulo = DEPLOYMENT_MODULO.replace("- configMapRef: { name: bna-configuracion }",
                                       "- configMapRef: { name: bna-configuracion }\n            "
                                       "- configMapRef: { name: bna-bus }")
    hallados = problemas(_repo(tmp_path, modulo=modulo))
    assert any("cuentas" in p and "bna-bus" in p for p in hallados), hallados


def test_la_direccion_directa_en_env_example(tmp_path):
    hallados = problemas(_repo(tmp_path, env_ejemplo="CORE_BASE_URL=http://coredb:8012\n"))
    assert any(".env.example" in p for p in hallados), hallados


def test_la_direccion_directa_como_valor_por_omision_de_un_modulo(tmp_path):
    hallados = problemas(_repo(tmp_path, config_modulo='core_base_url: str = "http://localhost:8012"\n'))
    assert any("CUENTAS/config.py" in p for p in hallados), hallados


def test_el_repositorio_no_tiene_la_direccion_directa_de_coredb_en_ningun_modulo():
    assert problemas(REPO) == []


def test_la_direccion_directa_en_el_env_example_de_la_billetera(tmp_path):
    repo = _repo(tmp_path)
    chaski = repo / "billetera-chaski" / "backend"
    chaski.mkdir(parents=True)
    (chaski / ".env.example").write_text("COREDB_URL=http://127.0.0.1:8012\n")
    hallados = problemas(repo)
    assert any("billetera-chaski/backend/.env.example" in p for p in hallados), hallados
