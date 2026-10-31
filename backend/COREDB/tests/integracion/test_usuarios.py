import hashlib
import threading
import uuid

import pytest
from fastapi.testclient import TestClient

from COREDB.database import get_session_factory, llamar
from COREDB.errores import ErrorCoreDb
from COREDB.main import app
from COREDB.services import usuarios
from COREDB.services.hashing import verify_password

CLAVE = "clave-segura-1"


@pytest.fixture
def cliente():
    return TestClient(app)


def nombre():
    return "u" + uuid.uuid4().hex[:12]


def alta(cliente, username, password=CLAVE, rol="OPERADOR"):
    return cliente.post(
        "/coredb/usuarios",
        json={"username": username, "nombre": "N", "password": password, "rol": rol},
        headers={"X-Actor": "pruebas"},
    )


def sembrar_sha256():
    username, id_usuario = nombre(), uuid.uuid4()
    with get_session_factory()() as db:
        llamar(
            db, "core.crear_usuario", id_usuario, username, "N", "ASESOR",
            hashlib.sha256(CLAVE.encode()).hexdigest(), "SHA256", "v1", None, True, "pruebas",
        )
        db.commit()
    return username, id_usuario


def test_crear_guarda_bcrypt_y_audita(cliente, consulta):
    username = nombre()
    respuesta = alta(cliente, username)
    assert respuesta.status_code == 201
    assert "hash" not in respuesta.text
    fila = consulta(
        "SELECT hash_password h, algoritmo_hash a FROM core.usuario_sistema WHERE username=%s",
        username,
    )[0]
    assert fila["a"] == "BCRYPT" and verify_password(CLAVE, fila["h"], "BCRYPT")
    evento = consulta(
        "SELECT actor FROM core.evento_auditoria WHERE accion='CREAR_USUARIO' AND id_entidad=%s",
        respuesta.json()["id_usuario"],
    )
    assert evento == [{"actor": "pruebas"}]


def test_uuid_se_guarda_binario_y_se_lee(cliente, consulta):
    id_usuario = alta(cliente, nombre()).json()["id_usuario"]
    assert cliente.get(f"/coredb/usuarios/{id_usuario}").status_code == 200
    assert consulta(
        "SELECT 1 FROM core.usuario_sistema WHERE id_usuario=UUID_TO_BIN(%s)", id_usuario
    )


def test_usuario_duplicado_409(cliente):
    username = nombre()
    alta(cliente, username)
    respuesta = alta(cliente, username)
    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["code"] == "REGISTRO_DUPLICADO"


def test_usuario_inexistente_404(cliente):
    assert cliente.get(f"/coredb/usuarios/{uuid.uuid4()}").status_code == 404


def test_cambia_rol(cliente):
    id_usuario = alta(cliente, nombre()).json()["id_usuario"]
    respuesta = cliente.post(f"/coredb/usuarios/{id_usuario}/rol", json={"rol": "AUDITOR"})
    assert respuesta.json()["rol"] == "AUDITOR"


@pytest.mark.parametrize("password", ["a" * 73, "clave\x00segura"])
def test_password_no_admitida(cliente, password):
    assert alta(cliente, nombre(), password).status_code == 422


def test_surrogate_crudo_responde_422(cliente):
    cuerpo = '{"username":"abcd","nombre":"N","password":"clave\\ud800segura","rol":"ASESOR"}'
    respuesta = cliente.post(
        "/coredb/usuarios", content=cuerpo, headers={"content-type": "application/json"}
    )
    assert respuesta.status_code == 422


def test_autenticar_y_clave_incorrecta(cliente):
    username = nombre()
    alta(cliente, username)
    with get_session_factory()() as db:
        assert usuarios.autenticar(db, username=username, password=CLAVE).username == username
        with pytest.raises(ErrorCoreDb) as exc:
            usuarios.autenticar(db, username=username, password="otra-clave")
    assert exc.value.code == "CREDENCIALES_INVALIDAS"


def test_ocho_logins_migran_una_vez(consulta):
    username, id_usuario = sembrar_sha256()
    barrera, resultados = threading.Barrier(8), []

    def login():
        with get_session_factory()() as db:
            barrera.wait()
            resultados.append(usuarios.autenticar(db, username=username, password=CLAVE).username)

    hilos = [threading.Thread(target=login) for _ in range(8)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    assert resultados == [username] * 8
    eventos = consulta(
        "SELECT 1 FROM core.evento_auditoria WHERE accion='MIGRAR_HASH_PASSWORD' AND id_entidad=%s",
        str(id_usuario),
    )
    assert len(eventos) == 1
    fila = consulta(
        "SELECT hash_password h, algoritmo_hash a FROM core.usuario_sistema WHERE username=%s",
        username,
    )[0]
    assert fila["a"] == "BCRYPT" and verify_password(CLAVE, fila["h"], "BCRYPT")


def test_fechas_se_publican_en_utc(cliente):
    assert alta(cliente, nombre()).json()["creado_en"].endswith("Z")


def test_actor_vacio_422(cliente):
    respuesta = cliente.post(
        "/coredb/usuarios",
        json={"username": nombre(), "nombre": "N", "password": CLAVE, "rol": "ASESOR"},
        headers={"X-Actor": ""},
    )
    assert respuesta.status_code == 422


@pytest.mark.parametrize("codigo", [1213, 1205])
def test_crear_usuario_se_reintenta(cliente, fallar_una_vez, codigo):
    intentos = fallar_una_vez(usuarios, codigo)
    respuesta = cliente.post(
        "/coredb/usuarios",
        json={"username": uuid.uuid4().hex[:20], "nombre": "A", "password": CLAVE, "rol": "ASESOR"},
    )
    assert respuesta.status_code == 201
    assert len(intentos) == 2


@pytest.mark.parametrize("codigo", [1213, 1205])
def test_asignar_rol_se_reintenta(cliente, fallar_una_vez, codigo):
    creado = cliente.post(
        "/coredb/usuarios",
        json={"username": uuid.uuid4().hex[:20], "nombre": "A", "password": CLAVE, "rol": "ASESOR"},
    ).json()
    intentos = fallar_una_vez(usuarios, codigo)
    respuesta = cliente.post(f"/coredb/usuarios/{creado['id_usuario']}/rol", json={"rol": "AUDITOR"})
    assert respuesta.status_code == 200
    assert respuesta.json()["rol"] == "AUDITOR"
    assert len(intentos) == 2
