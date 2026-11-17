"""El arranque crea o alinea el usuario de servicio de un módulo con el secreto de su .env.

Lo usan compose y Kubernetes para EVALUACIÓN: el secreto sale del almacén de secretos del
despliegue (no lo genera COREDB), así que repetir el arranque no lo cambia y cambiarlo en
.env lo reemplaza en la base.
"""

import os
import secrets
import subprocess
import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from COREDB.main import app

RAIZ = Path(__file__).resolve().parents[3]


def arrancar(username, secreto, modulo="EVALUACION"):
    entorno = {**os.environ, "CORE_DB_SERVICIO_SECRETO": secreto}
    return subprocess.run(
        [sys.executable, "-m", "COREDB.scripts.crear_servicio", "--modulo", modulo,
         "--username", username, "--nombre", "Evaluación"],
        cwd=RAIZ, env=entorno, capture_output=True, text=True,
    )


def login(username, secreto):
    return TestClient(app).post("/coredb/auth/login", json={"username": username, "password": secreto})


def test_crea_el_servicio_con_el_secreto_dado(consulta, token_admin):
    username, secreto = "svc-" + uuid.uuid4().hex[:10], secrets.token_hex(24)
    resultado = arrancar(username, secreto)
    assert resultado.returncode == 0, resultado.stderr
    assert secreto not in resultado.stdout + resultado.stderr
    r = login(username, secreto)
    assert r.status_code == 200, r.text
    perfil = TestClient(app).get("/coredb/auth/me",
                                 headers={"Authorization": f"Bearer {r.json()['access_token']}"}).json()
    assert perfil["rol"] == "SERVICIO" and perfil["modulo"] == "EVALUACION"
    assert set(perfil["acciones"]) == {"CREAR_SOLICITUD_CREDITO", "VER_CREDITO"}
    fila = consulta("SELECT algoritmo_hash FROM core.usuario_sistema WHERE username = %s", username)
    assert fila == [{"algoritmo_hash": "BCRYPT"}]


def test_repetir_el_arranque_no_cambia_nada(consulta, token_admin):
    username, secreto = "svc-" + uuid.uuid4().hex[:10], secrets.token_hex(24)
    assert arrancar(username, secreto).returncode == 0
    hash_antes = consulta("SELECT hash_password FROM core.usuario_sistema WHERE username = %s", username)
    resultado = arrancar(username, secreto)
    assert resultado.returncode == 0, resultado.stderr
    assert "ya existe" in resultado.stdout.lower()
    assert consulta("SELECT hash_password FROM core.usuario_sistema WHERE username = %s", username) == hash_antes
    assert login(username, secreto).status_code == 200


def test_otro_secreto_reemplaza_al_anterior(token_admin):
    username, viejo, nuevo = "svc-" + uuid.uuid4().hex[:10], secrets.token_hex(24), secrets.token_hex(24)
    assert arrancar(username, viejo).returncode == 0
    resultado = arrancar(username, nuevo)
    assert resultado.returncode == 0, resultado.stderr
    assert login(username, viejo).status_code == 401
    assert login(username, nuevo).status_code == 200


def test_secreto_corto_o_modulo_desconocido_no_crean_nada(consulta, token_admin):
    username = "svc-" + uuid.uuid4().hex[:10]
    corto = arrancar(username, "corto")
    assert corto.returncode == 1 and "32" in corto.stderr
    desconocido = arrancar(username, secrets.token_hex(24), modulo="NADIE")
    assert desconocido.returncode == 1
    assert consulta("SELECT COUNT(*) n FROM core.usuario_sistema WHERE username = %s", username)[0]["n"] == 0


def test_no_toca_a_una_persona_con_ese_nombre(sesion_de, token_admin):
    _, persona = sesion_de("ANALISTA")
    resultado = arrancar(persona["username"], secrets.token_hex(24))
    assert resultado.returncode == 1
    assert "no es un usuario de servicio" in resultado.stderr.lower()
