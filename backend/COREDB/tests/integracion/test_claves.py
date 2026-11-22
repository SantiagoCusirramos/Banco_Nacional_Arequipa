"""Contraseña inicial generada, renovación y cambio obligatorio en el primer ingreso (bd-v1.17).

Hallazgos B1/B2 de la prueba «solo con el mouse»: el administrador inventaba la contraseña y la
pasaba por fuera, y nadie tenía que cambiarla. Ahora COREDB la genera, la entrega una sola vez y
la persona no puede operar hasta cambiarla. Con `password` explícita (aprovisionamiento por
scripts y pruebas) no se exige el cambio.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from COREDB.main import app


@pytest.fixture
def api(autorizacion):
    return TestClient(app, headers=autorizacion)


def nombre():
    return "c" + uuid.uuid4().hex[:12]


def alta_sin_clave(api, rol="ADMINISTRADOR"):
    username = nombre()
    respuesta = api.post("/coredb/usuarios", json={"username": username, "nombre": "Persona Nueva", "rol": rol})
    assert respuesta.status_code == 201, respuesta.text
    return username, respuesta


def login(username, password):
    return TestClient(app).post("/coredb/auth/login", json={"username": username, "password": password})


def con_token(respuesta_login):
    return {"Authorization": f"Bearer {respuesta_login.json()['access_token']}"}


def test_alta_sin_clave_la_genera_la_entrega_una_vez_y_exige_cambiarla(api, consulta):
    username, respuesta = alta_sin_clave(api)
    cuerpo = respuesta.json()
    clave = cuerpo["clave_inicial"]
    assert len(clave) >= 12 and any(c.isdigit() for c in clave) and any(c.isalpha() for c in clave)
    assert cuerpo["debe_cambiar_clave"] is True
    assert respuesta.headers["cache-control"] == "no-store"
    # La lista y la ficha nunca la vuelven a mostrar.
    assert "clave_inicial" not in api.get(f"/coredb/usuarios/{cuerpo['id_usuario']}").json()
    entrada = login(username, clave)
    assert entrada.status_code == 200
    assert entrada.json()["usuario"]["debe_cambiar_clave"] is True
    eventos = consulta(
        "SELECT accion, actor, detalle FROM core.evento_auditoria WHERE id_entidad=%s ORDER BY id_evento",
        cuerpo["id_usuario"],
    )
    assert [e["accion"] for e in eventos] == ["CREAR_USUARIO", "EXIGIR_CAMBIO_CLAVE", "LOGIN"]
    assert all(clave not in str(e["detalle"]) for e in eventos)


def test_con_cambio_pendiente_solo_puede_ver_su_perfil_y_cambiar_la_clave(api):
    username, respuesta = alta_sin_clave(api)
    cabeceras = con_token(login(username, respuesta.json()["clave_inicial"]))
    cliente = TestClient(app, headers=cabeceras)
    perfil = cliente.get("/coredb/auth/me")
    assert perfil.status_code == 200
    assert perfil.json()["debe_cambiar_clave"] is True
    bloqueada = cliente.get("/coredb/usuarios")
    assert bloqueada.status_code == 403
    assert bloqueada.json()["error"]["code"] == "CAMBIO_CLAVE_OBLIGATORIO"


def test_cambiar_la_clave_propia_la_reemplaza_y_libera_el_acceso(api, consulta):
    username, respuesta = alta_sin_clave(api)
    inicial = respuesta.json()["clave_inicial"]
    cliente = TestClient(app, headers=con_token(login(username, inicial)))

    mala = cliente.post("/coredb/auth/clave", json={"actual": "no-es-la-clave", "nueva": "otra-clave-larga-1"})
    assert mala.status_code == 422
    assert mala.json()["error"]["code"] == "CLAVE_ACTUAL_INCORRECTA"
    igual = cliente.post("/coredb/auth/clave", json={"actual": inicial, "nueva": inicial})
    assert igual.status_code == 422
    assert igual.json()["error"]["code"] == "CLAVE_NO_ADMITIDA"
    assert cliente.post("/coredb/auth/clave", json={"actual": inicial, "nueva": "corta1"}).status_code == 422

    cambio = cliente.post("/coredb/auth/clave", json={"actual": inicial, "nueva": "mi-clave-propia-1"})
    assert cambio.status_code == 200, cambio.text
    assert cambio.json()["debe_cambiar_clave"] is False
    assert cliente.get("/coredb/usuarios").status_code == 200
    assert login(username, inicial).status_code == 401
    assert login(username, "mi-clave-propia-1").json()["usuario"]["debe_cambiar_clave"] is False
    evento = consulta(
        "SELECT actor FROM core.evento_auditoria WHERE accion='CAMBIAR_CLAVE' AND id_entidad=%s",
        respuesta.json()["id_usuario"],
    )
    assert evento == [{"actor": username}]


def test_quien_ya_cambio_su_clave_puede_volver_a_cambiarla(api):
    username, respuesta = alta_sin_clave(api, rol="OPERADOR")
    inicial = respuesta.json()["clave_inicial"]
    cliente = TestClient(app, headers=con_token(login(username, inicial)))
    assert cliente.post("/coredb/auth/clave", json={"actual": inicial, "nueva": "primera-propia-1"}).status_code == 200
    assert cliente.post("/coredb/auth/clave", json={"actual": "primera-propia-1", "nueva": "segunda-propia-2"}).status_code == 200
    assert login(username, "segunda-propia-2").status_code == 200


def test_renovar_la_clave_de_una_persona_entrega_una_temporal_y_exige_cambiarla(api, consulta):
    username, respuesta = alta_sin_clave(api, rol="ASESOR")
    id_usuario = respuesta.json()["id_usuario"]
    anterior = respuesta.json()["clave_inicial"]
    renovada = api.post(f"/coredb/usuarios/{id_usuario}/clave")
    assert renovada.status_code == 200, renovada.text
    assert renovada.headers["cache-control"] == "no-store"
    nueva = renovada.json()["clave_inicial"]
    assert nueva != anterior and renovada.json()["usuario"]["debe_cambiar_clave"] is True
    assert login(username, anterior).status_code == 401
    assert login(username, nueva).json()["usuario"]["debe_cambiar_clave"] is True
    assert consulta(
        "SELECT actor FROM core.evento_auditoria WHERE accion='RESTABLECER_CLAVE' AND id_entidad=%s", id_usuario
    ) == [{"actor": "pruebas"}]


def test_renovar_clave_rechaza_usuarios_de_servicio_inexistentes_y_a_quien_no_administra(api, sesion_de):
    servicio = api.post("/coredb/usuarios/servicios", json={"modulo": "CLIENTES", "username": nombre(), "nombre": "S"})
    assert servicio.status_code == 201, servicio.text
    rechazo = api.post(f"/coredb/usuarios/{servicio.json()['usuario']['id_usuario']}/clave")
    assert rechazo.status_code == 422
    assert api.post(f"/coredb/usuarios/{uuid.uuid4()}/clave").status_code == 404
    cabeceras_operador, _ = sesion_de("OPERADOR")
    _, otra = alta_sin_clave(api, rol="ASESOR")
    sin_permiso = TestClient(app, headers=cabeceras_operador).post(f"/coredb/usuarios/{otra.json()['id_usuario']}/clave")
    assert sin_permiso.status_code == 403


def test_alta_con_clave_explicita_no_exige_el_cambio(api):
    username = nombre()
    creado = api.post("/coredb/usuarios", json={"username": username, "nombre": "N", "password": "clave-explicita-1", "rol": "OPERADOR"})
    assert creado.status_code == 201
    assert creado.json()["debe_cambiar_clave"] is False
    assert "clave_inicial" not in creado.json() or creado.json()["clave_inicial"] is None
    assert login(username, "clave-explicita-1").json()["usuario"]["debe_cambiar_clave"] is False
