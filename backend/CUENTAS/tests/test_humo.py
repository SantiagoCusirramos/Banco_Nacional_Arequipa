import httpx

from CUENTAS.tests.test_cuentas import (
    APERTURA, BASE, CUENTA_CORE, HEADERS_OP, KEY, MOV_CORE, NUM,
)


def test_humo_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy", "modulo": "cuentas"}


def test_humo_openapi_lista_los_endpoints(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    rutas = r.json()["paths"]
    for ruta in [
        f"{BASE}/apertura",
        f"{BASE}/deposito",
        f"{BASE}/retiro",
        f"{BASE}/transferencia",
        f"{BASE}/consolidada/{{id_cliente}}",
        f"{BASE}/{{num_cuenta}}",
    ]:
        assert ruta in rutas


def test_humo_docs_disponible(client):
    assert client.get("/docs").status_code == 200


def test_humo_flujo_completo(client, core):
    core.respuesta = httpx.Response(201, json=CUENTA_CORE)
    assert client.post(f"{BASE}/apertura", json=APERTURA).status_code == 201

    core.respuesta = httpx.Response(200, json=CUENTA_CORE)
    assert client.get(f"{BASE}/{NUM}").status_code == 200

    core.respuesta = httpx.Response(200, json=[CUENTA_CORE])
    assert client.get(f"{BASE}/consolidada/CLI-1").status_code == 200

    core.respuesta = httpx.Response(201, json=MOV_CORE)
    dep = client.post(f"{BASE}/deposito", json={"num_cuenta": NUM, "monto": "100.00"}, headers=HEADERS_OP)
    assert dep.status_code == 201
    ret = client.post(f"{BASE}/retiro", json={"num_cuenta": NUM, "monto": "40.00"}, headers=HEADERS_OP)
    assert ret.status_code == 201

    core.respuesta = httpx.Response(201, json={
        "origen": {**MOV_CORE, "num_cuenta": "111"},
        "destino": {**MOV_CORE, "num_cuenta": "222"},
        "id_asiento": "a1", "replay": False,
    })
    tr = client.post(f"{BASE}/transferencia", headers=HEADERS_OP,
                     json={"num_cuenta_origen": "111", "num_cuenta_destino": "222", "monto": "10"})
    assert tr.status_code == 201
    assert len(core.llamadas) == 6


def test_humo_todas_las_respuestas_traen_envelope(client, core):
    core.respuesta = httpx.Response(200, json=CUENTA_CORE)
    ok = client.get(f"{BASE}/{NUM}").json()
    assert {"success", "status_code", "message", "data", "metadata"} <= ok.keys()
    mal = client.get("/api/v1/no-existe").json()
    assert {"success", "status_code", "error_code", "message", "details", "metadata"} <= mal.keys()


def test_humo_idempotency_key_se_devuelve_en_cabecera(client, core):
    core.respuesta = httpx.Response(201, json=MOV_CORE)
    r = client.post(f"{BASE}/deposito", json={"num_cuenta": NUM, "monto": "1"}, headers=HEADERS_OP)
    assert r.headers["X-Idempotency-Key"] == KEY
