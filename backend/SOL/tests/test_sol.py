"""SOL sin base propia: login por COREDB, borrador en COREDB, CR-INT-01/02/03 y bitácora."""

import json
from uuid import uuid4

import pytest

from SOL.service import operation_id
from SOL.settings import Settings
from conftest import CLIENT, GUARANTOR, PASSWORD, TOKENS, auth, form, reference, settings


def create(client, headers, **changes):
    response = client.post("/sol/applications", json=form(**changes), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def send(client, headers, application, key=None):
    return client.post(f"/sol/applications/{application['id']}/send", json={"revision": application["revision"]},
                       headers={**headers, "X-Idempotency-Key": key or str(uuid4())})


def result(bus, application, decision="APROBADO", **changes):
    detail = bus.solicitudes[application["id"]]
    evaluation = detail["evaluaciones"][-1]
    operation = str(uuid4())
    body = {"idSolicitud": application["id"], "versionSolicitud": 1, "idEvaluacion": evaluation["idEvaluacion"],
            "ronda": evaluation["ronda"], "idOperacion": operation, "idCorrelacion": operation,
            "decision": decision, "observaciones": "Aprobado por la regla R-A (RN-EVA-002-P)."}
    body.update(changes)
    return body


def callback(client, body, token=TOKENS["callback_token"]):
    return client.post("/sol/integrations/evaluation-results", json=body, headers={
        "Authorization": "Bearer " + token, "X-Idempotency-Key": body["idOperacion"],
        "X-Correlation-ID": body["idCorrelacion"]})


# ── Configuración ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("changes", [
    {"bus_url": ""}, {"bus_url": "http://user:clave@bus.test/bus"}, {"bus_url": "http://bus.test/bus/"},
    {"cap_token": "corto"}, {"eva_token": TOKENS["cap_token"]}, {"coredb_usuario": ""},
])
def test_configuracion_invalida(changes):
    with pytest.raises(ValueError):
        settings(**changes).validate()


def test_sin_base_propia():
    assert not hasattr(Settings, "database_url")
    import SOL
    from pathlib import Path
    archivos = {p.name for p in Path(SOL.__file__).parent.glob("*.py")}
    assert not archivos & {"database.py", "models.py", "migrations.py", "seed.py", "operations.py", "simulator.py"}


# ── Acceso ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(("username", "rol"), [("asesora", "ASESOR"), ("admin", "SUPERVISOR"), ("auditor", "AUDITOR")])
def test_el_login_es_el_de_coredb_y_su_rol_se_traduce(lab, username, rol):
    client, _ = lab
    response = client.post("/sol/auth/login", json={"username": username, "password": PASSWORD})
    assert response.status_code == 200, response.text
    assert response.json()["usuario"]["rol"] == rol
    headers = {"Authorization": "Bearer " + response.json()["token"]}
    assert client.get("/sol/auth/me", headers=headers).json() == {"username": username, "nombre": username, "rol": rol}


@pytest.mark.parametrize("username", ["analista", "svc-sol"])
def test_un_perfil_sin_sol_no_entra(lab, username):
    client, _ = lab
    password = TOKENS["coredb_secreto"] if username == "svc-sol" else PASSWORD
    response = client.post("/sol/auth/login", json={"username": username, "password": password})
    assert response.status_code == 403
    assert "token" not in response.json()


def test_credenciales_invalidas_y_sesion_requerida(lab):
    client, _ = lab
    assert client.post("/sol/auth/login", json={"username": "asesora", "password": "otra"}).status_code == 401
    assert client.get("/sol/applications").status_code == 401
    assert client.get("/sol/applications", headers={"Authorization": "Bearer tok-nadie"}).status_code == 401


def test_ya_no_hay_rutas_de_laboratorio(lab):
    client, _ = lab
    headers = auth(client)
    assert client.post("/gateway/sol/auth/login", json={}).status_code == 404
    for ruta in ("/sol/applications/x/demo-result", "/sol/applications/x/revise",
                 "/sol/admin/users/asesora/disable"):
        assert client.post(ruta, json={}, headers=headers).status_code in (404, 405)
    assert client.get("/sol/ops/pending", headers=headers).status_code == 404


# ── Borrador ────────────────────────────────────────────────────────────────


def test_el_borrador_se_guarda_en_coredb_con_el_token_de_la_asesora(lab, bus):
    client, _ = lab
    headers = auth(client)
    application = create(client, headers, garantias=[
        {"tipo_garantia": "HIPOTECARIA", "descripcion": "Casa en Cayma", "valor_tasacion": "25000.00"}],
        fiadores=[GUARANTOR])
    assert (application["estado"], application["revision"], application["version"]) == ("REGISTRADA", 1, 1)
    metodo, ruta, cabeceras, cuerpo = next(r for r in bus.requests if r[1].endswith("/creditos/borradores"))
    assert cabeceras["authorization"] == "Bearer tok-asesora"
    assert cuerpo["codCliente"] == CLIENT and cuerpo["destino"] == "Capital de trabajo"
    assert cuerpo["garantias"] == [{"tipo": "HIPOTECARIA", "descripcion": "Casa en Cayma", "valor": "25000.00"}]
    assert cuerpo["fiadores"] == [GUARANTOR] and cuerpo["politica"]["tea"] == "0.2200"
    snapshot = application["versiones"][0]["expediente"]
    assert snapshot["cliente"]["id_cliente"] == CLIENT
    assert "numero_celular" not in json.dumps(application)
    assert snapshot["fiadores"][0]["identidad"]["id_cliente"] == GUARANTOR
    assert len(snapshot["calendario"]["cuotas"]) == 12
    assert [e["accion"] for e in application["eventos"]] == ["CREAR_BORRADOR"]


def test_editar_usa_la_revision_y_coredb_detecta_otra_sesion(lab):
    client, _ = lab
    headers = auth(client)
    application = create(client, headers)
    edited = client.put(f"/sol/applications/{application['id']}", json=form(monto_solicitado="6000.00", revision=1),
                        headers=headers)
    assert edited.status_code == 200, edited.text
    assert (edited.json()["revision"], edited.json()["monto"]) == (2, "6000.00")
    stale = client.put(f"/sol/applications/{application['id']}", json=form(revision=1), headers=headers)
    assert stale.status_code == 409
    assert "otra sesión" in stale.json()["detail"]


def test_el_cliente_de_un_borrador_no_se_cambia(lab):
    client, _ = lab
    headers = auth(client)
    application = create(client, headers)
    response = client.put(f"/sol/applications/{application['id']}", json=form(id_cliente=GUARANTOR, revision=1),
                          headers=headers)
    assert response.status_code == 422


@pytest.mark.parametrize(("changes", "status"), [
    ({"monto_solicitado": "100.00"}, 422), ({"plazo_meses": 2}, 422), ({"moneda": "USD"}, 422),
    ({"fiadores": [CLIENT]}, 422), ({"fiadores": [GUARANTOR, GUARANTOR]}, 422),
    ({"garantias": [{"tipo_garantia": "PERSONAL", "descripcion": "Aval", "valor_tasacion": "10.00"}]}, 422),
    ({"id_cliente": "CLI000000999"}, 422),
])
def test_validaciones_del_borrador(lab, changes, status):
    client, _ = lab
    response = client.post("/sol/preview", json=form(**changes), headers=auth(client))
    assert response.status_code == status, response.text


def test_un_fiador_sin_referencia_vigente_se_rechaza(lab, bus):
    client, _ = lab
    bus.references[GUARANTOR] = reference(GUARANTOR, 2, estado_habilitante="OBSERVADO")
    response = client.post("/sol/preview", json=form(fiadores=[GUARANTOR]), headers=auth(client))
    assert response.status_code == 422
    assert "fiador" in response.json()["detail"]


def test_captacion_caida_es_503(lab, bus):
    client, _ = lab
    bus.cap_down = True
    assert client.post("/sol/preview", json=form(), headers=auth(client)).status_code == 503


def test_solo_la_asesora_escribe(lab):
    client, _ = lab
    for username in ("auditor", "admin"):
        assert client.post("/sol/applications", json=form(), headers=auth(client, username)).status_code == 403


def test_bandeja_con_nombres_de_captacion_y_conteo(lab):
    client, _ = lab
    headers = auth(client)
    application = create(client, headers)
    page = client.get("/sol/applications", headers=auth(client, "auditor"))
    assert page.status_code == 200, page.text
    datos = page.json()
    assert datos["total"] == 1 and datos["estados"] == {"REGISTRADA": 1}
    assert datos["items"][0]["id"] == application["id"]
    assert datos["items"][0]["cliente_nombre"] == "Persona Sintética 1 Prueba"
    assert datos["items"][0]["documento"] == "70000001"


def test_busqueda_de_clientes_por_el_cuerpo(lab, bus):
    client, _ = lab
    response = client.post("/sol/clients/search", json={"search": "70000002"}, headers=auth(client))
    assert response.status_code == 200
    assert [c["id_cliente"] for c in response.json()] == [GUARANTOR]
    assert "numero_celular" not in response.text
    assert not any("70000002" in ruta for _, ruta, _, _ in bus.requests)


# ── CR-INT-02: envío a Evaluación ───────────────────────────────────────────


def test_enviar_pasa_el_borrador_a_evaluacion_y_queda_en_la_bitacora(lab, bus):
    client, _ = lab
    headers = auth(client)
    application = create(client, headers)
    response = send(client, headers, application)
    assert response.status_code == 200, response.text
    datos = response.json()
    assert datos["estado"] == "EN_EVALUACION"
    assert datos["versiones"][0]["congelada"] is True
    assert datos["envios"][0]["id_operacion"] == operation_id(application["id"], 1)
    assert datos["envios"][0]["estado_transporte"] == "CONFIRMADO"
    sobre = next(r[3] for r in bus.requests if r[1] == "/bus/evaluacion/eva/applications")
    assert sobre["idOperacion"] == operation_id(application["id"], 1) and sobre["actorEnvio"] == "asesora"
    assert sobre["expediente"]["calendario"]["total_pagar"]
    (evento,) = bus.events.values()
    assert (evento["accion"], evento["actor"], evento["idEntidad"]) == ("ENVIAR_CR_INT_02", "asesora", application["id"])


def test_reenviar_lo_reconoce_sin_otro_envio(lab, bus):
    client, _ = lab
    headers = auth(client)
    application = create(client, headers)
    assert send(client, headers, application).status_code == 200
    again = send(client, headers, application)
    assert again.status_code == 200 and again.json()["reintento_reconocido"] is True
    assert sum(r[1] == "/bus/evaluacion/eva/applications" for r in bus.requests) == 1


def test_evaluacion_caida_deja_el_envio_pendiente(lab, bus):
    client, _ = lab
    headers = auth(client)
    application = create(client, headers)
    bus.eva_down = True
    pending = send(client, headers, application)
    assert pending.status_code == 202
    assert pending.json()["pendiente_envio"] is True and pending.json()["estado"] == "REGISTRADA"
    bus.eva_down = False
    assert send(client, headers, application).json()["estado"] == "EN_EVALUACION"


def test_enviar_exige_la_revision_vigente_y_la_politica_actual(lab, tmp_path):
    client, app = lab
    headers = auth(client)
    application = create(client, headers)
    stale = client.post(f"/sol/applications/{application['id']}/send", json={"revision": 9},
                        headers={**headers, "X-Idempotency-Key": str(uuid4())})
    assert stale.status_code == 409
    policy = json.loads(app.state.settings.policy_path.read_text())
    policy["tea"] = "0.2500"
    app.state.settings.policy_path.write_text(json.dumps(policy))
    changed = send(client, headers, application)
    assert changed.status_code == 409
    assert "política" in changed.json()["detail"]


def test_la_clave_de_operacion_es_obligatoria(lab):
    client, _ = lab
    headers = auth(client)
    application = create(client, headers)
    response = client.post(f"/sol/applications/{application['id']}/send", json={"revision": 1}, headers=headers)
    assert response.status_code == 422


# ── CR-INT-03: resultado de Evaluación ──────────────────────────────────────


def test_el_resultado_se_valida_contra_coredb_y_se_audita(lab, bus):
    client, _ = lab
    headers = auth(client)
    application = create(client, headers)
    send(client, headers, application)
    bus.evaluate(application["id"], "APROBADO")
    body = result(bus, application)
    response = callback(client, body)
    assert response.status_code == 200, response.text
    assert response.json() == {"recibido": True, "idOperacion": body["idOperacion"], "estado": "APROBADA"}
    repeated = callback(client, body)
    assert repeated.json()["reintento_reconocido"] is True
    audited = [e for e in bus.events.values() if e["accion"] == "RECIBIR_CR_INT_03"]
    assert len(audited) == 1 and audited[0]["detalle"]["decision"] == "APROBADO"
    detail = client.get(f"/sol/applications/{application['id']}", headers=headers).json()
    assert detail["estado"] == "APROBADA"
    assert detail["resultados"][0]["decision"] == "APROBADO"


@pytest.mark.parametrize("changes", [{"decision": "RECHAZADO"}, {"ronda": 2}, {"idEvaluacion": "otra"}])
def test_un_resultado_que_no_coincide_con_coredb_es_409(lab, bus, changes):
    client, _ = lab
    headers = auth(client)
    application = create(client, headers)
    send(client, headers, application)
    bus.evaluate(application["id"], "APROBADO")
    assert callback(client, result(bus, application, **changes)).status_code == 409


def test_el_resultado_exige_el_token_de_evaluacion(lab, bus):
    client, _ = lab
    headers = auth(client)
    application = create(client, headers)
    send(client, headers, application)
    bus.evaluate(application["id"], "APROBADO")
    assert callback(client, result(bus, application), token="otro-" + "x" * 40).status_code == 401
    assert callback(client, result(bus, application), token=TOKENS["eva_token"]).status_code == 401


def test_sin_bitacora_el_resultado_no_se_confirma(lab, bus):
    client, _ = lab
    headers = auth(client)
    application = create(client, headers)
    send(client, headers, application)
    bus.evaluate(application["id"], "APROBADO")
    bus.audit_down = True
    assert callback(client, result(bus, application)).status_code == 503


# ── Operación ───────────────────────────────────────────────────────────────


def test_metricas_para_supervision(lab):
    client, _ = lab
    assert client.get("/sol/ops/metrics", headers=auth(client)).status_code == 403
    assert client.get("/sol/ops/metrics", headers=auth(client, "auditor")).status_code == 200


def test_salud_y_listo(lab):
    client, _ = lab
    assert client.get("/health").json() == {"status": "ok", "modulo": "SOL", "integracion": "REAL"}
    assert client.get("/ready").json() == {"status": "ready", "coredb": "disponible"}
