"""Pruebas de aceptación del recorrido, límites de autoridad y reintentos."""

import copy
import json
from datetime import date, timedelta
from SOL.clock import business_today
from decimal import Decimal
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from pydantic import ValidationError
from conftest import auth
from SOL.app import create_app
from SOL.finance import calendar
from SOL.integrations import CLIENT_FIELDS
from SOL.models import Application, AuditOutbox, Base, ClientReference, Delivery, Event, Version
from SOL.schemas import ApplicationInput
from SOL.seed import seed
from SOL.settings import Settings

PREFIX = "/gateway/sol"
CLIENT = "0198b000-0000-7009-8000-000000000001"


def form(**changes):
    return {
        "id_cliente": CLIENT,
        "monto_solicitado": "15000.00",
        "moneda": "PEN",
        "plazo_meses": 12,
        "destino_credito": "Mejoras en la vivienda",
        "fecha_base": business_today().isoformat(),
        **changes,
    }


def create(client, headers, **changes):
    response = client.post(
        PREFIX + "/applications", headers=headers, json=form(**changes)
    )
    assert response.status_code == 201, response.text
    return response.json()


def send(client, headers, application, key=None):
    return client.post(
        f"{PREFIX}/applications/{application['id']}/send",
        headers={**headers, "X-Idempotency-Key": key or str(uuid4())},
        json={"revision": application["revision"]},
    )


def result(client, headers, application, decision="OBSERVADO", key=None, version=None):
    return client.post(
        f"{PREFIX}/applications/{application['id']}/demo-result",
        headers={**headers, "X-Idempotency-Key": key or str(uuid4())},
        json={
            "version": version or application["version"],
            "decision": decision,
            "observaciones": "Precisar destino del crédito para la prueba.",
        },
    )


@pytest.mark.parametrize(
    "value,expected",
    [
        ("999.99", 422),
        ("1000.00", 201),
        ("50000.00", 201),
        ("50000.01", 422),
        ("0", 422),
        ("-10", 422),
        ("1000.001", 422),
    ],
)
def test_amount_boundaries(lab, value, expected):
    c, _ = lab
    r = c.post(
        PREFIX + "/applications", headers=auth(c), json=form(monto_solicitado=value)
    )
    assert r.status_code == expected


@pytest.mark.parametrize(
    "months,expected", [(5, 422), (6, 201), (60, 201), (61, 422), (6.5, 422)]
)
def test_month_boundaries(lab, months, expected):
    c, _ = lab
    assert (
        c.post(
            PREFIX + "/applications", headers=auth(c), json=form(plazo_meses=months)
        ).status_code
        == expected
    )


@pytest.mark.parametrize("index", [3, 4, 5])
def test_captacion_gate(lab, index):
    c, _ = lab
    assert (
        c.post(
            PREFIX + "/applications",
            headers=auth(c),
            json=form(id_cliente=f"0198b000-0000-7009-8000-{index:012d}"),
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "username", ["supervisor.bna", "auditor.bna", "evaluador.demo"]
)
def test_readonly_roles_cannot_create(lab, username):
    c, _ = lab
    assert (
        c.post(
            PREFIX + "/applications", headers=auth(c, username), json=form()
        ).status_code
        == 403
    )


def test_session_logout_and_actor_cannot_be_spoofed(lab):
    c, _ = lab
    assert c.get(PREFIX + "/applications").status_code == 401
    h = auth(c)
    assert (
        c.post(
            PREFIX + "/applications", headers=h, json=form(actor="otro.usuario")
        ).status_code
        == 422
    )
    assert c.post(PREFIX + "/auth/logout", headers=h).status_code == 200
    assert c.get(PREFIX + "/applications", headers=h).status_code == 401


def test_assessor_cannot_evaluate(lab):
    c, _ = lab
    h = auth(c)
    d = create(c, h)
    assert send(c, h, d).status_code == 200
    assert result(c, h, d).status_code == 403


def test_idempotency_and_frozen_version(lab):
    c, _ = lab
    h = auth(c)
    d = create(c, h)
    key = str(uuid4())
    one, two = send(c, h, d, key), send(c, h, d, key)
    assert one.status_code == two.status_code == 200
    assert two.json()["reintento_reconocido"]
    assert len(two.json()["envios"]) == 1
    assert len(two.json()["eventos"]) == 2
    assert two.json()["versiones"][0]["congelada"]
    r = c.put(
        f"{PREFIX}/applications/{d['id']}",
        headers=h,
        json=form(revision=two.json()["revision"]),
    )
    assert r.status_code == 409
    other = create(c, h)
    assert send(c, h, other, key).status_code == 409


def test_subsanation_preserves_old_snapshot_and_rejects_stale_results(lab):
    c, _ = lab
    h, eva = auth(c), auth(c, "evaluador.demo")
    d = create(c, h)
    sent = send(c, h, d).json()
    frozen = copy.deepcopy(sent["versiones"][0])
    key = str(uuid4())
    observed = result(c, eva, sent, key=key)
    assert observed.status_code == 200
    assert result(c, eva, sent, key=key).json()["reintento_reconocido"]
    d = observed.json()
    revised = c.post(
        f"{PREFIX}/applications/{d['id']}/revise",
        headers=h,
        json={"revision": d["revision"]},
    ).json()
    assert revised["version"] == 2
    edited = c.put(
        f"{PREFIX}/applications/{d['id']}",
        headers=h,
        json=form(revision=revised["revision"], monto_solicitado="18000.00"),
    ).json()
    assert edited["versiones"][0] == frozen
    assert send(c, h, edited).status_code == 200
    assert result(c, eva, edited, version=1).status_code == 409
    approved = result(c, eva, edited, decision="APROBADO")
    assert approved.status_code == 200
    assert approved.json()["estado"] == "APROBADA"
    assert approved.json()["eventos"][-1]["actor"] == "evaluador.demo"


def test_optimistic_concurrency(lab):
    c, _ = lab
    h = auth(c)
    d = create(c, h)
    route = f"{PREFIX}/applications/{d['id']}"
    assert c.put(route, headers=h, json=form(revision=d["revision"])).status_code == 200
    assert c.put(route, headers=h, json=form(revision=d["revision"])).status_code == 409


def test_policy_changes_require_recalculation_but_preserve_sent_policy(lab):
    c, app = lab
    h = auth(c)
    d = create(c, h)
    before = d["versiones"][0]["expediente"]["politica"]
    p = app.state.settings.policy_path
    updated = json.loads(p.read_text())
    updated.update(version="SOL-DEMO-2026-02", monto_maximo="20000.00", tea="0.1800")
    p.write_text(json.dumps(updated))
    assert send(c, h, d).status_code == 409
    assert (
        c.get(f"{PREFIX}/applications/{d['id']}", headers=h).json()["versiones"][0][
            "expediente"
        ]["politica"]
        == before
    )
    changed = c.put(
        f"{PREFIX}/applications/{d['id']}", headers=h, json=form(revision=d["revision"])
    ).json()
    assert (
        changed["versiones"][0]["expediente"]["politica"]["version"]
        == updated["version"]
    )
    assert send(c, h, changed).status_code == 200
    p.write_text("{}")
    assert c.get(PREFIX + "/policy", headers=h).status_code == 503
    assert c.post(PREFIX + "/applications", headers=h, json=form()).status_code == 503


def test_fiadores_currency_and_double_payment(lab):
    c, _ = lab
    h = auth(c)
    for changes in [
        {"fiadores": [CLIENT]},
        {"fiadores": ["no-existe"]},
        {"moneda": "USD"},
        {"pago_doble": True},
    ]:
        assert (
            c.post(
                PREFIX + "/applications", headers=h, json=form(**changes)
            ).status_code
            == 422
        )
    d = create(
        c,
        h,
        fiadores=["0198b000-0000-7009-8000-000000000002"],
        garantias=[
            {
                "tipo_garantia": "VEHICULAR",
                "descripcion": "Vehículo declarado de prueba",
                "valor_tasacion": "12000.00",
            }
        ],
    )
    assert len(d["versiones"][0]["expediente"]["fiadores"]) == 1


def test_persistence_after_restart(tmp_path):
    # No depender de memoria demuestra persistencia real de expedientes/sesiones.
    settings = Settings("sqlite:///" + str(tmp_path / "persistencia.db"), worker_seconds=0)
    first = create_app(settings)
    Base.metadata.create_all(first.state.engine)
    seed(first.state.factory, "PruebaBNA2026!")
    with TestClient(first) as c:
        h = auth(c)
        d = create(c, h)
    second = create_app(settings)
    with TestClient(second) as c:
        restored = c.get(f"{PREFIX}/applications/{d['id']}", headers=h)
        assert restored.status_code == 200
        assert restored.json()["codigo"] == d["codigo"]


@pytest.mark.parametrize("tea,months", [("0", 6), ("0.22", 12), ("0.22", 60)])
def test_calendar_invariants(tea, months):
    data = calendar(Decimal("15000.00"), Decimal(tea), months, date(2026, 10, 21))
    rows = data["cuotas"]
    assert len(rows) == months
    assert sum(Decimal(r["amortizacion"]) for r in rows) == Decimal("15000.00")
    assert rows[-1]["saldo_final"] == "0.00"
    assert all(
        Decimal(r["cuota_total"]) == Decimal(r["amortizacion"]) + Decimal(r["interes"])
        for r in rows
    )
    assert rows[0]["fecha_vencimiento"] == "2026-11-20"


def business_counts(app):
    with app.state.factory() as db:
        return tuple(db.scalar(select(func.count()).select_from(model))
                     for model in (Application, Version, Event, Delivery, AuditOutbox))


def test_e02_invalid_conditions_and_guarantees_never_mutate_draft(lab):
    c, app = lab
    h = auth(c)
    d = create(c, h)
    route = f"{PREFIX}/applications/{d['id']}"
    before = business_counts(app)
    guarantee = {"tipo_garantia": "VEHICULAR", "descripcion": "Respaldo sintético", "valor_tasacion": "12000.00"}
    invalid = [
        {"monto_solicitado": "NaN"}, {"monto_solicitado": "Infinity"},
        {"monto_solicitado": "999.99"}, {"monto_solicitado": "15000.001"},
        {"plazo_meses": True}, {"plazo_meses": "12"}, {"plazo_meses": 6.5},
        {"plazo_meses": 61}, {"moneda": "USD"}, {"moneda": "pen"},
        {"moneda": "PENN"}, {"fecha_base": (business_today() - timedelta(days=1)).isoformat()},
        {"pago_doble": True},
        *[{"garantias": [{**guarantee, **change}]} for change in [
            {"tipo_garantia": "DESCONOCIDA"}, {"descripcion": "   "},
            {"valor_tasacion": "0"}, {"valor_tasacion": "-1"},
            {"valor_tasacion": "12.001"}, {"valor_tasacion": "NaN"},
            {"campo_no_admitido": "dato-sintetico"},
        ]],
        {"garantias": [guarantee] * 11},
    ]
    for changes in invalid:
        for suffix in ("/preview", "/applications"):
            response = c.post(PREFIX + suffix, headers=h, json=form(**changes))
            assert response.status_code == 422
        response = c.put(route, headers=h, json=form(revision=d["revision"], **changes))
        assert response.status_code == 422
        assert c.get(route, headers=h).json() == d
        assert business_counts(app) == before


def test_e02_policy_limits_apply_to_preview_create_and_edit(lab):
    c, app = lab
    h = auth(c)
    d = create(c, h)
    path = app.state.settings.policy_path
    policy = json.loads(path.read_text())
    # Política sintética temporal, sin alterar la propuesta versionada del repositorio.
    policy.update(version="E02-TEST", monto_minimo="2000.00", monto_maximo="16000.00",
                  plazo_minimo_meses=10, plazo_maximo_meses=24)
    path.write_text(json.dumps(policy))
    for changes in [{"monto_solicitado": "1999.99"}, {"monto_solicitado": "16000.01"},
                    {"plazo_meses": 9}, {"plazo_meses": 25}]:
        assert c.post(PREFIX + "/preview", headers=h, json=form(**changes)).status_code == 422
        assert c.post(PREFIX + "/applications", headers=h, json=form(**changes)).status_code == 422
        assert c.put(f"{PREFIX}/applications/{d['id']}", headers=h,
                     json=form(revision=d["revision"], **changes)).status_code == 422
    for amount, months in [("2000.00", 10), ("16000.00", 24)]:
        preview = c.post(PREFIX + "/preview", headers=h,
                         json=form(monto_solicitado=amount, plazo_meses=months))
        assert preview.status_code == 200
        saved = create(c, h, monto_solicitado=amount, plazo_meses=months)
        assert saved["versiones"][0]["expediente"] == preview.json()
        assert saved["monto"] == amount and saved["plazo"] == months


@pytest.mark.parametrize("amount,months,tea", [
    ("1000.00", 6, "0.22"), ("1000.00", 60, "0.22"),
    ("50000.00", 6, "0.22"), ("50000.00", 60, "0.22"),
    ("1000.01", 60, "0"),
])
def test_e02_calendar_cent_precision_dates_and_totals(amount, months, tea):
    start = date(2028, 1, 31)
    schedule = calendar(Decimal(amount), Decimal(tea), months, start)
    balance = Decimal(amount)
    total_interest, total_paid = Decimal(0), Decimal(0)
    for index, row in enumerate(schedule["cuotas"], 1):
        assert row["numero_cuota"] == index
        assert date.fromisoformat(row["fecha_vencimiento"]) == start + timedelta(days=30 * index)
        for key in ["saldo_inicial", "amortizacion", "interes", "cuota_total", "saldo_final"]:
            assert Decimal(row[key]).as_tuple().exponent == -2
            assert Decimal(row[key]) >= 0
        assert Decimal(row["saldo_inicial"]) == balance
        balance -= Decimal(row["amortizacion"])
        assert Decimal(row["saldo_final"]) == balance
        assert Decimal(row["cuota_total"]) == Decimal(row["amortizacion"]) + Decimal(row["interes"])
        if index < months:
            assert row["cuota_total"] == schedule["cuota_referencial"]
        total_interest += Decimal(row["interes"])
        total_paid += Decimal(row["cuota_total"])
    assert balance == 0 and len(schedule["cuotas"]) == months
    assert Decimal(schedule["intereses_totales"]) == total_interest
    assert Decimal(schedule["total_pagar"]) == total_paid == Decimal(amount) + total_interest
    assert schedule["estado"] == "PRELIMINAR"


def test_e02_guarantees_and_guarantors_versioned_with_recalculated_calendar(lab):
    c, app = lab
    h = auth(c)
    guarantor = "0198b000-0000-7009-8000-000000000002"
    guarantee = {"tipo_garantia": "VEHICULAR", "descripcion": "Respaldo de prueba", "valor_tasacion": "12000.00"}
    d = create(c, h, garantias=[guarantee], fiadores=[guarantor])
    route = f"{PREFIX}/applications/{d['id']}"
    assert d["versiones"][0]["expediente"]["condiciones"]["garantias"] == [guarantee]
    assert d["versiones"][0]["expediente"]["fiadores"][0]["validacion"] == "SIMULADA"
    changed = c.put(route, headers=h, json=form(revision=d["revision"], monto_solicitado="18000.00",
                    plazo_meses=24, garantias=[{**guarantee, "valor_tasacion": "13000.00"}], fiadores=[guarantor]))
    assert changed.status_code == 200
    changed = changed.json()
    assert changed["versiones"][0]["expediente"]["calendario"] != d["versiones"][0]["expediente"]["calendario"]
    # La pestaña antigua no puede sobrescribir los respaldos.
    assert c.put(route, headers=h, json=form(revision=d["revision"], garantias=[])).status_code == 409
    sent = send(c, h, changed).json()
    frozen = copy.deepcopy(sent["versiones"][0])
    observed = result(c, auth(c, "evaluador.demo"), sent).json()
    revised = c.post(route + "/revise", headers=h, json={"revision": observed["revision"]}).json()
    edited = c.put(route, headers=h, json=form(revision=revised["revision"], garantias=[], fiadores=[]))
    assert edited.status_code == 200
    detail = edited.json()
    assert detail["versiones"][0] == frozen
    assert detail["versiones"][1]["expediente"]["condiciones"]["garantias"] == []
    assert detail["versiones"][1]["expediente"]["fiadores"] == []
    with app.state.factory() as db:
        stored = db.scalar(select(Version).where(Version.application_id == d["id"], Version.number == 1))
        assert stored.snapshot == frozen["expediente"]


def test_e02_all_guarantee_types_and_maximum_are_supported(lab):
    c, _ = lab
    h = auth(c)
    guarantees = [{"tipo_garantia": kind, "descripcion": "Respaldo sintético declarado", "valor_tasacion": "0.01"}
                  for kind in ["PERSONAL", "HIPOTECARIA", "VEHICULAR", "MOBILIARIA", "FONDOS"]] * 2
    d = create(c, h, garantias=guarantees)
    assert d["versiones"][0]["expediente"]["condiciones"]["garantias"] == guarantees


def test_e02_payment_double_policy_cannot_bypass_block(lab):
    c, app = lab
    h = auth(c)
    d = create(c, h)
    path = app.state.settings.policy_path
    policy = json.loads(path.read_text())
    policy["pago_doble_habilitado"] = True
    path.write_text(json.dumps(policy))
    before = business_counts(app)
    assert c.get(PREFIX + "/policy", headers=h).status_code == 503
    for suffix in ("/preview", "/applications"):
        assert c.post(PREFIX + suffix, headers=h, json=form(pago_doble=True)).status_code == 503
    assert send(c, h, d).status_code == 503
    assert business_counts(app) == before
    assert c.get(f"{PREFIX}/applications/{d['id']}", headers=h).json() == d


def test_e02_readonly_roles_cannot_preview_or_edit_backing(lab):
    c, _ = lab
    d = create(c, auth(c))
    for username in ["supervisor.bna", "auditor.bna", "evaluador.demo"]:
        h = auth(c, username)
        assert c.post(PREFIX + "/preview", headers=h, json=form()).status_code == 403
        assert c.put(f"{PREFIX}/applications/{d['id']}", headers=h,
                     json=form(revision=d["revision"], garantias=[], fiadores=[])).status_code == 403


@pytest.mark.parametrize("identifier", ["", "   ", "x" * 37, None, 123])
def test_e02_guarantor_reference_format(identifier):
    with pytest.raises(ValidationError):
        ApplicationInput.model_validate(form(fiadores=[identifier]))


def test_e02_guarantor_minimizes_identity_and_rejects_duplicates(lab):
    c, app = lab
    h = auth(c)
    identifier = "0198b000-0000-7009-8000-000000000002"
    with app.state.factory.begin() as db:
        ref = db.get(ClientReference, identifier)
        ref.snapshot = {**ref.snapshot, "dato_extra_sensible": "SINTETICO-NO-EXPORTAR"}
    response = c.post(PREFIX + "/preview", headers=h, json=form(fiadores=[identifier]))
    assert response.status_code == 200
    identity = response.json()["fiadores"][0]["identidad"]
    assert set(identity).issubset(CLIENT_FIELDS)
    assert response.json()["fiadores"][0]["validacion"] == "SIMULADA"
    before = business_counts(app)
    for references in [[identifier, identifier], [" " + identifier + " ", identifier],
                       [CLIENT], ["no-existe"], ["0198b000-0000-7009-8000-000000000004"],
                       [identifier] * 6]:
        assert c.post(PREFIX + "/applications", headers=h, json=form(fiadores=references)).status_code == 422
    assert business_counts(app) == before


def test_e02_guarantor_history_is_minimized_without_rewriting_snapshot(lab):
    c, app = lab
    h = auth(c)
    identifier = "0198b000-0000-7009-8000-000000000002"
    d = create(c, h, fiadores=[identifier])
    with app.state.factory.begin() as db:
        version = db.scalar(select(Version).where(Version.application_id == d["id"]))
        legacy = copy.deepcopy(version.snapshot)
        legacy["fiadores"][0]["identidad"]["dato_extra_sensible"] = "SINTETICO-NO-EXPORTAR"
        version.snapshot = legacy
    for username in ["asesor.bna", "supervisor.bna", "auditor.bna", "evaluador.demo"]:
        response = c.get(f"{PREFIX}/applications/{d['id']}", headers=auth(c, username))
        assert response.status_code == 200
        identity = response.json()["versiones"][0]["expediente"]["fiadores"][0]["identidad"]
        assert set(identity).issubset(CLIENT_FIELDS)
    with app.state.factory() as db:
        stored = db.scalar(select(Version).where(Version.application_id == d["id"]))
        assert stored.snapshot == legacy


def test_e02_guarantor_reference_keeps_identifier_agnostic_contract():
    for identifier in ["f", "x" * 36]:
        assert ApplicationInput.model_validate(form(fiadores=[identifier])).fiadores == [identifier]


@pytest.mark.parametrize("microsecond", [0, 499999, 500000, 999999])
def test_e06_written_detail_matches_persisted_timestamp(lab, monkeypatch, microsecond):
    # MySQL DATETIME(0) redondea; SQLite conserva microsegundos. La respuesta
    # de escritura debe coincidir con la lectura, sin aparentar otra edición.
    from SOL.models import now
    instant = now().replace(microsecond=microsecond)
    monkeypatch.setattr("SOL.service.now", lambda: instant)
    c, _ = lab
    h = auth(c)
    d = create(c, h)
    route = f"{PREFIX}/applications/{d['id']}"
    assert c.get(route, headers=h).json() == d
    edited = c.put(route, headers=h, json=form(revision=d["revision"])).json()
    assert c.get(route, headers=h).json() == edited
