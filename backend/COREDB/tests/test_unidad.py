"""Pruebas sin base de datos."""

import re
import uuid
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from COREDB.auth import Actor, actor_actual
from COREDB.config import Settings
from COREDB import transacciones
from COREDB.database import INIT_COMMAND, UuidBinario, get_engine, llamar
from COREDB.errores import ErrorCoreDb, registrar_manejadores
from COREDB.main import app
from COREDB.models import Base
from COREDB.scripts.exporta_openapi import ARCHIVO, especificacion


def test_uuid_ida_y_vuelta():
    tipo, valor = UuidBinario(), uuid.uuid4()
    binario = tipo.process_bind_param(valor, None)
    assert len(binario) == 16
    assert tipo.process_result_value(binario, None) == valor
    assert tipo.process_bind_param(None, None) is None


def test_url_sin_base_y_con_usuario_de_la_aplicacion():
    url = make_url(Settings(_env_file=None, port=3307, app_password="p@ss/w").database_url)
    assert (url.username, url.port, url.database) == ("bna_app_user", 3307, None)
    assert url.password == "p@ss/w"


def test_init_command_es_una_sola_sentencia():
    assert ";" not in INIT_COMMAND
    assert "time_zone = '+00:00'" in INIT_COMMAND


def test_llamar_rechaza_nombres_inseguros():
    with pytest.raises(ValueError):
        llamar(None, "core.x(); DROP TABLE y")


def test_validacion_no_devuelve_valores():
    prueba = FastAPI()
    registrar_manejadores(prueba)

    @prueba.post("/x")
    def x(datos: dict[str, int]) -> int:
        return 1

    respuesta = TestClient(prueba).post("/x", json={"clave": "secreto"})
    assert respuesta.status_code == 422
    assert "secreto" not in respuesta.text


def test_autenticacion_es_reemplazable():
    prueba = FastAPI()

    @prueba.get("/quien")
    def quien(actor: Actor = Depends(actor_actual)) -> str:
        return actor.usuario

    cliente = TestClient(prueba)
    assert cliente.get("/quien", headers={"X-Actor": "ana"}).json() == "ana"

    def jwt_de_prueba() -> Actor:
        raise HTTPException(status_code=401)

    prueba.dependency_overrides[actor_actual] = jwt_de_prueba
    assert cliente.get("/quien").status_code == 401


def test_actor_en_blanco_se_rechaza():
    prueba = FastAPI()

    @prueba.get("/quien")
    def quien(actor: Actor = Depends(actor_actual)) -> str:
        return actor.usuario

    cliente = TestClient(prueba)
    assert cliente.get("/quien", headers={"X-Actor": "   "}).status_code == 422
    assert cliente.get("/quien", headers={"X-Actor": " ana "}).json() == "ana"


def test_spec_publicada_al_dia():
    assert ARCHIVO.read_text(encoding="utf-8") == especificacion()


def test_escrituras_solo_por_procedimientos():
    prohibido = re.compile(
        r"\b(INSERT\s+INTO|UPDATE\s+\w|DELETE\s+FROM|REPLACE\s+INTO|TRUNCATE\s+TABLE)\b"
        r"|\.(add|add_all|delete|merge|update|bulk_\w+)\("
        r"|\b(insert|update|delete)\("
    )
    paquete = Path(ARCHIVO).parent
    fuentes = [f for f in paquete.rglob("*.py") if "tests" not in f.parts]
    assert fuentes
    for fuente in fuentes:
        assert not prohibido.search(fuente.read_text(encoding="utf-8")), fuente


def test_modelos_declaran_su_base():
    assert all(t.schema for t in Base.metadata.tables.values())


def test_engine_oculta_parametros():
    assert get_engine().hide_parameters is True


def test_llamar_rechaza_salto_de_linea_final():
    with pytest.raises(ValueError):
        llamar(None, "core.crear_usuario\n")


class _DbFalsa:
    def __init__(self):
        self.commits = self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def _deadlock():
    return OperationalError("CALL", {}, Exception(1213, "Deadlock found"))


def test_reintenta_tras_deadlock(monkeypatch):
    monkeypatch.setattr(transacciones.time, "sleep", lambda _: None)
    db, intentos = _DbFalsa(), []

    def operacion():
        intentos.append(1)
        if len(intentos) < 3:
            raise _deadlock()
        return "hecho"

    assert transacciones.con_reintentos(db, operacion, nombre="x") == "hecho"
    assert (db.rollbacks, db.commits) == (2, 1)


def test_reintentos_agotados_503(monkeypatch):
    monkeypatch.setattr(transacciones.time, "sleep", lambda _: None)

    def operacion():
        raise _deadlock()

    with pytest.raises(ErrorCoreDb) as exc:
        transacciones.con_reintentos(_DbFalsa(), operacion, nombre="x")
    assert exc.value.status_code == 503


def test_deadlock_fuera_de_reintentos_responde_503():
    prueba = FastAPI()
    registrar_manejadores(prueba)

    @prueba.get("/x")
    def x():
        raise _deadlock()

    respuesta = TestClient(prueba, raise_server_exceptions=False).get("/x")
    assert respuesta.status_code == 503


def test_docs_disponibles():
    assert TestClient(app).get("/docs").status_code == 200
