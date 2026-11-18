"""Pruebas de Seguridad. Las unitarias usan un COREDB en memoria (coredb_simulado.py); las de
integración, COREDB y la base integrada reales a través del Bus (scripts/pruebas_integracion.sh)."""
import pytest
from fastapi.testclient import TestClient

from seguridad.app import Contexto, crear_app
from seguridad.auth import Verificador
from seguridad.config import Config
from seguridad.coredb import ClienteCoreDb
from seguridad.tests.coredb_simulado import SECRETO_SERVICIO, CoreDbSimulado

CLAVE = "clave-de-pruebas-" + "k" * 32


@pytest.fixture
def coredb():
    return CoreDbSimulado()


@pytest.fixture
def config():
    return Config(clave=CLAVE, servicio_secreto=SECRETO_SERVICIO, coredb_url="http://coredb.prueba",
                  sellado_seg=0, sellado_antiguedad_seg=60)


@pytest.fixture
def ctx(coredb, config):
    cliente = ClienteCoreDb(config.coredb_url, config.servicio_usuario, config.servicio_secreto,
                            transporte=coredb.transporte())
    return Contexto(config, cliente, Verificador(cliente, recordar_seg=0))


@pytest.fixture
def api(ctx):
    with TestClient(crear_app(contexto=ctx), headers={"X-Correlation-ID": "pytest-seguridad"}) as cliente:
        yield cliente


def como(usuario: str) -> dict:
    return {"Authorization": f"Bearer tok-{usuario}"}
