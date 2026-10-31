"""Pruebas del JWT: emisión, validación, login, /me y permisos por rol.

Usan SQLite en memoria (solo las tablas usuario_sistema y auditoria_evento),
así que no requieren MySQL.
"""

import base64
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from CORE.api import montar_en
from CORE.config import get_settings
from CORE.dependencies import db_session, requiere_permiso
from CORE.exceptions import AuthenticationError
from CORE.models import AuditoriaEvento, UsuarioSistema
from CORE.services import authsvc, usuariossvc
from CORE.utils import tokens

CLAVE = "k" * 40
PASSWORD = "Clave-Segura-123"


@pytest.fixture(autouse=True)
def _entorno(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", CLAVE)
    monkeypatch.setenv("ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    UsuarioSistema.__table__.create(engine)
    AuditoriaEvento.__table__.create(engine)
    sesion = sessionmaker(bind=engine, expire_on_commit=False)()
    usuariossvc.crear_usuario(sesion, username="admin.t", nombre="Admin", password=PASSWORD, rol="ADMINISTRADOR")
    usuariossvc.crear_usuario(sesion, username="oper.t", nombre="Oper", password=PASSWORD, rol="OPERADOR")
    yield sesion
    sesion.close()


@pytest.fixture()
def client(db):
    app = FastAPI()
    montar_en(app)

    @app.get("/solo-auditores", dependencies=[Depends(requiere_permiso("VER_AUDITORIA"))])
    def solo_auditores():
        return {"ok": True}

    app.dependency_overrides[db_session] = lambda: db
    return TestClient(app)


def _login(client, username="admin.t", password=PASSWORD):
    return client.post("/core/auth/login", json={"username": username, "password": password})


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------- tokens (unidad)
def test_token_contiene_claims_esperados():
    token, expires_in = tokens.crear_token_acceso(id_usuario="u-1", username="ana", rol="ASESOR")
    claims = tokens.decodificar_token(token)
    assert claims["sub"] == "u-1" and claims["username"] == "ana" and claims["rol"] == "ASESOR"
    assert claims["iss"] == tokens.ISSUER and claims["type"] == "access" and claims["jti"]
    assert expires_in == 30 * 60
    assert claims["exp"] - claims["iat"] == 30 * 60


def test_token_no_lleva_password_ni_hash():
    token, _ = tokens.crear_token_acceso(id_usuario="u-1", username="ana", rol="ASESOR")
    assert set(tokens.decodificar_token(token)) == {"sub", "username", "rol", "type", "iss", "iat", "exp", "jti"}


def test_token_expirado_da_401_token_expirado():
    claims = {"sub": "u", "iss": tokens.ISSUER, "type": "access",
              "iat": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
              "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())}
    viejo = jose_jwt.encode(claims, CLAVE, algorithm="HS256")
    with pytest.raises(Exception) as e:
        tokens.decodificar_token(viejo)
    assert e.value.status_code == 401 and e.value.code == "TOKEN_EXPIRADO"


def test_firma_con_otra_clave_se_rechaza():
    falso = jose_jwt.encode({"sub": "u", "iss": tokens.ISSUER, "type": "access",
                             "iat": 1, "exp": 4102444800}, "otra-clave-" * 4, algorithm="HS256")
    with pytest.raises(Exception) as e:
        tokens.decodificar_token(falso)
    assert e.value.code == "TOKEN_INVALIDO"


def test_alg_none_se_rechaza():
    b64 = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()
    sin_firma = f"{b64({'alg': 'none', 'typ': 'JWT'})}.{b64({'sub': 'u', 'iss': tokens.ISSUER, 'type': 'access', 'iat': 1, 'exp': 4102444800})}."
    with pytest.raises(Exception) as e:
        tokens.decodificar_token(sin_firma)
    assert e.value.code == "TOKEN_INVALIDO"


def test_emisor_incorrecto_o_tipo_incorrecto_se_rechaza():
    base = {"sub": "u", "iat": 1, "exp": 4102444800}
    for extra in ({"iss": "otro", "type": "access"}, {"iss": tokens.ISSUER, "type": "refresh"}):
        tk = jose_jwt.encode({**base, **extra}, CLAVE, algorithm="HS256")
        with pytest.raises(Exception) as e:
            tokens.decodificar_token(tk)
        assert e.value.code == "TOKEN_INVALIDO"


def test_clave_corta_fuera_de_desarrollo_falla(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "corta")
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError):
        tokens.crear_token_acceso(id_usuario="u", username="a", rol="ASESOR")


# ------------------------------------------------------------------ login
def test_login_ok_devuelve_token_y_usuario_sin_hash(client):
    r = _login(client)
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer" and body["expires_in"] == 1800
    assert body["usuario"]["username"] == "admin.t" and body["usuario"]["rol"] == "ADMINISTRADOR"
    assert "hash" not in r.text and PASSWORD not in r.text
    assert tokens.decodificar_token(body["access_token"])["sub"] == body["usuario"]["id_usuario"]


def test_login_registra_auditoria(client, db):
    _login(client)
    assert db.query(AuditoriaEvento).filter_by(accion="LOGIN", actor="admin.t").count() == 1


def test_login_clave_incorrecta_y_usuario_inexistente_responden_igual(client):
    a = _login(client, password="incorrecta")
    b = _login(client, username="no.existe")
    assert a.status_code == b.status_code == 401
    assert a.json()["error"] == b.json()["error"]
    assert a.headers["www-authenticate"] == "Bearer"


def test_login_usuario_inactivo_responde_igual_que_clave_incorrecta(client, db):
    u = db.query(UsuarioSistema).filter_by(username="oper.t").one()
    u.activo = False
    db.commit()
    inactivo = _login(client, "oper.t")
    incorrecta = _login(client, password="incorrecta")
    assert inactivo.status_code == incorrecta.status_code == 401
    assert inactivo.json() == incorrecta.json()
    assert inactivo.headers["www-authenticate"] == "Bearer"


def test_password_no_admitida_da_el_mismo_401(db):
    with pytest.raises(AuthenticationError) as e:
        authsvc.iniciar_sesion(db, username="admin.t", password="clave\ud800segura")
    assert e.value.status_code == 401 and e.value.code == "CREDENCIALES_INVALIDAS"


# ---------------------------------------------------------------- /me y permisos
def test_me_con_token_valido(client):
    token = _login(client).json()["access_token"]
    r = client.get("/core/auth/me", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["username"] == "admin.t" and "VER_AUDITORIA" in r.json()["acciones"]


def test_me_sin_token_o_con_token_basura_da_401(client):
    assert client.get("/core/auth/me").status_code == 401
    assert client.get("/core/auth/me", headers=_auth("esto.no.es.jwt")).status_code == 401
    assert client.get("/core/auth/me", headers={"Authorization": "Basic abc"}).status_code == 401


def test_permiso_por_rol(client):
    t_admin = _login(client).json()["access_token"]
    t_oper = _login(client, "oper.t").json()["access_token"]
    assert client.get("/solo-auditores", headers=_auth(t_admin)).status_code == 200
    r = client.get("/solo-auditores", headers=_auth(t_oper))
    assert r.status_code == 403 and r.json()["error"]["code"] == "PERMISO_DENEGADO"
    assert client.get("/solo-auditores").status_code == 401


def test_usuario_desactivado_pierde_acceso_aunque_el_token_no_venza(client, db):
    token = _login(client, "oper.t").json()["access_token"]
    u = db.query(UsuarioSistema).filter_by(username="oper.t").one()
    u.activo = False
    db.commit()
    r = client.get("/core/auth/me", headers=_auth(token))
    assert r.status_code == 401 and r.json()["error"]["code"] == "USUARIO_NO_VIGENTE"


def test_cambio_de_rol_aplica_de_inmediato(client, db):
    token = _login(client, "oper.t").json()["access_token"]
    assert client.get("/solo-auditores", headers=_auth(token)).status_code == 403
    db.query(UsuarioSistema).filter_by(username="oper.t").one().rol = "AUDITOR"
    db.commit()
    assert client.get("/solo-auditores", headers=_auth(token)).status_code == 200


# ------------------------------------------------------- validación sin eco (#10)
def test_login_422_no_repite_la_password(client):
    secreta = "Clave-Filtrada-" * 10  # supera el máximo de 128 caracteres
    r = _login(client, password=secreta)
    assert r.status_code == 422
    assert "Clave-Filtrada" not in r.text
