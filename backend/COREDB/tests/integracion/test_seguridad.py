"""Rutas del módulo Seguridad (bd-v1.13) contra la base real.

Seguridad llama con su usuario de servicio (OPERAR_SEGURIDAD) y presenta el token de la
persona por la que actúa en X-Persona-Token: COREDB comprueba el permiso de la persona y la
registra como actor. Nadie más llega a estas rutas.
"""

import hashlib
import hmac
import uuid

import pytest
from fastapi.testclient import TestClient

from COREDB.main import app

CLAVE = b"clave-de-seguridad-de-las-pruebas"


def _hmac(id_desafio: str, codigo: str) -> str:
    return hmac.new(CLAVE, f"{id_desafio}:{codigo}".encode(), hashlib.sha256).hexdigest()


@pytest.fixture
def cliente():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def servicio(cliente, autorizacion):
    """Encabezados del usuario de servicio de Seguridad, con sesión por la API."""
    creado = cliente.post(
        "/coredb/usuarios/servicios",
        json={"modulo": "SEGURIDAD", "username": "svc-" + uuid.uuid4().hex[:10], "nombre": "Seguridad"},
        headers=autorizacion,
    )
    assert creado.status_code == 201, creado.text
    cuerpo = creado.json()
    login = cliente.post("/coredb/auth/login",
                         json={"username": cuerpo["usuario"]["username"], "password": cuerpo["secreto"]})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture
def por_persona(servicio, sesion_de):
    """Encabezados de Seguridad actuando por una persona con `rol`, y su username."""
    def _por(rol):
        encabezados, usuario = sesion_de(rol)
        token = encabezados["Authorization"].removeprefix("Bearer ")
        return {**servicio, "X-Persona-Token": token}, usuario["username"]
    return _por


def _evaluar(cliente, encabezados, cuenta, monto, canal="ATM", operacion=None, **extra):
    return cliente.post("/coredb/seguridad/evaluaciones", headers=encabezados, json={
        "uuid_operacion": operacion or str(uuid.uuid4()), "num_cuenta": cuenta, "canal": canal,
        "monto": monto, **extra})


# --------------------------------------------------------------------- quién llega
def test_una_persona_no_llama_directo_a_las_rutas_de_seguridad(cliente, sesion_de, abrir_cuenta):
    encabezados, _ = sesion_de("OPERADOR")
    respuesta = _evaluar(cliente, encabezados, abrir_cuenta(), "10.00")
    assert respuesta.status_code == 403
    assert respuesta.json()["error"]["code"] == "PERMISO_DENEGADO"


def test_el_servicio_sin_token_de_persona_no_opera(cliente, servicio, abrir_cuenta):
    respuesta = _evaluar(cliente, servicio, abrir_cuenta(), "10.00")
    assert respuesta.status_code == 401
    assert respuesta.json()["error"]["code"] == "PERSONA_TOKEN_REQUERIDO"


def test_el_token_de_persona_no_puede_ser_otro_servicio(cliente, servicio, abrir_cuenta):
    respuesta = _evaluar(cliente, {**servicio, "X-Persona-Token": servicio["Authorization"][7:]},
                         abrir_cuenta(), "10.00")
    assert respuesta.status_code == 401
    assert respuesta.json()["error"]["code"] == "PERSONA_NO_VIGENTE"


def test_la_persona_necesita_su_propio_permiso(cliente, por_persona, abrir_cuenta):
    encabezados, _ = por_persona("AUDITOR")  # sin REGISTRAR_MOVIMIENTO
    respuesta = _evaluar(cliente, encabezados, abrir_cuenta(), "10.00")
    assert respuesta.status_code == 403
    assert respuesta.json()["error"]["code"] == "PERMISO_DENEGADO"


def test_otro_servicio_no_llega(cliente, autorizacion, abrir_cuenta, sesion_de):
    creado = cliente.post("/coredb/usuarios/servicios", headers=autorizacion, json={
        "modulo": "COBRANZA", "username": "svc-" + uuid.uuid4().hex[:10], "nombre": "C"}).json()
    token = cliente.post("/coredb/auth/login", json={
        "username": creado["usuario"]["username"], "password": creado["secreto"]}).json()["access_token"]
    persona, _ = sesion_de("OPERADOR")
    respuesta = _evaluar(cliente, {"Authorization": f"Bearer {token}",
                                   "X-Persona-Token": persona["Authorization"][7:]}, abrir_cuenta(), "1.00")
    assert respuesta.status_code == 403


# --------------------------------------------------------------------- evaluación y desafío
def test_evaluacion_bajo_el_umbral_autoriza_y_registra_a_la_persona(cliente, por_persona, abrir_cuenta,
                                                                    consulta):
    encabezados, username = por_persona("OPERADOR")
    operacion = str(uuid.uuid4())
    respuesta = _evaluar(cliente, encabezados, abrir_cuenta(), "1000.00", operacion=operacion)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {"uuid_operacion": operacion, "decision": "AUTORIZADA", "motivo": None,
                                "tope": "1500.00", "consumido": "0.00", "repetida": False}
    assert consulta("SELECT actor FROM core.evento_auditoria WHERE id_entidad = %s AND accion = "
                    "'EVALUAR_OPERACION'", operacion) == [{"actor": username}]


def test_evaluacion_sobre_el_tope_se_rechaza(cliente, por_persona, abrir_cuenta):
    encabezados, _ = por_persona("OPERADOR")
    cuerpo = _evaluar(cliente, encabezados, abrir_cuenta(), "1500.01").json()
    assert (cuerpo["decision"], cuerpo["motivo"]) == ("RECHAZADA", "TOPE")


def test_desafio_completo(cliente, por_persona, abrir_cuenta, consulta):
    encabezados, _ = por_persona("OPERADOR")
    cuenta, operacion, id_desafio = abrir_cuenta(), str(uuid.uuid4()), str(uuid.uuid4())
    primera = _evaluar(cliente, encabezados, cuenta, "1300.00", operacion=operacion).json()
    assert primera["decision"] == "DESAFIO_REQUERIDO"

    creado = cliente.post("/coredb/seguridad/desafios", headers=encabezados, json={
        "id_desafio": id_desafio, "uuid_operacion": operacion, "num_cuenta": cuenta, "canal": "ATM",
        "monto": "1300.00", "hmac_codigo": _hmac(id_desafio, "123456")})
    assert creado.status_code == 201, creado.text
    assert creado.json()["id_desafio"] == id_desafio
    assert creado.json()["vence_en"].endswith("Z")
    # La base guarda el HMAC, nunca el código.
    assert consulta("SELECT hmac_codigo h FROM core.desafio_operacion WHERE id_desafio = UUID_TO_BIN(%s)",
                    id_desafio) == [{"h": _hmac(id_desafio, "123456")}]

    mal = _evaluar(cliente, encabezados, cuenta, "1300.00", operacion=operacion, id_desafio=id_desafio,
                   hmac_codigo=_hmac(id_desafio, "000000"))
    assert mal.status_code == 200 and mal.json()["decision"] == "DESAFIO_RECHAZADO"
    bien = _evaluar(cliente, encabezados, cuenta, "1300.00", operacion=operacion, id_desafio=id_desafio,
                    hmac_codigo=_hmac(id_desafio, "123456"))
    assert bien.json()["decision"] == "AUTORIZADA" and bien.json()["repetida"] is False
    otra_vez = _evaluar(cliente, encabezados, cuenta, "1300.00", operacion=operacion)
    assert otra_vez.json()["decision"] == "AUTORIZADA" and otra_vez.json()["repetida"] is True


def test_la_misma_operacion_con_otro_monto_es_409(cliente, por_persona, abrir_cuenta):
    encabezados, _ = por_persona("OPERADOR")
    cuenta, operacion = abrir_cuenta(), str(uuid.uuid4())
    _evaluar(cliente, encabezados, cuenta, "10.00", operacion=operacion)
    respuesta = _evaluar(cliente, encabezados, cuenta, "11.00", operacion=operacion)
    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["code"] == "BNA-IDEMPOTENCIA"


def test_desafio_y_codigo_van_juntos(cliente, por_persona, abrir_cuenta):
    encabezados, _ = por_persona("OPERADOR")
    respuesta = _evaluar(cliente, encabezados, abrir_cuenta(), "10.00", id_desafio=str(uuid.uuid4()))
    assert respuesta.status_code == 422


def test_evaluacion_de_una_cuenta_que_no_existe_es_404(cliente, por_persona):
    encabezados, _ = por_persona("OPERADOR")
    respuesta = _evaluar(cliente, encabezados, "NO-EXISTE", "10.00")
    assert respuesta.status_code == 404


# --------------------------------------------------------------------- sellos de la bitácora
def test_sellos_encadenados(cliente, servicio, autorizacion, por_persona):
    # Al menos un evento sin sellar.
    encabezados, _ = por_persona("OPERADOR")
    cliente.post("/coredb/seguridad/incidentes", headers=encabezados,
                 json={"prioridad": "P4", "titulo": "Evento para sellar"})
    sellos = cliente.get("/coredb/auditoria/sellos", headers=servicio).json()
    desde = sellos[-1]["hasta_evento"] if sellos else 0
    eventos = cliente.get("/coredb/auditoria", headers=servicio,
                          params={"despues_de_id": desde, "limite": 200}).json()
    assert eventos and [e["id_evento"] for e in eventos] == sorted(e["id_evento"] for e in eventos)
    assert eventos[0]["id_evento"] > desde
    hasta = eventos[-1]["id_evento"]
    sello = cliente.post("/coredb/auditoria/sellos", headers=servicio,
                         json={"hasta_evento": hasta, "eventos": len(eventos), "hmac": "a" * 64})
    assert sello.status_code == 201, sello.text
    assert sello.json()["desde_evento"] == desde and sello.json()["hasta_evento"] == hasta
    # Repetirlo ya no sigue al último sello.
    repetido = cliente.post("/coredb/auditoria/sellos", headers=servicio,
                            json={"hasta_evento": hasta, "eventos": len(eventos), "hmac": "a" * 64})
    assert repetido.status_code == 409
    assert repetido.json()["error"]["code"] == "BNA-SELLO"
    # El auditor (VER_AUDITORIA) los lee; no los escribe.
    assert cliente.get("/coredb/auditoria/sellos", headers=autorizacion).status_code == 200
    escribe = cliente.post("/coredb/auditoria/sellos", headers=autorizacion,
                           json={"hasta_evento": hasta + 1, "eventos": 1, "hmac": "a" * 64})
    assert escribe.status_code == 403


# --------------------------------------------------------------------- incidentes
def test_ciclo_de_un_incidente(cliente, por_persona, consulta):
    encabezados, username = por_persona("OPERADOR")
    creado = cliente.post("/coredb/seguridad/incidentes", headers=encabezados,
                          json={"prioridad": "P2", "titulo": "Intentos de acceso repetidos"})
    assert creado.status_code == 201, creado.text
    incidente = creado.json()
    assert (incidente["estado"], incidente["abierto_por"]) == ("ABIERTO", username)
    url = f"/coredb/seguridad/incidentes/{incidente['id_incidente']}/estado"

    salto = cliente.post(url, headers=encabezados, json={"estado": "RESUELTO", "resolucion": "Sin pasar"})
    assert salto.status_code == 409
    assert salto.json()["error"]["code"] == "BNA-INCIDENTE-TRANSICION"
    assert cliente.post(url, headers=encabezados, json={"estado": "EN_PROGRESO"}).status_code == 200
    sin_resolucion = cliente.post(url, headers=encabezados, json={"estado": "RESUELTO"})
    assert sin_resolucion.status_code == 422
    resuelto = cliente.post(url, headers=encabezados,
                            json={"estado": "RESUELTO", "resolucion": "Se bloqueó el origen"})
    assert resuelto.json()["estado"] == "RESUELTO"
    cerrado = cliente.post(url, headers=encabezados, json={"estado": "CERRADO"}).json()
    assert (cerrado["estado"], cerrado["resolucion"]) == ("CERRADO", "Se bloqueó el origen")

    auditor, _ = por_persona("AUDITOR")
    lista = cliente.get("/coredb/seguridad/incidentes", headers=auditor)
    assert lista.status_code == 200
    assert incidente["id_incidente"] in [i["id_incidente"] for i in lista.json()]
    # El auditor lee, pero no abre ni avanza incidentes.
    assert cliente.post("/coredb/seguridad/incidentes", headers=auditor,
                        json={"prioridad": "P1", "titulo": "No debería abrirse"}).status_code == 403


def test_incidente_que_no_existe_es_404(cliente, por_persona):
    encabezados, _ = por_persona("OPERADOR")
    respuesta = cliente.post(f"/coredb/seguridad/incidentes/{uuid.uuid4()}/estado", headers=encabezados,
                             json={"estado": "EN_PROGRESO"})
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["code"] == "INCIDENTE_NO_ENCONTRADO"


# --------------------------------------------------------------------- desbloqueo de tarjetas
def _tarjeta_bloqueada(cliente, autorizacion, cuenta):
    tarjeta = cliente.post("/coredb/tarjetas", headers=autorizacion, json={
        "pan_token": uuid.uuid4().hex, "bin": "004499", "ultimos4": "4321", "fecha_emision": "2026-01-01",
        "fecha_vencimiento": "2030-01-01", "cod_cliente": "C001", "num_cuenta": cuenta}).json()["id_tarjeta"]
    for estado in ("ACTIVA", "BLOQUEADA"):
        r = cliente.post(f"/coredb/tarjetas/{tarjeta}/estado", headers=autorizacion, json={"estado": estado})
        assert r.status_code == 200, r.text
    return tarjeta


def test_seguridad_desbloquea_una_tarjeta_por_una_persona(cliente, autorizacion, por_persona, abrir_cuenta,
                                                          consulta):
    tarjeta = _tarjeta_bloqueada(cliente, autorizacion, abrir_cuenta())
    encabezados, username = por_persona("OPERADOR")
    respuesta = cliente.post(f"/coredb/tarjetas/{tarjeta}/desbloqueo", headers=encabezados,
                             json={"motivo": "El cliente confirmó su identidad"})
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado_tarjeta"] == "ACTIVA"
    assert consulta("SELECT origen FROM tarjetas.historial_estado_tarjeta WHERE id_tarjeta = UUID_TO_BIN(%s) "
                    "ORDER BY id_historial DESC LIMIT 1", tarjeta) == [{"origen": "SEGURIDAD"}]
    assert consulta("SELECT actor FROM core.evento_auditoria WHERE id_entidad = %s AND accion = "
                    "'DESBLOQUEAR_TARJETA'", tarjeta) == [{"actor": username}]
    # Otra vez: ya no está bloqueada.
    otra = cliente.post(f"/coredb/tarjetas/{tarjeta}/desbloqueo", headers=encabezados,
                        json={"motivo": "Repetido"})
    assert otra.status_code == 409
    assert otra.json()["error"]["code"] == "TARJETA_NO_BLOQUEADA"


def test_el_desbloqueo_exige_una_persona_que_pueda_bloquear(cliente, autorizacion, por_persona, abrir_cuenta):
    tarjeta = _tarjeta_bloqueada(cliente, autorizacion, abrir_cuenta())
    encabezados, _ = por_persona("ASESOR")  # sin BLOQUEAR_TARJETA
    respuesta = cliente.post(f"/coredb/tarjetas/{tarjeta}/desbloqueo", headers=encabezados,
                             json={"motivo": "Sin permiso"})
    assert respuesta.status_code == 403


def test_el_desbloqueo_de_una_tarjeta_que_no_existe_es_404(cliente, por_persona):
    encabezados, _ = por_persona("OPERADOR")
    respuesta = cliente.post(f"/coredb/tarjetas/{uuid.uuid4()}/desbloqueo", headers=encabezados,
                             json={"motivo": "No existe"})
    assert respuesta.status_code == 404
