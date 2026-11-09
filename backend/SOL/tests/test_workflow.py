"""Pruebas de aceptación del recorrido, límites de autoridad y reintentos."""

import copy
import json
from datetime import date
from SOL.clock import business_today
from decimal import Decimal
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from conftest import auth
from SOL.app import create_app
from SOL.finance import calendar
from SOL.models import Base
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
