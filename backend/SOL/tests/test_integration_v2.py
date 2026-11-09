"""Pruebas HTTP con simulador de Bus; no acreditan integración institucional."""
import copy
import os
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from SOL import clock
from SOL.app import create_app
from SOL.integrations import IntegrationError, Integrations
from SOL.migrations import migrate
from SOL.models import (Application, AuditOutbox, Base, ClientReference, Delivery,
                        Event, LoginSession, Outcome, SecurityEvent, User, now)
from SOL.operations import maintenance, process_audit, process_delivery
from SOL.seed import seed
from SOL.settings import Settings
from conftest import PASSWORD, auth
from test_workflow import CLIENT, create, form, send


class BusSimulator:
    """Contrato propuesto; almacena un solo acuse por idOperacion/idEvento."""
    def __init__(self):
        self.references = {}
        self.received = {}
        self.audit_events = {}
        self.calls = []
        self.audit_down = False
        self.timeout_after_receipt = False
        self.status_down = False
        self.send_down = False
        self.bad_receipt = False

    def __call__(self, request):
        self.calls.append((request.method, request.url.path))
        assert request.headers["Authorization"] == "Bearer " + "b"*32
        assert request.headers.get("X-Correlation-ID")
        path = request.url.path
        if path == "/cap/references":
            return httpx.Response(200, json=list(self.references.values()))
        if path.startswith("/cap/references/"):
            data = self.references.get(path.rsplit("/", 1)[1])
            return httpx.Response(200 if data else 404, json=data or {})
        if path.startswith("/eva/operations/"):
            if self.status_down:
                raise httpx.ReadTimeout("Simulador no disponible", request=request)
            data = self.received.get(path.rsplit("/", 1)[1])
            return httpx.Response(200 if data else 404, json=data or {})
        data = json.loads(request.content)
        if path == "/eva/applications":
            assert request.headers["X-Idempotency-Key"] == data["idOperacion"]
            if self.send_down:
                raise httpx.ConnectTimeout("Simulador no disponible", request=request)
            receipt = {k: data[k] for k in ("idSolicitud", "versionSolicitud", "idOperacion")}
            receipt.update(idEvaluacion="EVA-" + data["idSolicitud"], ronda=7 + data["versionSolicitud"], acuse="ACK-" + data["idOperacion"][:12])
            if self.bad_receipt:
                receipt["idSolicitud"] = "ajena"
            self.received.setdefault(data["idOperacion"], receipt)
            if self.timeout_after_receipt:
                self.timeout_after_receipt = False
                raise httpx.ReadTimeout("Aceptado; respuesta perdida", request=request)
            return httpx.Response(200, json=receipt)
        if path == "/security/events":
            assert request.headers["X-Idempotency-Key"] == data["idEvento"]
            if self.audit_down:
                raise httpx.ReadTimeout("Simulador no disponible", request=request)
            self.audit_events.setdefault(data["idEvento"], data)
            return httpx.Response(200, json={"idEvento": data["idEvento"], "confirmado": True, "acuse": "ACK-AUD-" + data["idEvento"]})
        return httpx.Response(404, json={})


@pytest.fixture
def real_lab(tmp_path):
    database = os.getenv("SOL_TEST_DATABASE_URL", "sqlite:///" + str(tmp_path / "real.db"))
    if not database.startswith("sqlite"):
        from sqlalchemy.engine import make_url
        assert make_url(database).database == "bna_sol_mvp_test"
    settings = Settings(database, mode="REAL",
                        bus_base_url="http://bus.simulador.test", bus_token="b"*32,
                        callback_token="c"*32, cap_search_path="/cap/references",
                        cap_reference_path="/cap/references/{idCliente}", eva_send_path="/eva/applications",
                        eva_status_path="/eva/operations/{idOperacion}", audit_path="/security/events",
                        worker_seconds=0)
    bus = BusSimulator()
    app = create_app(settings, httpx.MockTransport(bus))
    from SOL.database import make_database
    ddl_engine = app.state.engine if database.startswith("sqlite") else make_database(settings, for_maintenance=True)[0]
    Base.metadata.drop_all(ddl_engine)
    Base.metadata.create_all(ddl_engine)
    seed(app.state.factory, PASSWORD)
    with app.state.factory() as db:
        bus.references = {r.id: {**r.snapshot, "simulado": False} for r in db.scalars(select(ClientReference))}
    with TestClient(app) as client:
        yield client, app, bus
    Base.metadata.drop_all(ddl_engine)
    ddl_engine.dispose()


def real_create(c, h, **changes):
    r = c.post("/sol/applications", headers=h, json=form(**changes))
    assert r.status_code == 201, r.text
    return r.json()


def real_auth(c, username="asesor.bna"):
    r = c.post("/sol/auth/login", json={"username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def real_send(c, app, h, d, key=None):
    key = key or str(uuid4())
    r = c.post(f"/sol/applications/{d['id']}/send", headers={**h, "X-Idempotency-Key": key}, json={"revision": d["revision"]})
    assert r.status_code == 202, r.text
    assert r.json()["pendiente_envio"]
    return key


def callback(c, app, d, operation=None, **changes):
    with app.state.factory() as db:
        delivery = db.scalar(select(Delivery).where(Delivery.application_id == d["id"], Delivery.version == d["version"]))
        data = {"idSolicitud": d["id"], "versionSolicitud": d["version"], "idEvaluacion": delivery.evaluation_id,
                "ronda": delivery.round, "idOperacion": operation or str(uuid4()), "idCorrelacion": str(uuid4()),
                "decision": "OBSERVADO", "observaciones": "Precisar el destino de prueba.", **changes}
    headers = {"Authorization": "Bearer " + app.state.settings.callback_token,
               "X-Idempotency-Key": data["idOperacion"], "X-Correlation-ID": data["idCorrelacion"]}
    return c.post("/sol/integrations/evaluation-results", headers=headers, json=data), data, headers


def test_lima_night_creation_and_send_no_false_stale(lab, monkeypatch):
    c, _ = lab
    today = clock.business_today()
    # 01:00 UTC del siguiente día = 20:00 del día de negocio actual en Lima.
    instant = datetime.combine(today + timedelta(days=1), datetime.min.time(), timezone.utc) + timedelta(hours=1)
    monkeypatch.setattr(clock, "utc_now", lambda: instant)
    h = auth(c)
    d = create(c, h, fecha_base=today.isoformat())
    assert send(c, h, d).status_code == 200
    assert clock.business_today() == today


def test_lima_midnight_really_expires_old_base(lab, monkeypatch):
    c, _ = lab
    h = auth(c)
    today = clock.business_today()
    d = create(c, h)
    instant = datetime.combine(today + timedelta(days=1), datetime.min.time(), timezone.utc) + timedelta(hours=5)
    monkeypatch.setattr(clock, "utc_now", lambda: instant)
    assert send(c, h, d).status_code == 409


@pytest.mark.parametrize("index,expected", [(1, 201), (3, 422), (4, 422), (5, 422)])
def test_cr01_real_adapter_gate_with_http_simulator(real_lab, index, expected):
    c, _, bus = real_lab
    r = c.post("/sol/applications", headers=real_auth(c), json=form(id_cliente=f"0198b000-0000-7009-8000-{index:012d}"))
    assert r.status_code == expected
    assert any(path.startswith("/cap/references/") for _, path in bus.calls)


def test_real_never_falls_back_to_local_reference(real_lab):
    c, _, bus = real_lab
    del bus.references[CLIENT]
    assert c.post("/sol/applications", headers=real_auth(c), json=form()).status_code == 422


def test_cr02_timeout_after_acceptance_is_reconciled_without_second_post(real_lab):
    c, app, bus = real_lab
    h = real_auth(c)
    d = real_create(c, h)
    bus.timeout_after_receipt = True
    key = real_send(c, app, h, d)
    assert process_delivery(app.state.factory, app.state.integrations, key)
    assert [m for m, p in bus.calls if p.startswith("/eva/")] == ["GET", "POST", "GET"]
    assert len(bus.received) == 1
    r = c.post(f"/sol/applications/{d['id']}/send", headers={**h, "X-Idempotency-Key": key}, json={"revision": d["revision"]})
    assert r.status_code == 200 and r.json()["reintento_reconocido"]
    assert r.json()["estado"] == "EN_EVALUACION"
    with app.state.factory() as db:
        assert db.scalar(select(func.count()).select_from(Delivery)) == 1


def test_cr02_failed_status_consult_never_reposts_and_survives_restart(real_lab):
    c, app, bus = real_lab
    h = real_auth(c)
    d = real_create(c, h)
    key = real_send(c, app, h, d)
    bus.status_down = True
    assert not process_delivery(app.state.factory, app.state.integrations, key)
    assert not any(m == "POST" and p.startswith("/eva/") for m, p in bus.calls)
    assert len([p for _, p in bus.calls if p.startswith("/eva/")]) == 3
    # Reabrir el motor acredita que el pendiente está en disco, no en una lista.
    from SOL.database import make_database
    engine, factory = make_database(app.state.settings)
    with factory() as db:
        row = db.get(Delivery, key)
        assert row.status == "PENDIENTE" and row.receipt == ""
    bus.status_down = False
    assert process_delivery(factory, app.state.integrations, key)
    engine.dispose()
    assert len(bus.received) == 1


def test_cr02_max_two_retries_and_no_edit_of_reserved_version(real_lab):
    c, app, bus = real_lab
    h = real_auth(c)
    d = real_create(c, h)
    key = real_send(c, app, h, d)
    bus.send_down = True
    assert not process_delivery(app.state.factory, app.state.integrations, key)
    assert sum(m == "POST" and p == "/eva/applications" for m, p in bus.calls) == 3
    assert c.put(f"/sol/applications/{d['id']}", headers=h, json=form(revision=d["revision"])).status_code == 409
    assert c.post(f"/sol/applications/{d['id']}/send", headers={**h, "X-Idempotency-Key": str(uuid4())}, json={"revision": d["revision"]}).status_code == 409


def test_cr02_rejects_mismatched_receipt_without_changing_business_state(real_lab):
    c, app, bus = real_lab
    h = real_auth(c)
    d = real_create(c, h)
    key = real_send(c, app, h, d)
    bus.bad_receipt = True
    assert not process_delivery(app.state.factory, app.state.integrations, key)
    with app.state.factory() as db:
        assert db.get(Delivery, key).status == "ERROR_CONTRATO"
        assert db.get(Application, d["id"]).state == "BORRADOR"


def test_cr03_callback_auth_round_version_and_full_v2_cycle(real_lab):
    c, app, bus = real_lab
    h = real_auth(c)
    d = real_create(c, h)
    key = real_send(c, app, h, d)
    assert process_delivery(app.state.factory, app.state.integrations, key)
    assert callback(c, app, d, ronda=999)[0].status_code == 409
    assert callback(c, app, d, idEvaluacion="OTRA")[0].status_code == 409
    observed, data, headers = callback(c, app, d)
    assert observed.status_code == 200 and observed.json()["estado"] == "OBSERVADA"
    assert c.post("/sol/integrations/evaluation-results", headers=headers, json=data).json()["reintento_reconocido"]
    assert c.post("/sol/integrations/evaluation-results", headers={**headers, "Authorization": h["Authorization"]}, json=data).status_code == 401
    assert c.post("/sol/integrations/evaluation-results", headers={**headers, "X-Idempotency-Key": "diferente"}, json=data).status_code == 422
    current = c.get(f"/sol/applications/{d['id']}", headers=h).json()
    revised = c.post(f"/sol/applications/{d['id']}/revise", headers=h, json={"revision": current["revision"]}).json()
    assert revised["version"] == 2
    key2 = real_send(c, app, h, revised)
    assert process_delivery(app.state.factory, app.state.integrations, key2)
    assert callback(c, app, d)[0].status_code == 409
    approved, _, _ = callback(c, app, revised, decision="APROBADO")
    assert approved.status_code == 200 and approved.json()["estado"] == "APROBADA"
    with app.state.factory() as db:
        assert db.scalar(select(func.count()).select_from(Outcome)) == 2
    assert c.post(f"/sol/applications/{d['id']}/demo-result", headers=h, json={"version": 2, "decision": "APROBADO", "observaciones": "Prueba local."}).status_code == 403


def test_cr10_outbox_survives_failure_recovers_and_deduplicates(real_lab):
    c, app, bus = real_lab
    h = real_auth(c)
    real_create(c, h)
    with app.state.factory() as db:
        ids = list(db.scalars(select(AuditOutbox.id)))
        assert len(ids) == 2  # ingreso y creación
    bus.audit_down = True
    assert not process_audit(app.state.factory, app.state.integrations, ids[0])
    with app.state.factory() as db:
        assert db.get(AuditOutbox, ids[0]).status == "PENDIENTE"
    bus.audit_down = False
    for key in ids:
        assert process_audit(app.state.factory, app.state.integrations, key)
        assert not process_audit(app.state.factory, app.state.integrations, key)
    assert len(bus.audit_events) == 2
    with app.state.factory() as db:
        assert all(db.get(AuditOutbox, key).status == "CONFIRMADO" for key in ids)
    # Respuesta perdida tras aceptación: el mismo idEvento no crea otro registro.
    assert app.state.integrations.audit(bus.audit_events[ids[0]])
    assert len(bus.audit_events) == 2


def test_event_and_outbox_rollback_together(real_lab):
    _, app, _ = real_lab
    from SOL.operations import security_event
    with app.state.factory() as db:
        security_event(db, "cuenta:prueba", "PRUEBA_ROLLBACK", str(uuid4()))
        db.flush()
        db.rollback()
    with app.state.factory() as db:
        assert db.scalar(select(func.count()).select_from(SecurityEvent)) == 0
        assert db.scalar(select(func.count()).select_from(AuditOutbox)) == 0


def test_session_revocation_and_cleanup(lab):
    c, app = lab
    h, supervisor = auth(c), auth(c, "supervisor.bna")
    assert c.post("/sol/admin/users/asesor.bna/disable", headers=h, json={"motivo": "Baja de prueba"}).status_code == 403
    r = c.post("/sol/admin/users/asesor.bna/disable", headers=supervisor, json={"motivo": "Baja de prueba"})
    assert r.status_code == 200 and r.json()["sesiones_revocadas"] == 1
    with app.state.factory() as db:
        revoked = next(row.payload for row in db.scalars(select(AuditOutbox)) if row.payload["tipo"] == "SESIONES_REVOCADAS")
        assert revoked["actor"] == "supervisor.bna" and revoked["sujeto"] == "asesor.bna"
    assert c.get("/sol/auth/me", headers=h).status_code == 401
    assert c.post("/sol/auth/login", json={"username": "asesor.bna", "password": PASSWORD}).status_code == 401
    with app.state.factory.begin() as db:
        user = db.scalar(select(User).where(User.username == "auditor.bna"))
        db.add(LoginSession(token_hash="f"*64, user_id=user.id, expires=now()-timedelta(days=1)))
    assert maintenance(app.state.factory, app.state.integrations)["sesiones_eliminadas"] == 1


def test_access_events_lockout_and_no_secrets_in_logs(lab, caplog):
    c, app = lab
    for attempt in range(5):
        assert c.post("/sol/auth/login", json={"username": "asesor.bna" if attempt % 2 else "ASESOR.BNA", "password": "clave-incorrecta"}).status_code == 401
    assert c.post("/sol/auth/login", json={"username": "asesor.bna", "password": PASSWORD}).status_code == 429
    with app.state.factory() as db:
        actions = list(db.scalars(select(SecurityEvent.action)))
        assert actions.count("INGRESO_FALLIDO") == 5
        assert "BLOQUEO_TEMPORAL" in actions and "INTENTO_BLOQUEADO" in actions
    assert PASSWORD not in caplog.text and "clave-incorrecta" not in caplog.text


def test_client_and_legacy_detail_minimization_all_roles(lab):
    c, app = lab
    h = auth(c)
    d = create(c, h)
    # Incluso datos sensibles guardados en una versión v1 se proyectan al leer.
    from SOL.models import Version
    with app.state.factory.begin() as db:
        v = db.scalar(select(Version).where(Version.application_id == d["id"]))
        v.snapshot = {**v.snapshot, "cliente": {**v.snapshot["cliente"], "correo_electronico": "privado@example.com", "fecha_nacimiento": "1990-05-10", "numero_celular": "999999999"}}
    for name in ["asesor.bna", "supervisor.bna", "auditor.bna", "evaluador.demo"]:
        headers = auth(c, name)
        for route in ["/sol/clients", f"/sol/applications/{d['id']}"]:
            data = c.get(route, headers=headers).json()
            assert all(key not in json.dumps(data) for key in ["correo_electronico", "numero_celular", "fecha_nacimiento"])


def test_readiness_when_db_fails_but_liveness_remains(lab, monkeypatch):
    c, app = lab
    def fail():
        raise RuntimeError("No mostrar secretos")
    monkeypatch.setattr(app.state.engine, "connect", fail)
    assert c.get("/health").status_code == 200
    assert c.get("/ready").status_code == 503
    assert "secretos" not in c.get("/ready").text


def test_correlation_logs_and_measured_p95(lab, caplog):
    c, _ = lab
    h = auth(c, "supervisor.bna")
    trace = str(uuid4())
    r = c.get("/sol/applications", headers={**h, "X-Correlation-ID": trace})
    assert r.headers["X-Correlation-ID"] == trace and trace in caplog.text
    data = c.get("/sol/ops/metrics", headers=h).json()
    entry = next(v for v in data["operaciones"] if v["operacion"] == "GET /sol/applications")
    assert entry["muestras"] == 1 and entry["p95_ms"] > 0
    assert c.get("/sol/ops/metrics", headers=auth(c)).status_code == 403
    forged = c.get("/health", headers={"X-Correlation-ID": "malicioso con espacios"})
    assert forged.headers["X-Correlation-ID"] != "malicioso con espacios"


def test_paginated_listing_has_constant_query_count_and_detail_no_lock(lab):
    c, app = lab
    from sqlalchemy import event
    h = auth(c)
    for _ in range(4):
        create(c, h)
    statements = []
    def record(conn, cursor, statement, params, context, many):
        statements.append(statement)
    event.listen(app.state.engine, "before_cursor_execute", record)
    one = c.get("/sol/applications?limit=1&offset=0", headers=h).json()
    first_count = len(statements)
    statements.clear()
    four = c.get("/sol/applications?limit=4&offset=0", headers=h).json()
    assert len(statements) == first_count
    assert one["total"] == four["total"] == 4
    assert len(one["items"]) == 1 and len(four["items"]) == 4
    statements.clear()
    assert c.get("/sol/applications/" + one["items"][0]["id"], headers=h).status_code == 200
    assert not any("FOR UPDATE" in q.upper() for q in statements)
    event.remove(app.state.engine, "before_cursor_execute", record)
    assert c.get("/sol/applications?limit=1000", headers=h).status_code == 422


def test_incremental_migration_preserves_v1_records(tmp_path):
    from sqlalchemy import create_engine, inspect
    engine = create_engine("sqlite:///" + str(tmp_path/"v1.db"))
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE mvp_sol_usuario (id VARCHAR(36) PRIMARY KEY, username VARCHAR(60), name VARCHAR(100), role VARCHAR(20), password_hash VARCHAR(250))"))
        conn.execute(text("INSERT INTO mvp_sol_usuario VALUES ('original', 'asesor', 'Prueba', 'ASESOR', 'hash-conservado')"))
    migrate(engine)
    migrate(engine)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT password_hash, active FROM mvp_sol_usuario")).first() == ("hash-conservado", 1)
    assert "mvp_sol_auditoria_pendiente" in inspect(engine).get_table_names()
    engine.dispose()


def test_real_requires_explicit_configuration_and_retry_limit():
    with pytest.raises(ValueError):
        create_app(Settings("sqlite://", mode="REAL"))
    with pytest.raises(ValueError):
        create_app(Settings("sqlite://", max_retries=3))


def test_event_order_follows_revision_when_mysql_timestamps_tie(lab):
    c, app = lab
    from sqlalchemy import update
    from test_workflow import result
    h, evaluator = auth(c), auth(c, "evaluador.demo")
    d = create(c, h)
    d = send(c, h, d).json()
    assert result(c, evaluator, d, decision="APROBADO").status_code == 200
    with app.state.factory.begin() as db:
        db.execute(update(Event).values(date=datetime(2026, 10, 23, 12)))
    events = c.get("/sol/applications/" + d["id"], headers=h).json()["eventos"]
    assert [e["accion"] for e in events] == ["CREAR_BORRADOR", "ENVIAR_CR_INT_02_SIMULADO", "RECIBIR_CR_INT_03_SIMULADO"]
