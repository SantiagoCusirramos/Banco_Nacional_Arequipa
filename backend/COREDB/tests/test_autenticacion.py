"""Autenticación sin base de datos: tokens, configuración, permisos y rutas."""

import time
import uuid

import jwt
import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from COREDB import auth, permisos, tokens
from COREDB.auth import Actor, actor_actual
from COREDB.config import Settings, get_settings
from COREDB.errores import ErrorCoreDb
from COREDB.main import app
from COREDB.routers import auth as rutas_auth
from COREDB.services import hashing, usuarios

RUTAS_PUBLICAS = {"/coredb/salud", "/coredb/auth/login"}


def _claims(**cambios):
    ahora = int(time.time())
    claims = {
        "sub": str(uuid.uuid4()), "username": "ana", "rol": "ASESOR", "modulo": None,
        "type": "access", "iss": tokens.EMISOR, "aud": tokens.AUDIENCIA,
        "iat": ahora, "exp": ahora + 60, "jti": str(uuid.uuid4()),
    }
    claims.update(cambios)
    return {k: v for k, v in claims.items() if v is not ...}


def _firmar(claims, clave=None, algoritmo="HS256"):
    return jwt.encode(claims, clave or get_settings().jwt_clave, algorithm=algoritmo)


def _codigo(token):
    with pytest.raises(ErrorCoreDb) as exc:
        tokens.decodificar(token)
    assert exc.value.status_code == 401
    return exc.value.code


def test_token_de_ida_y_vuelta():
    id_usuario = uuid.uuid4()
    token, vigencia = tokens.crear_token(id_usuario=id_usuario, username="ana", rol="ASESOR", modulo=None)
    claims = tokens.decodificar(token)
    assert claims["sub"] == str(id_usuario) and claims["type"] == "access"
    assert claims["iss"] == "bna-coredb" and claims["aud"] == "coredb"
    assert vigencia == get_settings().jwt_minutos * 60
    assert {"iat", "exp", "jti"} <= claims.keys()


def test_cada_token_tiene_su_jti():
    datos = {"id_usuario": uuid.uuid4(), "username": "ana", "rol": "ASESOR", "modulo": None}
    assert tokens.decodificar(tokens.crear_token(**datos)[0])["jti"] != tokens.decodificar(
        tokens.crear_token(**datos)[0])["jti"]


def test_alg_none_se_rechaza():
    token = jwt.encode(_claims(), None, algorithm="none")
    assert _codigo(token) == "TOKEN_INVALIDO"


def test_firma_ajena_se_rechaza():
    assert _codigo(_firmar(_claims(), clave="otra-clave-de-otro-sistema-con-32-caracteres")) == "TOKEN_INVALIDO"


def test_algoritmo_distinto_del_servidor_se_rechaza():
    assert _codigo(_firmar(_claims(), algoritmo="HS512")) == "TOKEN_INVALIDO"


def test_token_vencido():
    ahora = int(time.time())
    assert _codigo(_firmar(_claims(iat=ahora - 120, exp=ahora - 60))) == "TOKEN_EXPIRADO"


@pytest.mark.parametrize("cambio", [
    {"iss": "bna-core"}, {"aud": "core"}, {"type": "refresh"}, {"sub": ...}, {"exp": ...},
    {"iat": ...}, {"jti": ...}, {"aud": ...}, {"iss": ...}, {"sub": "no-es-un-uuid"},
])
def test_claims_obligatorios(cambio):
    assert _codigo(_firmar(_claims(**cambio))) == "TOKEN_INVALIDO"


def test_un_token_de_core_no_sirve():
    """CORE firma con su SECRET_KEY y emisor bna-core, sin audiencia."""
    ahora = int(time.time())
    token_core = jwt.encode(
        {"sub": str(uuid.uuid4()), "username": "ana", "rol": "ASESOR", "type": "access",
         "iss": "bna-core", "iat": ahora, "exp": ahora + 60, "jti": str(uuid.uuid4())},
        get_settings().jwt_clave, algorithm="HS256",
    )
    assert _codigo(token_core) == "TOKEN_INVALIDO"


@pytest.mark.parametrize("clave", ["", "corta", "change_me_" + "x" * 40])
def test_clave_debil_impide_arrancar_sin_repetirla(monkeypatch, clave):
    monkeypatch.setattr(tokens, "get_settings", lambda: Settings(_env_file=None, jwt_clave=clave))
    with pytest.raises(RuntimeError) as exc:
        tokens.verificar_clave()
    assert "CORE_DB_JWT_CLAVE" in str(exc.value)
    if clave:
        assert clave not in str(exc.value)


def test_algoritmo_no_admitido_impide_arrancar(monkeypatch):
    monkeypatch.setattr(tokens, "get_settings",
                        lambda: Settings(_env_file=None, jwt_clave="x" * 40, jwt_algoritmo="none"))
    with pytest.raises(RuntimeError):
        tokens.verificar_clave()


def _dependencias(dependant):
    for dependencia in dependant.dependencies:
        yield dependencia.call
        yield from _dependencias(dependencia)


def _rutas():
    return [r for r in app.routes if isinstance(r, APIRoute)]


def test_toda_ruta_exige_autenticacion_salvo_las_publicas():
    assert {r.path for r in _rutas()} >= RUTAS_PUBLICAS
    for ruta in _rutas():
        llamadas = set(_dependencias(ruta.dependant))
        if ruta.path in RUTAS_PUBLICAS:
            assert actor_actual not in llamadas, ruta.path
        else:
            assert actor_actual in llamadas, ruta.path


def test_toda_escritura_exige_un_permiso():
    for ruta in _rutas():
        if ruta.path in RUTAS_PUBLICAS or not (ruta.methods & {"POST", "PUT", "PATCH", "DELETE"}):
            continue
        acciones = [getattr(c, "accion", None) for c in _dependencias(ruta.dependant)]
        assert any(acciones), ruta.path


def test_x_actor_no_autentica():
    respuesta = TestClient(app).get("/coredb/catalogos/monedas", headers={"X-Actor": "admin"})
    assert respuesta.status_code == 401
    assert respuesta.json()["error"]["code"] == "TOKEN_REQUERIDO"
    assert respuesta.headers["www-authenticate"] == "Bearer"


def test_esquema_distinto_de_bearer_no_autentica():
    respuesta = TestClient(app).get("/coredb/catalogos/monedas", headers={"Authorization": "Basic YTpi"})
    assert respuesta.json()["error"]["code"] == "TOKEN_REQUERIDO"


def test_permisos_de_los_roles():
    assert permisos.ACCIONES >= {"VALIDAR_IDENTIDAD", "CREAR_CLIENTE", "REGISTRAR_MOVIMIENTO"}
    assert permisos.PERMISOS["ADMINISTRADOR"] == permisos.ACCIONES - {"VALIDAR_IDENTIDAD"}
    assert "VALIDAR_IDENTIDAD" in permisos.PERMISOS["ASESOR"]
    assert permisos.PERMISOS["SERVICIO:CLIENTES"] == {
        "VER_CLIENTE", "CREAR_CLIENTE", "MODIFICAR_CLIENTE", "VALIDAR_IDENTIDAD"}
    assert all(acciones <= permisos.ACCIONES for acciones in permisos.PERMISOS.values())


def test_permiso_por_actor():
    servicio = Actor(uuid.uuid4(), "svc", "SERVICIO", "CLIENTES")
    otro_servicio = Actor(uuid.uuid4(), "svc2", "SERVICIO", "CUENTAS")
    assert permisos.puede(servicio, "CREAR_CLIENTE")
    assert not permisos.puede(servicio, "REGISTRAR_MOVIMIENTO")
    assert not permisos.puede(otro_servicio, "VER_CLIENTE")
    assert not permisos.puede(Actor(uuid.uuid4(), "x", "DESCONOCIDO"), "VER_CLIENTE")


def test_requiere_permiso_rechaza_accion_desconocida():
    with pytest.raises(ValueError):
        auth.requiere_permiso("BORRAR_TODO")


@pytest.mark.parametrize("rol,modulo,origen", [
    ("ASESOR", None, "OPERADOR"), ("ADMINISTRADOR", None, "OPERADOR"),
    ("SERVICIO", "CLIENTES", "MODULO_CLIENTES"), ("SERVICIO", "CUENTAS", "SISTEMA"),
])
def test_origen_del_actor(rol, modulo, origen):
    assert Actor(uuid.uuid4(), "x", rol, modulo).origen == origen


def test_dependencia_reemplazable():
    prueba = TestClient(app)
    app.dependency_overrides[actor_actual] = lambda: Actor(uuid.uuid4(), "doble", "AUDITOR")
    try:
        assert prueba.get("/coredb/auth/me").json()["username"] == "doble"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("codigo", ["CREDENCIALES_INVALIDAS", "USUARIO_INACTIVO", "PASSWORD_NO_ADMITIDA"])
def test_todo_fallo_de_login_responde_lo_mismo(monkeypatch, codigo):
    def autenticar(db, *, username, password):
        raise ErrorCoreDb(codigo, "detalle interno", 422 if codigo == "PASSWORD_NO_ADMITIDA" else 401)

    monkeypatch.setattr(rutas_auth.usuarios, "autenticar", autenticar)
    app.dependency_overrides[rutas_auth.db_session] = lambda: None
    try:
        respuesta = TestClient(app).post("/coredb/auth/login", json={"username": "ana", "password": "x"})
    finally:
        app.dependency_overrides.clear()
    assert respuesta.status_code == 401
    assert respuesta.json() == {"error": {"code": "CREDENCIALES_INVALIDAS",
                                          "message": "Usuario o contraseña incorrectos."}}
    assert respuesta.headers["www-authenticate"] == "Bearer"


class _ConsultaVacia:
    def query(self, *_):
        return self

    def filter(self, *_):
        return self

    def first(self):
        return None


def test_usuario_inexistente_gasta_una_verificacion(monkeypatch):
    llamadas = []
    monkeypatch.setattr(usuarios, "simular_verificacion", lambda: llamadas.append(1))
    monkeypatch.setattr(hashing, "simular_verificacion", lambda: llamadas.append(1))
    with pytest.raises(ErrorCoreDb):
        usuarios.autenticar(_ConsultaVacia(), username="nadie", password="clave-segura")
    assert llamadas


def test_login_sin_campos_extra():
    respuesta = TestClient(app).post(
        "/coredb/auth/login", json={"username": "a", "password": "b", "rol": "ADMINISTRADOR"})
    assert respuesta.status_code == 422
    assert "ADMINISTRADOR" not in respuesta.text
