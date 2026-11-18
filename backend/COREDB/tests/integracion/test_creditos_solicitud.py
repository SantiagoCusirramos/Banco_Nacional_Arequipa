"""Créditos: el borrador de SOL y el receptor de eventos de módulos (CONTRATO_CREDITOS.md §6),
contra la base real (bd-v1.14-mysql)."""

import uuid
from datetime import date

import pytest
from creditos_apoyo import BASE, calendario, sesion_servicio
from fastapi.testclient import TestClient

from COREDB.main import app

POLITICA = {"version": "SOL-DEMO-2026-01", "tea": "0.2200", "amortizacion": "FRANCES", "dias_por_periodo": 30}


@pytest.fixture
def api():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def asesor(autorizacion, datos_base):
    api = TestClient(app)
    username, password = "u" + uuid.uuid4().hex[:12], "clave-de-un-usuario-1"
    creado = api.post("/coredb/usuarios", headers=autorizacion, json={
        "username": username, "nombre": "Asesora", "password": password, "rol": "ASESOR"})
    assert creado.status_code == 201, creado.text
    login = api.post("/coredb/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, username


@pytest.fixture(scope="module")
def evaluacion(autorizacion, datos_base):
    return sesion_servicio(autorizacion, "EVALUACION")


@pytest.fixture(scope="module")
def sol(autorizacion, datos_base):
    return sesion_servicio(autorizacion, "SOLICITUD DE CREDITO")


@pytest.fixture
def cliente(admin, datos_base):
    """Un cliente ACTIVO nuevo: un cliente respalda una sola solicitud como fiador."""

    def _crear(estado="ACTIVO"):
        sufijo = uuid.uuid4().hex[:8].upper()
        cod, verificacion = "S" + sufijo, "VC-S" + sufijo
        numero = str(uuid.uuid4().int)[:8]
        with admin.cursor() as cursor:
            cursor.execute("INSERT INTO clientes.verificacion_captacion (id_verificacion_captacion, "
                           "estado_habilitante) VALUES (%s, 'HABILITADO')", (verificacion,))
            cursor.execute(
                "INSERT INTO clientes.cliente (cod_cliente, tipo_documento, numero_documento, nombres, "
                "apellido_paterno, correo, celular, estado_cliente, id_verificacion_captacion, version_contrato) "
                "VALUES (%s, 'DNI', %s, 'Fiador', 'Prueba', %s, %s, %s, %s, 'v1')",
                (cod, numero, f"{cod.lower()}@example.com", "9" + numero, estado, verificacion))
        return cod

    return _crear


def borrador(cod_cliente="C001", fiadores=(), garantias=None, **cambios):
    cuerpo = {
        "idSolicitud": str(uuid.uuid4()), "codCliente": cod_cliente, "montoSolicitado": "3000.00",
        "moneda": "PEN", "plazoMeses": 3, "condicionPagoDoble": False, "destino": "Capital de trabajo",
        "fechaBase": date.today().isoformat(), "politica": POLITICA,
        "garantias": garantias if garantias is not None else [
            {"tipo": "HIPOTECARIA", "descripcion": "Casa en Cayma", "valor": "25000.00"}],
        "fiadores": list(fiadores),
    }
    cuerpo.update(cambios)
    return cuerpo


def edicion(cuerpo, revision, **cambios):
    datos = {k: v for k, v in cuerpo.items() if k != "idSolicitud"}
    datos.update(revision=revision, **cambios)
    return datos


def crear(api, asesor, **datos):
    cuerpo = borrador(**datos)
    respuesta = api.post(f"{BASE}/borradores", json=cuerpo, headers=asesor[0])
    assert respuesta.status_code == 201, respuesta.text
    return cuerpo, respuesta.json()


# ── Borrador ────────────────────────────────────────────────────────────────


def test_crea_el_borrador_y_lo_audita_con_el_asesor(api, asesor, cliente, consulta):
    fiador = cliente()
    correlacion = str(uuid.uuid4())
    cuerpo = borrador(fiadores=[fiador])
    respuesta = api.post(f"{BASE}/borradores", json=cuerpo, headers={**asesor[0], "X-Correlation-ID": correlacion})
    assert respuesta.status_code == 201, respuesta.text
    datos = respuesta.json()
    assert datos["idSolicitud"] == cuerpo["idSolicitud"]
    assert (datos["revision"], datos["estado"]) == (1, "REGISTRADA")
    assert datos["codigo"] == "SOL-" + date.today().strftime("%y%m") + "-" + cuerpo["idSolicitud"][:8].upper()
    (evento,) = consulta("SELECT actor, BIN_TO_UUID(correlation_id) AS c FROM core.evento_auditoria "
                         "WHERE accion = 'CREAR_BORRADOR' AND id_entidad = %s", cuerpo["idSolicitud"])
    assert evento == {"actor": asesor[1], "c": correlacion}


def test_repetir_la_creacion_devuelve_lo_mismo_y_otro_contenido_es_409(api, asesor):
    cuerpo, creado = crear(api, asesor)
    repetido = api.post(f"{BASE}/borradores", json=cuerpo, headers=asesor[0])
    assert repetido.status_code == 200, repetido.text
    assert repetido.json() == creado
    otro = api.post(f"{BASE}/borradores", json={**cuerpo, "destino": "Otro destino del crédito"}, headers=asesor[0])
    assert otro.status_code == 409
    assert otro.json()["error"]["code"] == "IDEMPOTENCIA_CONFLICTO"


def test_editar_exige_la_revision_vigente(api, asesor):
    cuerpo, _ = crear(api, asesor)
    ruta = f"{BASE}/borradores/{cuerpo['idSolicitud']}"
    editado = api.put(ruta, json=edicion(cuerpo, 1, montoSolicitado="3500.00", garantias=[]), headers=asesor[0])
    assert editado.status_code == 200, editado.text
    assert editado.json()["revision"] == 2
    repetido = api.put(ruta, json=edicion(cuerpo, 1, montoSolicitado="3500.00", garantias=[]), headers=asesor[0])
    assert (repetido.status_code, repetido.json()["revision"]) == (200, 2)
    viejo = api.put(ruta, json=edicion(cuerpo, 1, montoSolicitado="4000.00"), headers=asesor[0])
    assert viejo.status_code == 409
    assert viejo.json()["error"]["code"] == "REVISION_DESACTUALIZADA"
    detalle = api.get(f"{BASE}/solicitudes/{cuerpo['idSolicitud']}", headers=asesor[0]).json()
    assert (detalle["montoSolicitado"], detalle["garantias"], detalle["expediente"]["revision"]) == ("3500.00", [], 2)


def test_editar_un_borrador_que_no_existe_es_404(api, asesor):
    cuerpo = borrador()
    respuesta = api.put(f"{BASE}/borradores/{cuerpo['idSolicitud']}", json=edicion(cuerpo, 1), headers=asesor[0])
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["code"] == "SOLICITUD_NO_ENCONTRADA"


def test_el_detalle_tiene_expediente_garantias_y_fiadores(api, asesor, cliente):
    fiador = cliente()
    cuerpo, creado = crear(api, asesor, fiadores=[fiador])
    detalle = api.get(f"{BASE}/solicitudes/{cuerpo['idSolicitud']}", headers=asesor[0])
    assert detalle.status_code == 200, detalle.text
    datos = detalle.json()
    assert datos["estado"] == "REGISTRADA"
    assert (datos["codigo"], datos["revision"]) == (creado["codigo"], 1)
    assert datos["expediente"]["destino"] == "Capital de trabajo"
    assert datos["expediente"]["fechaBase"] == cuerpo["fechaBase"]
    assert datos["expediente"]["politica"] == POLITICA
    assert datos["garantias"] == [{"tipo": "HIPOTECARIA", "descripcion": "Casa en Cayma", "valor": "25000.00",
                                   "moneda": "PEN", "estado": "REGISTRADA"}]
    assert [f["codCliente"] for f in datos["fiadores"]] == [fiador]
    assert datos["calendario"] is None and datos["recepciones"] == []
    assert [h["estado"] for h in datos["historial"]] == ["REGISTRADA"]


def test_la_bandeja_separa_los_borradores_y_cuenta_por_estado(api, asesor, cliente):
    titular = cliente()
    cuerpo, _ = crear(api, asesor, cod_cliente=titular)
    sin_estado = api.get(f"{BASE}/solicitudes", params={"codCliente": titular}, headers=asesor[0])
    assert sin_estado.status_code == 200, sin_estado.text
    assert sin_estado.json() == []
    borradores = api.get(f"{BASE}/solicitudes", params={"codCliente": titular, "estado": "REGISTRADA"},
                         headers=asesor[0]).json()
    assert [(s["idSolicitud"], s["revision"]) for s in borradores] == [(cuerpo["idSolicitud"], 1)]
    todas = api.get(f"{BASE}/solicitudes", params={"codCliente": titular, "borradores": "true"},
                    headers=asesor[0]).json()
    assert [s["estado"] for s in todas] == ["REGISTRADA"]
    conteo = api.get(f"{BASE}/solicitudes/conteo", params={"codCliente": titular}, headers=asesor[0])
    assert conteo.status_code == 200, conteo.text
    assert conteo.json() == {"total": 1, "estados": {"REGISTRADA": 1}}


def test_el_expediente_del_borrador_lo_pasa_a_evaluacion(api, asesor, evaluacion):
    cuerpo, _ = crear(api, asesor)
    expediente = {"idSolicitud": cuerpo["idSolicitud"], "versionSolicitud": 1, "codCliente": "C001",
                  "montoSolicitado": "3000.00", "moneda": "PEN", "plazoMeses": 3,
                  "destino": "Capital de trabajo", "calendario": calendario("3000.00", 3)}
    recibido = api.post(f"{BASE}/solicitudes", json=expediente, headers=evaluacion[0])
    assert recibido.status_code == 201, recibido.text
    assert (recibido.json()["estado"], recibido.json()["ronda"]) == ("EN_EVALUACION", 1)
    datos = api.get(f"{BASE}/solicitudes/{cuerpo['idSolicitud']}", headers=asesor[0]).json()
    assert [(r["versionSolicitud"], r["ronda"], r["idEvaluacion"]) for r in datos["recepciones"]] == [
        (1, 1, recibido.json()["idEvaluacion"])]
    assert [h["estado"] for h in datos["historial"]] == ["REGISTRADA", "EN_EVALUACION"]
    editar = api.put(f"{BASE}/borradores/{cuerpo['idSolicitud']}", json=edicion(cuerpo, 1), headers=asesor[0])
    assert editar.status_code == 422
    assert editar.json()["error"]["code"] == "SOLICITUD_NO_ADMITIDA"


@pytest.mark.parametrize(("cambios", "codigo"), [
    ({"garantias": [{"tipo": "PERSONAL", "descripcion": "Aval personal", "valor": "100.00"}]}, "GARANTIA_NO_ADMITIDA"),
    ({"fiadores": ["C001"]}, "FIADOR_NO_ADMITIDO"),
    ({"codCliente": "NOEXISTE"}, "CLIENTE_NO_HABILITADO"),
])
def test_rechazos_del_borrador(api, asesor, cambios, codigo):
    respuesta = api.post(f"{BASE}/borradores", json=borrador(**{}) | cambios, headers=asesor[0])
    assert respuesta.status_code == 422, respuesta.text
    assert respuesta.json()["error"]["code"] == codigo
    assert "NOEXISTE" not in respuesta.text


def test_un_fiador_respalda_una_sola_solicitud(api, asesor, cliente):
    fiador = cliente()
    crear(api, asesor, fiadores=[fiador])
    respuesta = api.post(f"{BASE}/borradores", json=borrador(fiadores=[fiador]), headers=asesor[0])
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "FIADOR_NO_ADMITIDO"


def test_validacion_del_cuerpo_del_borrador(api, asesor):
    assert api.post(f"{BASE}/borradores", json=borrador(destino="Uso"), headers=asesor[0]).status_code == 422
    assert api.post(f"{BASE}/borradores", json=borrador(fiadores=["A", "B", "C", "D", "E", "F"]),
                    headers=asesor[0]).status_code == 422
    snake = borrador()
    snake["cod_cliente"] = snake.pop("codCliente")
    assert api.post(f"{BASE}/borradores", json=snake, headers=asesor[0]).status_code == 422


def test_permisos_del_borrador(api, sol, evaluacion):
    assert api.post(f"{BASE}/borradores", json=borrador()).status_code == 401
    for encabezados in (sol[0], evaluacion[0]):
        respuesta = api.post(f"{BASE}/borradores", json=borrador(), headers=encabezados)
        assert respuesta.status_code == 403
        assert respuesta.json()["error"]["code"] == "PERMISO_DENEGADO"


def test_svc_sol_lee_las_solicitudes(api, asesor, sol):
    cuerpo, _ = crear(api, asesor)
    assert api.get(f"{BASE}/solicitudes/{cuerpo['idSolicitud']}", headers=sol[0]).status_code == 200


# ── Eventos de auditoría de los módulos ─────────────────────────────────────


def evento(**cambios):
    cuerpo = {"idEvento": str(uuid.uuid4()), "accion": "RECIBIR_CR_INT_03", "entidad": "solicitud_credito",
              "idEntidad": str(uuid.uuid4()), "actor": "servicio:EVA", "detalle": {"decision": "APROBADO"}}
    cuerpo.update(cambios)
    return cuerpo


def test_svc_sol_registra_un_evento_una_sola_vez(api, sol, autorizacion):
    correlacion = str(uuid.uuid4())
    cuerpo = evento()
    creado = api.post("/coredb/auditoria/eventos", json=cuerpo, headers={**sol[0], "X-Correlation-ID": correlacion})
    assert creado.status_code == 201, creado.text
    datos = creado.json()
    assert (datos["idEvento"], datos["confirmado"]) == (cuerpo["idEvento"], True)
    assert datos["acuse"] == f"AUD-{datos['idRegistro']}"
    repetido = api.post("/coredb/auditoria/eventos", json=cuerpo, headers=sol[0])
    assert (repetido.status_code, repetido.json()) == (200, datos)
    otro = api.post("/coredb/auditoria/eventos", json={**cuerpo, "detalle": {"decision": "RECHAZADO"}},
                    headers=sol[0])
    assert otro.status_code == 409
    assert otro.json()["error"]["code"] == "IDEMPOTENCIA_CONFLICTO"
    (registrado,) = api.get("/coredb/auditoria", params={"id_entidad": cuerpo["idEntidad"]},
                            headers=autorizacion).json()
    assert (registrado["modulo"], registrado["accion"], registrado["actor"]) == (
        "SOLICITUD DE CREDITO", "RECIBIR_CR_INT_03", "servicio:EVA")
    assert registrado["correlation_id"] == correlacion
    assert registrado["detalle"] == {"decision": "APROBADO", "id_evento_modulo": cuerpo["idEvento"],
                                     "reportado_por": sol[1]}


def test_solo_un_modulo_con_permiso_registra_eventos(api, evaluacion, asesor):
    for encabezados in (evaluacion[0], asesor[0]):
        respuesta = api.post("/coredb/auditoria/eventos", json=evento(), headers=encabezados)
        assert respuesta.status_code == 403
    assert api.post("/coredb/auditoria/eventos", json=evento()).status_code == 401


@pytest.mark.parametrize("cambios", [
    {"accion": "borrar todo"}, {"actor": ""}, {"detalle": {"x": "y" * 5000}}, {"otro": 1},
])
def test_validacion_del_evento(api, sol, cambios):
    assert api.post("/coredb/auditoria/eventos", json=evento(**cambios), headers=sol[0]).status_code == 422

