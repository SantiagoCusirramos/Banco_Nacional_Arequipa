"""Proveedores separados, Bus legado y referencias mínimas; sin servicios externos."""
import copy
import json
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select

from SOL.app import create_app
from SOL.clock import business_today
from SOL.integrations import Integrations, IntegrationError, normalize_reference
from SOL.models import Base, ClientReference, Version
from SOL.operations import process_delivery
from SOL.seed import seed
from SOL.settings import Settings
from conftest import PASSWORD, auth
from test_workflow import CLIENT, create, form


def settings(**changes):
    return Settings("sqlite://", mode="REAL", worker_seconds=0,
        callback_token="callback-sintetico-" + "c" * 32,
        cap_base_url="http://cap.test", cap_token="cap-sintetico-" + "a" * 32,
        eva_base_url="http://eva.test", eva_token="eva-sintetico-" + "e" * 32,
        audit_base_url="http://audit.test", audit_token="audit-sintetico-" + "s" * 32,
        cap_search_path="/cap/references", cap_reference_path="/cap/references/{idCliente}",
        eva_send_path="/eva/applications", eva_status_path="/eva/operations/{idOperacion}",
        audit_path="/security/events", **changes)


def reference():
    today = business_today()
    return {"id_cliente": CLIENT, "numero_documento": "DOC-SINTETICO", "nombres": "Persona",
        "apellido_paterno": "Sintetica", "apellido_materno": "Prueba", "estado_cliente": "ACTIVO",
        "id_caso": "caso-sintetico", "id_verificacion": "ver-sintetica",
        "fecha_verificacion": today.isoformat(), "vigente_hasta": (today + timedelta(days=1)).isoformat(),
        "estado_habilitante": "HABILITADO", "version_contrato": "CR-INT-01-PROPUESTA-v2", "simulado": True}


def test_separate_providers_receive_only_their_own_credentials_and_reconcile():
    cfg = settings(); cfg.validate()
    calls, receipts = [], {}
    expected = {"cap.test": cfg.cap_token, "eva.test": cfg.eva_token, "audit.test": cfg.audit_token}
    envelope = {"idSolicitud": "sol-sintetica", "versionSolicitud": 1,
                "idOperacion": str(uuid4()), "idCorrelacion": str(uuid4()), "expediente": {}}
    def provider(request):
        calls.append((request.method, request.url.host, request.url.path))
        assert request.headers["Authorization"] == "Bearer " + expected[request.url.host]
        assert all(cfg.callback_token not in value for value in request.headers.values())
        if request.url.host == "cap.test":
            return httpx.Response(200, json=[reference()] if request.url.path == "/cap/references" else reference())
        if request.url.host == "audit.test":
            payload = json.loads(request.content)
            assert request.headers["X-Idempotency-Key"] == payload["idEvento"]
            return httpx.Response(200, json={"idEvento": payload["idEvento"], "confirmado": True, "acuse": "ACK-sintetico"})
        if request.method == "GET":
            receipt = receipts.get(envelope["idOperacion"])
            return httpx.Response(200 if receipt else 404, json=receipt or {})
        assert json.loads(request.content) == envelope
        assert request.headers["X-Idempotency-Key"] == envelope["idOperacion"]
        assert request.headers["X-Correlation-ID"] == envelope["idCorrelacion"]
        receipts[envelope["idOperacion"]] = {k: envelope[k] for k in ["idSolicitud", "versionSolicitud", "idOperacion"]}
        receipts[envelope["idOperacion"]].update(idEvaluacion="EVA-sintetica", ronda=3, acuse="ACK-EVA")
        raise httpx.ReadTimeout("Respuesta perdida sintética", request=request)
    adapter = Integrations(cfg, httpx.MockTransport(provider))
    try:
        assert adapter.clients("prueba", "trace") == [reference()]
        assert adapter.reference(CLIENT, "trace") == reference()
        first = adapter.deliver(envelope)
        assert adapter.deliver(envelope) == first and first["ronda"] == 3
        assert adapter.audit({"idEvento": str(uuid4()), "idCorrelacion": "trace"}) == "ACK-sintetico"
        assert sum(m == "POST" and h == "eva.test" for m, h, _ in calls) == 1
    finally:
        adapter.close()


@pytest.mark.parametrize("provider", ["cap", "eva", "audit"])
@pytest.mark.parametrize("missing", ["base_url", "token"])
def test_partial_override_is_rejected_even_when_bus_is_configured(provider, missing):
    cfg = replace(settings(), bus_base_url="http://bus.test", bus_token="bus-" + "b" * 32,
                  **{provider + "_" + missing: ""})
    with pytest.raises(ValueError):
        cfg.validate()


@pytest.mark.parametrize("provider", ["cap", "eva", "audit"])
def test_missing_provider_without_bus_is_explicit_error(provider):
    cfg = replace(settings(), **{provider + "_base_url": "", provider + "_token": ""})
    with pytest.raises(ValueError):
        cfg.validate()
    with pytest.raises(ValueError):
        Integrations(cfg)


@pytest.mark.parametrize("provider", ["cap", "eva", "audit"])
def test_provider_cannot_reuse_callback_credential(provider):
    with pytest.raises(ValueError):
        replace(settings(), **{provider + "_token": settings().callback_token}).validate()


def test_bus_legacy_and_explicit_whole_pair_override():
    cfg = replace(settings(), cap_base_url="", cap_token="", audit_base_url="", audit_token="",
                  bus_base_url="http://bus.test", bus_token="bus-" + "b" * 32)
    cfg.validate()
    seen = []
    def provider(request):
        seen.append(request.url.host)
        token = cfg.eva_token if request.url.host == "eva.test" else cfg.bus_token
        assert request.headers["Authorization"] == "Bearer " + token
        return httpx.Response(200, json=reference())
    adapter = Integrations(cfg, httpx.MockTransport(provider))
    try:
        adapter.reference(CLIENT, "trace")
        adapter.request("GET", "/legacy", "trace")
        adapter.request("GET", "/eva/operations/operacion-sintetica", "trace", provider="eva")
        assert seen == ["bus.test", "bus.test", "eva.test"]
    finally:
        adapter.close()


@pytest.mark.parametrize("failure", [401, 503, "timeout"])
def test_real_cap_failure_never_falls_back_to_bus_or_simulation(failure):
    cfg = replace(settings(), bus_base_url="http://bus.test", bus_token="bus-" + "b" * 32)
    calls = []
    def provider(request):
        calls.append(request.url.host)
        if failure == "timeout":
            raise httpx.ConnectTimeout("Fallo sintético", request=request)
        return httpx.Response(failure, json={"detail": "Fallo sintético"})
    adapter = Integrations(cfg, httpx.MockTransport(provider))
    try:
        with pytest.raises(HTTPException) as exc:
            adapter.reference(CLIENT, "trace")
        assert exc.value.status_code == 503 and set(calls) == {"cap.test"}
    finally:
        adapter.close()


@pytest.mark.parametrize("materno", ["ausente", None, "", "Prueba"])
def test_optional_maternal_surname_in_reference_and_search(materno):
    data = reference()
    if materno == "ausente":
        data.pop("apellido_materno")
    else:
        data["apellido_materno"] = materno
    before = copy.deepcopy(data)
    adapter = Integrations(settings(), httpx.MockTransport(lambda r: httpx.Response(
        200, json=[data] if r.url.path == "/cap/references" else data)))
    try:
        for value in [adapter.reference(CLIENT, "trace"), adapter.clients("", "trace")[0]]:
            assert value["apellido_materno"] == ("Prueba" if materno == "Prueba" else "")
            assert value["simulado"] is True
        assert data == before
    finally:
        adapter.close()


@pytest.mark.parametrize("materno", [123, False, [], {}])
def test_non_text_maternal_surname_is_not_accepted(materno):
    with pytest.raises(ValueError):
        normalize_reference({**reference(), "apellido_materno": materno})


@pytest.mark.parametrize("change,status", [
    ({"vigente_hasta": "2000-01-01"}, 422), ({"estado_habilitante": "REVOCADO"}, 422),
    ({"estado_cliente": "BLOQUEADO"}, 422), ({"id_caso": ""}, 503),
])
def test_optional_surname_does_not_relax_cap_gate(change, status):
    adapter = Integrations(settings(), httpx.MockTransport(lambda r: httpx.Response(
        200, json={**reference(), "apellido_materno": None, **change})))
    try:
        with pytest.raises(HTTPException) as exc:
            adapter.reference(CLIENT, "trace")
        assert exc.value.status_code == status
    finally:
        adapter.close()


@pytest.mark.parametrize("materno", ["ausente", None, ""])
def test_simulated_optional_surname_and_history_projection(lab, materno):
    c, app = lab
    with app.state.factory.begin() as db:
        ref = db.get(ClientReference, CLIENT)
        data = copy.deepcopy(ref.snapshot)
        if materno == "ausente":
            data.pop("apellido_materno")
        else:
            data["apellido_materno"] = materno
        ref.snapshot = data
    h = auth(c)
    preview = c.post("/sol/preview", headers=h, json=form())
    assert preview.status_code == 200
    assert preview.json()["cliente"]["apellido_materno"] == ""
    d = create(c, h)
    with app.state.factory.begin() as db:
        v = db.scalar(select(Version).where(Version.application_id == d["id"]))
        snapshot = copy.deepcopy(v.snapshot)
        snapshot["cliente"].pop("apellido_materno")
        v.snapshot = snapshot
    detail = c.get("/sol/applications/" + d["id"], headers=h)
    assert detail.status_code == 200
    assert detail.json()["versiones"][0]["expediente"]["cliente"]["apellido_materno"] == ""
    assert "null" not in detail.json()["cliente_nombre"]
    assert c.get("/sol/clients", headers=h).status_code == 200
    assert c.get("/sol/applications", headers=h).status_code == 200
    with app.state.factory() as db:
        assert db.scalar(select(Version).where(Version.application_id == d["id"])).snapshot == snapshot


def test_provider_environment_configuration(monkeypatch):
    cfg = settings()
    for field in ["cap_base_url", "cap_token", "eva_base_url", "eva_token", "audit_base_url", "audit_token",
                  "cap_search_path", "cap_reference_path", "eva_send_path", "eva_status_path", "audit_path"]:
        monkeypatch.setenv("SOL_" + field.upper(), getattr(cfg, field))
    monkeypatch.setenv("SOL_INTEGRATION_MODE", "REAL")
    monkeypatch.setenv("SOL_EVA_CALLBACK_TOKEN", cfg.callback_token)
    monkeypatch.delenv("SOL_BUS_BASE_URL", raising=False)
    monkeypatch.delenv("SOL_BUS_TOKEN", raising=False)
    parsed = Settings.from_env(); parsed.validate()
    for field in ["cap_base_url", "cap_token", "eva_base_url", "eva_token", "audit_base_url", "audit_token"]:
        assert getattr(parsed, field) == getattr(cfg, field)


@pytest.mark.parametrize("provider", ["cap", "eva", "audit"])
@pytest.mark.parametrize("url", ["https://user:clave@host.test", "ftp://host.test", "http://host.test:mal", "http://host.test/?secreto=1"])
def test_invalid_provider_urls_are_rejected_without_echoing_values(provider, url):
    with pytest.raises(ValueError) as exc:
        replace(settings(), **{provider + "_base_url": url}).validate()
    assert url not in str(exc.value) and "clave" not in str(exc.value)


@pytest.mark.parametrize("path", ["https://ajeno.test/", "//ajeno.test/", "/\\ajeno.test/"])
def test_request_cannot_route_credentials_to_another_host(path):
    calls = []
    adapter = Integrations(settings(), httpx.MockTransport(lambda r: calls.append(r)))
    try:
        with pytest.raises(IntegrationError):
            adapter.request("GET", path, "trace", provider="cap")
        assert not calls
    finally:
        adapter.close()


def test_simulated_mode_never_contacts_configured_http_providers(lab):
    cfg = replace(settings(), mode="SIMULADO")
    calls = []
    adapter = Integrations(cfg, httpx.MockTransport(lambda r: calls.append(r)))
    try:
        envelope = {"idSolicitud": "sol-sintetica", "versionSolicitud": 1, "idOperacion": str(uuid4())}
        assert adapter.deliver(envelope)["idOperacion"] == envelope["idOperacion"]
        assert adapter.audit({"idEvento": "evento-sintetico"}).startswith("AUD-DEMO-")
        assert not calls
    finally:
        adapter.close()


def test_real_three_provider_workflow_preserves_pending_callback_and_subsanation():
    cfg, receipts, calls = settings(), {}, []
    expected = {"cap.test": cfg.cap_token, "eva.test": cfg.eva_token, "audit.test": cfg.audit_token}
    def provider(request):
        calls.append((request.method, request.url.host))
        assert request.headers["Authorization"] == "Bearer " + expected[request.url.host]
        if request.url.host == "cap.test":
            return httpx.Response(200, json={**reference(), "apellido_materno": None})
        if request.url.host == "eva.test" and request.method == "GET":
            value = receipts.get(request.url.path.rsplit("/", 1)[1])
            return httpx.Response(200 if value else 404, json=value or {})
        body = json.loads(request.content)
        if request.url.host == "eva.test":
            result = {k: body[k] for k in ["idSolicitud", "versionSolicitud", "idOperacion"]}
            result.update(idEvaluacion="EVA-sintetica-" + str(body["versionSolicitud"]),
                          ronda=10 + body["versionSolicitud"], acuse="ACK-sintetico")
            receipts[body["idOperacion"]] = result
            return httpx.Response(201, json=result)
        return httpx.Response(200, json={"idEvento": body["idEvento"], "confirmado": True, "acuse": "ACK-audit-sintetico"})
    app = create_app(cfg, httpx.MockTransport(provider))
    Base.metadata.create_all(app.state.engine)
    seed(app.state.factory, PASSWORD)
    with TestClient(app) as c:
        login = c.post("/sol/auth/login", json={"username": "asesor.bna", "password": PASSWORD})
        h = {"Authorization": "Bearer " + login.json()["token"]}
        created = c.post("/sol/applications", headers=h, json=form())
        assert created.status_code == 201
        d = created.json()
        route = "/sol/applications/" + d["id"]
        assert d["versiones"][0]["expediente"]["cliente"]["apellido_materno"] == ""
        for version, decision in [(1, "OBSERVADO"), (2, "APROBADO")]:
            operation = str(uuid4())
            revision = d["revision"]
            pending = c.post(route + "/send", headers={**h, "X-Idempotency-Key": operation}, json={"revision": revision})
            assert pending.status_code == 202
            assert pending.json()["versiones"][-1]["congelada"]
            assert c.put(route, headers=h, json=form(revision=revision)).status_code == 409
            assert process_delivery(app.state.factory, app.state.integrations, operation)
            repeat = c.post(route + "/send", headers={**h, "X-Idempotency-Key": operation}, json={"revision": revision})
            assert repeat.status_code == 200 and repeat.json()["reintento_reconocido"]
            receipt = receipts[operation]
            result_op, trace = str(uuid4()), str(uuid4())
            payload = {k: receipt[k] for k in ["idSolicitud", "versionSolicitud", "idEvaluacion", "ronda"]}
            payload.update(idOperacion=result_op, idCorrelacion=trace, decision=decision, observaciones="Resultado sintético de prueba")
            headers = {"Authorization": "Bearer " + cfg.callback_token, "X-Idempotency-Key": result_op, "X-Correlation-ID": trace}
            assert c.post("/sol/integrations/evaluation-results", headers={**headers, "Authorization": "Bearer " + cfg.eva_token}, json=payload).status_code == 401
            callback = c.post("/sol/integrations/evaluation-results", headers=headers, json=payload)
            assert callback.status_code == 200
            assert c.post("/sol/integrations/evaluation-results", headers=headers, json=payload).json()["reintento_reconocido"]
            d = c.get(route, headers=h).json()
            if version == 1:
                assert d["estado"] == "OBSERVADA"
                frozen = copy.deepcopy(d["versiones"][0])
                d = c.post(route + "/revise", headers=h, json={"revision": d["revision"]}).json()
                assert d["version"] == 2
            else:
                assert d["estado"] == "APROBADA" and d["versiones"][0] == frozen
        assert len(d["envios"]) == 2
        assert sum(m == "POST" and host == "eva.test" for m, host in calls) == 2
