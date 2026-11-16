"""Pruebas de Evaluación. Las de integración usan COREDB y la base integrada reales
(scripts/pruebas_integracion.sh); sin EVALUACION_TEST_COREDB se omiten."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from EVALUACION.main import crear_app
from EVALUACION.tests import ayudas


@pytest.fixture(scope="session")
def admin():
    if not ayudas.COREDB:
        pytest.skip("Requiere EVALUACION_TEST_COREDB (scripts/pruebas_integracion.sh).")
    return ayudas.token_admin()


@pytest.fixture(scope="session")
def analista(admin):
    """(token, username) de un analista registrado: puede evaluar y decidir."""
    return ayudas.analista_registrado(admin)


@pytest.fixture
def cliente(admin):
    return ayudas.cliente_nuevo(admin)


@pytest.fixture
def sol():
    return ayudas.SolFalso()


@pytest.fixture
def api(admin, sol):
    contexto = ayudas.contexto(sol)
    with TestClient(crear_app(contexto=contexto)) as cliente_http:
        cliente_http.contexto = contexto
        yield cliente_http
