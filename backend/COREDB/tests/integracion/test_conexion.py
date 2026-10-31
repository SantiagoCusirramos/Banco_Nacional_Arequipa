import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from COREDB.database import get_session_factory
from COREDB.main import app


@pytest.fixture
def sesion():
    with get_session_factory()() as s:
        yield s


def test_sesion_en_utc_y_modo_estricto(sesion):
    zona, modo = sesion.execute(text("SELECT @@session.time_zone, @@session.sql_mode")).one()
    assert zona == "+00:00"
    assert "STRICT_ALL_TABLES" in modo


def test_conecta_con_el_rol_de_la_api(sesion):
    assert "bna_api" in sesion.execute(text("SELECT CURRENT_ROLE()")).scalar()
    assert sesion.execute(text("SELECT SUBSTRING_INDEX(USER(), '@', 1)")).scalar() == "bna_app_user"


def test_la_aplicacion_no_borra(sesion):
    with pytest.raises(Exception, match="denied"):
        sesion.execute(text("DELETE FROM core.agencia"))


def test_arranque_verifica_configuracion_y_salud():
    with TestClient(app) as cliente:
        assert cliente.get("/coredb/salud").json() == {"estado": "ok"}


@pytest.mark.parametrize(
    "tabla",
    ["cuentas.cuenta_ahorro", "cuentas.titularidad", "cuentas.movimiento",
     "tarjetas.tarjeta", "tarjetas.historial_estado_tarjeta"],
)
def test_la_aplicacion_no_inserta_directamente(sesion, tabla):
    with pytest.raises(Exception, match="denied"):
        sesion.execute(text(f"INSERT INTO {tabla} () VALUES ()"))


def test_excepcion_no_contiene_parametros(sesion):
    secreto = "$2b$12$hashquenodebeaparecer"
    with pytest.raises(DBAPIError) as exc:
        sesion.execute(text("SELECT no_existe FROM core.moneda WHERE cod_moneda = :h"), {"h": secreto})
    assert secreto not in str(exc.value)
