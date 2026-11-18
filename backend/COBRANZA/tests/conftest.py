"""Pruebas de Cobranza. Las de integración usan COREDB y la base integrada reales
(scripts/pruebas_integracion.sh); sin COBRANZA_TEST_COREDB se omiten."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from COBRANZA.main import crear_app
from COBRANZA.tests import ayudas


@pytest.fixture(scope="session")
def admin():
    if not ayudas.COREDB:
        pytest.skip("Requiere COBRANZA_TEST_COREDB (scripts/pruebas_integracion.sh).")
    return ayudas.token_admin()


@pytest.fixture(scope="session")
def operador(admin):
    """(token, username) de un OPERADOR: cobra la cuota con su propia sesión."""
    return ayudas.persona(admin, "OPERADOR")


@pytest.fixture(scope="session")
def auditor(admin):
    return ayudas.persona(admin, "AUDITOR")


@pytest.fixture
def api(admin):
    with TestClient(crear_app(contexto=ayudas.contexto())) as cliente_http:
        yield cliente_http


@pytest.fixture
def credito(api, admin, operador):
    """Un crédito desembolsado, con su cuenta con fondos y sus cuotas."""
    datos = ayudas.credito_desembolsado(admin, operador[0])
    detalle = api.get(f"/api/v1/creditos/{datos['codCredito']}", headers=ayudas.cabeceras(operador[0])).json()
    datos["cuotas"] = detalle["cuotas"]
    return datos
