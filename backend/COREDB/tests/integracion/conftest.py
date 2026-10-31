"""Pruebas contra el contenedor de la base. Las prepara scripts/pruebas_integracion.sh."""

import os

import pymysql
import pytest
from sqlalchemy.exc import OperationalError

ACTIVAS = os.environ.get("COREDB_INTEGRACION") == "1"


def pytest_collection_modifyitems(items):
    if ACTIVAS:
        return
    omitir = pytest.mark.skip(reason="Requiere scripts/pruebas_integracion.sh.")
    for item in items:
        if "integracion" in str(item.fspath):
            item.add_marker(omitir)


@pytest.fixture(scope="session")
def admin():
    conexion = pymysql.connect(
        host=os.environ.get("CORE_DB_HOST", "127.0.0.1"),
        port=int(os.environ["CORE_DB_PORT"]),
        user="bna_admin_user",
        password=os.environ["CORE_DB_ADMIN_PASSWORD"],
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )
    yield conexion
    conexion.close()


@pytest.fixture
def consulta(admin):
    def _consulta(sql, *parametros):
        with admin.cursor() as cursor:
            cursor.execute(sql, parametros)
            return cursor.fetchall()

    return _consulta


@pytest.fixture
def fallar_una_vez(monkeypatch):
    """Reemplaza `llamar` en `modulo`: el primer intento recibe `codigo` de MySQL y los
    demás llegan a la base. Si un endpoint no usa con_reintentos, el error no se repite."""
    from COREDB.database import llamar

    def _fallar(modulo, codigo):
        intentos = []

        def doble(db, *args, **kwargs):
            intentos.append(args[0])
            if len(intentos) == 1:
                raise OperationalError("CALL", {}, pymysql.err.OperationalError(codigo, "simulado"))
            return llamar(db, *args, **kwargs)

        monkeypatch.setattr(modulo, "llamar", doble)
        return intentos

    return _fallar
