"""Login, token y usuarios de servicio contra la base real."""

import hashlib
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from COREDB.database import get_session_factory, llamar
from COREDB.main import app
from COREDB.services.hashing import verify_password

CLAVE = "clave-de-un-usuario-1"


@pytest.fixture
def cliente():
    return TestClient(app)


def login(cliente, username, password, **kwargs):
    return cliente.post("/coredb/auth/login", json={"username": username, "password": password}, **kwargs)


def bearer(respuesta):
    assert respuesta.status_code == 200, respuesta.text
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


def test_login_entrega_token_y_perfil(cliente, sesion_de):
    _, creado = sesion_de("ASESOR")
    respuesta = login(cliente, creado["username"], CLAVE)
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["token_type"] == "bearer" and cuerpo["expires_in"] == 30 * 60
    assert cuerpo["usuario"]["username"] == creado["username"]
    assert "hash" not in respuesta.text and CLAVE not in respuesta.text
    perfil = cliente.get("/coredb/auth/me", headers=bearer(respuesta)).json()
    assert perfil["rol"] == "ASESOR" and "VALIDAR_IDENTIDAD" in perfil["acciones"]


def test_login_queda_en_la_bitacora_con_su_correlacion(cliente, sesion_de, consulta):
    _, creado = sesion_de("AUDITOR")
    correlacion = str(uuid.uuid4())
    login(cliente, creado["username"], CLAVE, headers={"X-Correlation-ID": correlacion})
    eventos = consulta(
        "SELECT actor, BIN_TO_UUID(correlation_id) c FROM core.evento_auditoria"
        " WHERE accion='LOGIN' AND id_entidad=%s ORDER BY id_evento DESC LIMIT 1",
        creado["id_usuario"],
    )
    assert eventos == [{"actor": creado["username"], "c": correlacion}]


def test_correlacion_invalida_no_impide_el_login(cliente, sesion_de):
    _, creado = sesion_de("AUDITOR")
    assert login(cliente, creado["username"], CLAVE, headers={"X-Correlation-ID": "x" * 80}).status_code == 200


def test_fallos_de_login_identicos(cliente, sesion_de, autorizacion):
    _, inactivo = sesion_de("ASESOR")
    cliente.post(f"/coredb/usuarios/{inactivo['id_usuario']}/estado", json={"activo": False},
                 headers=autorizacion)
    _, otro = sesion_de("ASESOR")
    respuestas = [
        login(cliente, "nadie-" + uuid.uuid4().hex[:8], CLAVE),
        login(cliente, otro["username"], "clave-incorrecta"),
        login(cliente, inactivo["username"], CLAVE),
        login(cliente, otro["username"], "a" * 100),
    ]
    assert {r.status_code for r in respuestas} == {401}
    assert len({r.text for r in respuestas}) == 1
    assert respuestas[0].json()["error"]["code"] == "CREDENCIALES_INVALIDAS"


def test_login_migra_sha256_a_bcrypt(cliente, consulta):
    username, id_usuario = "u" + uuid.uuid4().hex[:12], uuid.uuid4()
    with get_session_factory()() as db:
        llamar(db, "core.crear_usuario", id_usuario, username, "N", "AUDITOR",
               hashlib.sha256(CLAVE.encode()).hexdigest(), "SHA256", "v1", None, True, "pruebas")
        db.commit()
    assert login(cliente, username, CLAVE).status_code == 200
    fila = consulta("SELECT hash_password h, algoritmo_hash a FROM core.usuario_sistema WHERE username=%s",
                    username)[0]
    assert fila["a"] == "BCRYPT" and verify_password(CLAVE, fila["h"], "BCRYPT")


def test_sin_token_401_y_salud_publica(cliente):
    respuesta = cliente.get("/coredb/usuarios")
    assert respuesta.status_code == 401
    assert respuesta.json()["error"]["code"] == "TOKEN_REQUERIDO"
    assert cliente.get("/coredb/salud").status_code == 200


def test_token_de_un_usuario_desactivado_deja_de_servir(cliente, sesion_de, autorizacion):
    encabezados, creado = sesion_de("AUDITOR")
    assert cliente.get("/coredb/auth/me", headers=encabezados).status_code == 200
    cliente.post(f"/coredb/usuarios/{creado['id_usuario']}/estado", json={"activo": False},
                 headers=autorizacion)
    respuesta = cliente.get("/coredb/auth/me", headers=encabezados)
    assert respuesta.status_code == 401
    assert respuesta.json()["error"]["code"] == "USUARIO_NO_VIGENTE"


def test_cambio_de_rol_surte_efecto_de_inmediato(cliente, sesion_de, autorizacion):
    encabezados, creado = sesion_de("AUDITOR")
    respuesta = cliente.get("/coredb/usuarios", headers=encabezados)
    assert respuesta.status_code == 403
    assert respuesta.json()["error"]["code"] == "PERMISO_DENEGADO"
    cliente.post(f"/coredb/usuarios/{creado['id_usuario']}/rol", json={"rol": "ADMINISTRADOR"},
                 headers=autorizacion)
    assert cliente.get("/coredb/usuarios", headers=encabezados).status_code == 200


def test_un_rol_sin_permiso_no_escribe(cliente, sesion_de, abrir_cuenta):
    encabezados, _ = sesion_de("AUDITOR")
    respuesta = cliente.post(
        "/coredb/movimientos",
        json={"num_cuenta": abrir_cuenta(), "tipo": "DEPOSITO", "monto": "1.00", "glosa": "g", "id_canal": "VEN"},
        headers=encabezados,
    )
    assert respuesta.status_code == 403


def crear_servicio(cliente, autorizacion, modulo="CLIENTES"):
    respuesta = cliente.post(
        "/coredb/usuarios/servicios",
        json={"modulo": modulo, "username": "svc-" + uuid.uuid4().hex[:10], "nombre": "Módulo"},
        headers=autorizacion,
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta


def test_usuario_de_servicio_se_crea_con_su_secreto_una_vez(cliente, autorizacion, consulta):
    respuesta = crear_servicio(cliente, autorizacion)
    cuerpo = respuesta.json()
    assert respuesta.headers["cache-control"] == "no-store"
    assert cuerpo["usuario"]["rol"] == "SERVICIO" and cuerpo["usuario"]["modulo"] == "CLIENTES"
    secreto = cuerpo["secreto"]
    assert len(secreto) >= 40
    fila = consulta("SELECT hash_password h, algoritmo_hash a FROM core.usuario_sistema WHERE username=%s",
                    cuerpo["usuario"]["username"])[0]
    assert fila["a"] == "BCRYPT" and fila["h"] != secreto and verify_password(secreto, fila["h"], "BCRYPT")
    leido = cliente.get(f"/coredb/usuarios/{cuerpo['usuario']['id_usuario']}", headers=autorizacion)
    assert secreto not in leido.text
    evento = consulta("SELECT actor FROM core.evento_auditoria WHERE accion='CREAR_USUARIO_SERVICIO'"
                      " AND id_entidad=%s", cuerpo["usuario"]["id_usuario"])
    assert evento == [{"actor": "pruebas"}]


def test_servicio_inicia_sesion_y_solo_tiene_sus_permisos(cliente, autorizacion, abrir_cuenta):
    cuerpo = crear_servicio(cliente, autorizacion).json()
    encabezados = bearer(login(cliente, cuerpo["usuario"]["username"], cuerpo["secreto"]))
    perfil = cliente.get("/coredb/auth/me", headers=encabezados).json()
    assert (perfil["rol"], perfil["modulo"]) == ("SERVICIO", "CLIENTES")
    assert set(perfil["acciones"]) == {"VER_CLIENTE", "CREAR_CLIENTE", "MODIFICAR_CLIENTE", "VALIDAR_IDENTIDAD"}
    assert cliente.get("/coredb/usuarios", headers=encabezados).status_code == 403
    deposito = cliente.post(
        "/coredb/movimientos",
        json={"num_cuenta": abrir_cuenta(), "tipo": "DEPOSITO", "monto": "1.00", "glosa": "g", "id_canal": "VEN"},
        headers=encabezados,
    )
    assert deposito.status_code == 403


def test_servicio_de_un_modulo_desconocido_422(cliente, autorizacion):
    respuesta = cliente.post(
        "/coredb/usuarios/servicios",
        json={"modulo": "NOEXISTE", "username": "svc-" + uuid.uuid4().hex[:10], "nombre": "M"},
        headers=autorizacion,
    )
    assert respuesta.status_code == 422


def test_renovar_credencial_invalida_la_anterior(cliente, autorizacion):
    cuerpo = crear_servicio(cliente, autorizacion).json()
    username, viejo = cuerpo["usuario"]["username"], cuerpo["secreto"]
    renovado = cliente.post(f"/coredb/usuarios/{cuerpo['usuario']['id_usuario']}/credencial",
                            headers=autorizacion)
    assert renovado.status_code == 200 and renovado.headers["cache-control"] == "no-store"
    nuevo = renovado.json()["secreto"]
    assert nuevo != viejo
    assert login(cliente, username, viejo).status_code == 401
    assert login(cliente, username, nuevo).status_code == 200


def test_no_se_renueva_la_clave_de_una_persona(cliente, sesion_de, autorizacion):
    _, creado = sesion_de("ASESOR")
    respuesta = cliente.post(f"/coredb/usuarios/{creado['id_usuario']}/credencial", headers=autorizacion)
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "BNA-USUARIO-SERVICIO"


def test_renovar_un_usuario_inexistente_404(cliente, autorizacion):
    respuesta = cliente.post(f"/coredb/usuarios/{uuid.uuid4()}/credencial", headers=autorizacion)
    assert respuesta.status_code == 404


def test_revocar_un_servicio_corta_su_token(cliente, autorizacion, consulta):
    cuerpo = crear_servicio(cliente, autorizacion).json()
    encabezados = bearer(login(cliente, cuerpo["usuario"]["username"], cuerpo["secreto"]))
    respuesta = cliente.post(f"/coredb/usuarios/{cuerpo['usuario']['id_usuario']}/estado",
                             json={"activo": False}, headers=autorizacion)
    assert respuesta.status_code == 200 and respuesta.json()["activo"] is False
    assert cliente.get("/coredb/auth/me", headers=encabezados).status_code == 401
    assert login(cliente, cuerpo["usuario"]["username"], cuerpo["secreto"]).status_code == 401
    assert consulta("SELECT actor FROM core.evento_auditoria WHERE accion='DESACTIVAR_USUARIO'"
                    " AND id_entidad=%s", cuerpo["usuario"]["id_usuario"]) == [{"actor": "pruebas"}]


def test_crear_servicio_exige_crear_usuario(cliente, sesion_de):
    encabezados, _ = sesion_de("ASESOR")
    respuesta = cliente.post(
        "/coredb/usuarios/servicios",
        json={"modulo": "CLIENTES", "username": "svc-" + uuid.uuid4().hex[:10], "nombre": "M"},
        headers=encabezados,
    )
    assert respuesta.status_code == 403


def test_el_arranque_no_crea_un_segundo_administrador(consulta, token_admin, clave_admin):
    antes = consulta("SELECT COUNT(*) n FROM core.usuario_sistema WHERE rol='ADMINISTRADOR'")[0]["n"]
    entorno = {**os.environ, "CORE_DB_ADMIN_INICIAL_PASSWORD": clave_admin}
    resultado = subprocess.run(
        [sys.executable, "-m", "COREDB.scripts.crear_administrador", "--username", "otro-admin",
         "--nombre", "Otro"],
        cwd=Path(__file__).resolve().parents[3], env=entorno, capture_output=True, text=True,
    )
    assert resultado.returncode == 1
    assert "ya existe" in resultado.stderr.lower()
    assert clave_admin not in resultado.stderr + resultado.stdout
    despues = consulta("SELECT COUNT(*) n FROM core.usuario_sistema WHERE rol='ADMINISTRADOR'")[0]["n"]
    assert despues == antes
