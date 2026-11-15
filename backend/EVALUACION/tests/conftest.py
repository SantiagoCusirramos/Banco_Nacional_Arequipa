"""Pruebas de Evaluación.

Las que usan la base corren solo con EVALUACION_TEST_MYSQL (por ejemplo
mysql+pymysql://root:clave@127.0.0.1:3306), un MySQL 8.4 de pruebas: se crea desde cero la base
bna_evaluacion_pruebas con el esquema real y la API se conecta con el usuario de permisos mínimos.
scripts/pruebas_integracion.sh lo prepara en contenedores. Sin esa variable, esas pruebas se omiten.

COREDB y SOL se reemplazan por transportes en memoria. Los perfiles salen del mapa real de
permisos de COREDB (COREDB/permisos.py) y los contratos de SOL se validan con su propio código.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url

from EVALUACION import esquema
from EVALUACION.main import crear_app
from EVALUACION.tests.ayudas import BASE, CLAVE_APP, URL_MYSQL, USUARIO, SolFalso, _root, construir_contexto


@pytest.fixture(scope="session")
def base_de_datos():
    if not URL_MYSQL:
        pytest.skip("Requiere EVALUACION_TEST_MYSQL (scripts/pruebas_integracion.sh).")
    conexion = _root()
    with conexion.cursor() as cursor:
        cursor.execute(f"DROP DATABASE IF EXISTS `{BASE}`")
        esquema.instalar(cursor, BASE, USUARIO, CLAVE_APP)
    conexion.close()
    url = make_url(URL_MYSQL)
    yield f"mysql+pymysql://{USUARIO}:{CLAVE_APP}@{url.host}:{url.port or 3306}/{BASE}?charset=utf8mb4"
    conexion = _root()
    with conexion.cursor() as cursor:
        cursor.execute(f"DROP DATABASE IF EXISTS `{BASE}`")
        cursor.execute(f"DROP USER IF EXISTS '{USUARIO}'@'%'")
    conexion.close()


@pytest.fixture
def root(base_de_datos):
    """Conexión administrativa a la base de pruebas (vacía las tablas antes de cada prueba)."""
    conexion = _root()
    with conexion.cursor() as cursor:
        cursor.execute(f"USE `{BASE}`")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        for tabla in ("eva_historial", "eva_envio", "eva_cuota", "eva_aprobacion", "eva_situacion_financiera",
                      "eva_evaluacion", "eva_expediente", "eva_correlativo"):
            cursor.execute(f"TRUNCATE TABLE {tabla}")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    yield conexion
    conexion.close()


@pytest.fixture
def sol():
    return SolFalso()


@pytest.fixture
def api(base_de_datos, root, sol):
    contexto = construir_contexto(base_de_datos, sol)
    with TestClient(crear_app(contexto=contexto)) as cliente:
        cliente.contexto = contexto
        yield cliente
