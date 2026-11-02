"""Hashing y autenticación contra un MySQL real con el esquema `bna`.

Escribe en la BD y necesita una carga limpia, por eso solo corre con
BNA_INTEGRACION_MYSQL=1. Ver "Pruebas de integración" en AUTENTICACION.md.
"""

import os
import re
import statistics
import threading
import time
import uuid
from pathlib import Path

import pymysql
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from CORE.api import montar_en
from CORE.config import get_settings
from CORE.database import get_session_factory
from CORE.exceptions import NotFoundError, ValidationError
from CORE.services import usuariossvc
from CORE.utils.hashing import hash_bcrypt, verify_password

pytestmark = pytest.mark.skipif(
    os.environ.get("BNA_INTEGRACION_MYSQL") != "1",
    reason="Requiere BNA_INTEGRACION_MYSQL=1 y una BD `bna` recién cargada.",
)

BACKEND = Path(__file__).resolve().parents[3]
SQL = (BACKEND / "Infraestructura - BD/Trabajo_hecho/BD/99_bna_unificado.sql").read_text(
    encoding="utf-8"
)
SEMILLAS = re.findall(r"^\s*\('[0-9a-f-]{36}','([a-z.]+)','[^']+','[A-Z]+',SHA2\('([^']+)',256\)", SQL, re.M)
CLAVE = "clave-segura-1"


def conn():
    ajustes = get_settings()
    return pymysql.connect(
        host=ajustes.db_host,
        port=ajustes.db_port,
        user=ajustes.db_user,
        password=ajustes.db_password,
        database=ajustes.db_name,
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )


def sql(q, *a):
    with conn() as c, c.cursor() as cur:
        cur.execute(q, a)
        return cur.fetchall()


def fila(u):
    return sql("select hash_password h, algoritmo_hash a, version_hash v, activo from usuario_sistema where username=%s", u)[0]


def eventos(id_entidad):
    return sql("select actor, detalle from auditoria_evento where accion='MIGRAR_HASH_PASSWORD' and id_entidad=%s", id_entidad)


def sembrar(password=CLAVE, activo=1):
    u, i = "u" + uuid.uuid4().hex[:12], str(uuid.uuid4())
    sql("insert into usuario_sistema (id_usuario,username,nombre,rol,hash_password,activo) values (%s,%s,'P','ASESOR',SHA2(%s,256),%s)",
        i, u, password, activo)
    return u, i


@pytest.fixture
def db():
    s = get_session_factory()()
    yield s
    s.close()


def test_semillas_detectadas():
    assert len(SEMILLAS) == 5


@pytest.mark.parametrize("n", range(5))
def test_semilla_migra_persiste_y_audita(db, n):
    username, password = SEMILLAS[n]
    assert fila(username)["a"] == "SHA256"
    u = usuariossvc.autenticar(db, username=username, password=password)
    f = fila(username)
    assert (f["a"], f["v"], len(f["h"])) == ("BCRYPT", "v2", 60)
    assert verify_password(password, f["h"], "BCRYPT")
    ev = eventos(u.id_usuario)
    assert len(ev) == 1 and ev[0]["actor"] == username and f["h"] not in str(ev[0]["detalle"])
    usuariossvc.autenticar(db, username=username, password=password)
    assert len(eventos(u.id_usuario)) == 1


def test_clave_incorrecta_no_toca_fila(db):
    u, i = sembrar()
    antes = fila(u)
    with pytest.raises(NotFoundError):
        usuariossvc.autenticar(db, username=u, password="otra-clave")
    assert fila(u) == antes and not eventos(i)


def test_inexistente(db):
    with pytest.raises(NotFoundError):
        usuariossvc.autenticar(db, username="no.existe", password=CLAVE)


def test_inactivo_no_migra(db):
    u, i = sembrar(activo=0)
    with pytest.raises(ValidationError) as e:
        usuariossvc.autenticar(db, username=u, password=CLAVE)
    assert e.value.code == "USUARIO_INACTIVO" and fila(u)["a"] == "SHA256" and not eventos(i)


def test_hash_sha256_corrupto(db):
    u, _ = sembrar()
    sql("update usuario_sistema set hash_password=%s where username=%s", "ñ" * 64, u)
    with pytest.raises(NotFoundError) as e:
        usuariossvc.autenticar(db, username=u, password=CLAVE)
    assert e.value.code == "CREDENCIALES_INVALIDAS"


@pytest.mark.parametrize("h", ["", "no-es-un-hash", "$2b$12$corto", "ñ" * 60])
def test_hash_bcrypt_malformado(db, h):
    u, _ = sembrar()
    sql("update usuario_sistema set hash_password=%s, algoritmo_hash='BCRYPT' where username=%s", h, u)
    with pytest.raises(NotFoundError):
        usuariossvc.autenticar(db, username=u, password=CLAVE)


def test_algoritmo_desconocido(db):
    u, _ = sembrar()
    sql("update usuario_sistema set algoritmo_hash='MD5' where username=%s", u)
    with pytest.raises(NotFoundError):
        usuariossvc.autenticar(db, username=u, password=CLAVE)


def test_legada_larga_sigue_en_sha256(db):
    largo = "a" * 73
    u, i = sembrar(largo)
    assert usuariossvc.autenticar(db, username=u, password=largo)
    assert fila(u)["a"] == "SHA256" and not eventos(i)


def test_surrogate(db):
    u, _ = sembrar()
    with pytest.raises(ValidationError) as e:
        usuariossvc.autenticar(db, username=u, password="clave\ud800x")
    assert e.value.status_code == 422


def test_commit_fallido_revierte_y_autentica(db, monkeypatch):
    u, i = sembrar()
    def falla():
        raise OperationalError("COMMIT", {}, Exception("caida"))
    monkeypatch.setattr(db, "commit", falla)
    r = usuariossvc.autenticar(db, username=u, password=CLAVE)
    monkeypatch.undo()
    assert usuariossvc.vista_publica(r)["username"] == u
    assert r.algoritmo_hash == "SHA256" and fila(u)["a"] == "SHA256" and not eventos(i)
    usuariossvc.autenticar(db, username=u, password=CLAVE)
    assert fila(u)["a"] == "BCRYPT" and len(eventos(i)) == 1


def test_logins_concurrentes():
    u, i = sembrar()
    barrera, res = threading.Barrier(8), []
    def login():
        s = get_session_factory()()
        try:
            barrera.wait()
            res.append(usuariossvc.autenticar(s, username=u, password=CLAVE).username)
        except Exception as exc:
            res.append(repr(exc))
        finally:
            s.close()
    hs = [threading.Thread(target=login) for _ in range(8)]
    for h in hs:
        h.start()
    for h in hs:
        h.join()
    assert res == [u] * 8, res
    f = fila(u)
    assert f["a"] == "BCRYPT" and verify_password(CLAVE, f["h"], "BCRYPT")
    assert len(eventos(i)) == 1


@pytest.fixture
def http():
    app = FastAPI()
    montar_en(app)
    cliente = TestClient(app, raise_server_exceptions=False)
    admin, _ = sembrar()
    sql("update usuario_sistema set rol='ADMINISTRADOR' where username=%s", admin)
    r = cliente.post("/core/auth/login", json={"username": admin, "password": CLAVE})
    assert r.status_code == 200, r.text
    cliente.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return cliente


def alta(http, username, password):
    return http.post("/core/usuarios", json={"username": username, "nombre": "N", "password": password, "rol": "OPERADOR"})


def test_http_crear_y_login(http, db):
    u = "h" + uuid.uuid4().hex[:12]
    r = alta(http, u, CLAVE)
    assert r.status_code == 201, r.text
    assert "hash" not in r.text
    f = fila(u)
    assert (f["a"], f["v"], len(f["h"])) == ("BCRYPT", "v2", 60)
    assert usuariossvc.autenticar(db, username=u, password=CLAVE).username == u
    a = sql("select detalle from auditoria_evento where accion='CREAR_USUARIO' and id_entidad=%s", r.json()["id_usuario"])
    assert len(a) == 1 and f["h"] not in str(a[0]["detalle"])


@pytest.mark.parametrize("password", ["a" * 73, "clave\x00segura"])
def test_http_password_no_admitida(http, password):
    u = "h" + uuid.uuid4().hex[:12]
    r = alta(http, u, password)
    assert r.status_code == 422, r.text
    assert not sql("select 1 from usuario_sistema where username=%s", u)


def test_http_surrogate_json_crudo(http):
    u = "h" + uuid.uuid4().hex[:12]
    cuerpo = '{"username":"%s","nombre":"N","password":"clave\\ud800segura","rol":"OPERADOR"}' % u
    r = http.post("/core/usuarios", content=cuerpo, headers={"content-type": "application/json"})
    assert r.status_code == 422, r.text


def test_http_login_con_correlation_id_largo(http):
    u, _ = sembrar()
    r = http.post("/core/auth/login", json={"username": u, "password": CLAVE},
                  headers={"x-correlation-id": "c" * 37})
    assert r.status_code == 200, r.text


def test_tiempos_uniformes(db):
    from CORE.utils import hashing
    if not hasattr(hashing, "simular_verificacion"):
        pytest.skip("solo tarea 2")
    bc, _ = sembrar()
    sql("update usuario_sistema set hash_password=%s, algoritmo_hash='BCRYPT' where username=%s", hash_bcrypt(CLAVE), bc)
    sh, _ = sembrar()
    mal, _ = sembrar()
    sql("update usuario_sistema set hash_password='x', algoritmo_hash='BCRYPT' where username=%s", mal)
    casos = {"inexistente": ("no.existe", "otra-clave"), "bcrypt": (bc, "otra-clave"), "sha256": (sh, "otra-clave"),
             "malformado": (mal, "otra-clave"), "larga": (bc, "a" * 80)}
    t = {}
    for k, (u, p) in casos.items():
        m = []
        for _ in range(7):
            s = time.perf_counter()
            with pytest.raises(NotFoundError):
                usuariossvc.autenticar(db, username=u, password=p)
            m.append(time.perf_counter() - s)
        t[k] = statistics.median(m) * 1000
    assert max(t.values()) / min(t.values()) < 1.2


def test_http_login_fallido_uniforme(http):
    bc, _ = sembrar()
    sql("update usuario_sistema set hash_password=%s, algoritmo_hash='BCRYPT' where username=%s", hash_bcrypt(CLAVE), bc)
    sh, _ = sembrar()
    inactivo, _ = sembrar(activo=0)
    bc_inactivo, _ = sembrar(activo=0)
    sql("update usuario_sistema set hash_password=%s, algoritmo_hash='BCRYPT' where username=%s", hash_bcrypt(CLAVE), bc_inactivo)
    casos = {"inexistente": ("no.existe", CLAVE), "bcrypt": (bc, "otra-clave"), "sha256": (sh, "otra-clave"),
             "inactivo_clave_correcta": (inactivo, CLAVE), "inactivo_clave_mala": (inactivo, "otra-clave"),
             "bcrypt_inactivo": (bc_inactivo, CLAVE)}
    t, cuerpos = {}, set()
    for k, (u, p) in casos.items():
        m = []
        for _ in range(7):
            s = time.perf_counter()
            r = http.post("/core/auth/login", json={"username": u, "password": p})
            m.append(time.perf_counter() - s)
            assert r.status_code == 401, (k, r.text)
            cuerpos.add(r.text)
        t[k] = statistics.median(m) * 1000
    assert len(cuerpos) == 1
    assert max(t.values()) / min(t.values()) < 1.2, t
