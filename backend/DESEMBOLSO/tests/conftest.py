"""Pruebas de Desembolso. Las de integración usan COREDB y la base integrada reales
(scripts/pruebas_integracion.sh); sin DESEMBOLSO_TEST_COREDB se omiten."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from DESEMBOLSO.main import crear_app
from DESEMBOLSO.tests import ayudas


@pytest.fixture(scope="session")
def admin():
    if not ayudas.COREDB:
        pytest.skip("Requiere DESEMBOLSO_TEST_COREDB (scripts/pruebas_integracion.sh).")
    return ayudas.token_admin()


@pytest.fixture(scope="session")
def operador(admin):
    """(token, username) de un OPERADOR: verifica el documento, prepara, valida y confirma."""
    return ayudas.persona(admin, "OPERADOR")


@pytest.fixture
def api(admin):
    with TestClient(crear_app(contexto=ayudas.contexto())) as cliente_http:
        yield cliente_http
