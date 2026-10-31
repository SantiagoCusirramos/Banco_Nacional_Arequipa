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
def admin(request):
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


@pytest.fixture(scope="session")
def datos_base(admin):
    """Clientes de las pruebas; lo demás viene de sql/bna_datos_dev.sql."""
    sentencias = [
        "INSERT IGNORE INTO clientes.verificacion_captacion (id_verificacion_captacion, estado_habilitante) "
        "VALUES ('VC-1', 'HABILITADO'), ('VC-2', 'HABILITADO')",
        "INSERT IGNORE INTO clientes.cliente (cod_cliente, tipo_documento, numero_documento, nombres, "
        "apellido_paterno, correo, celular, estado_cliente, id_verificacion_captacion, version_contrato) VALUES "
        "('C001', 'DNI', '70000001', 'Juan', 'Perez', 'j@example.com', '959000001', 'ACTIVO', 'VC-1', 'v1'), "
        "('C002', 'DNI', '70000002', 'Ana', 'Diaz', 'a@example.com', '959000002', 'ACTIVO', 'VC-2', 'v1')",
    ]
    with admin.cursor() as cursor:
        for sentencia in sentencias:
            cursor.execute(sentencia)


@pytest.fixture
def abrir_cuenta(datos_base):
    from COREDB.database import get_session_factory, llamar

    def _abrir(moneda="PEN"):
        import uuid

        sufijo = uuid.uuid4().int % 10**16
        num_cuenta = f"CTA-{sufijo:016d}"
        with get_session_factory()() as db:
            llamar(
                db, "cuentas.abrir_cuenta",
                num_cuenta, f"{sufijo:020d}", moneda, "INDIVIDUAL", "AQP01", '["C001"]', "pruebas",
            )
            db.commit()
        return num_cuenta

    return _abrir
