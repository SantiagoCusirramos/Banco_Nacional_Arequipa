import httpx

from TARJETAS.tests.test_tarjetas import AUTH, BASE, EMISION, HEADERS_EMISION, ID, TARJETA_CORE


def test_humo_openapi_lista_los_endpoints(client):
    rutas = client.get("/openapi.json").json()["paths"]
    for ruta in [
        f"{BASE}/cliente/{{cod_cliente}}",
        f"{BASE}/emision",
        f"{BASE}/{{id_tarjeta}}",
        f"{BASE}/{{id_tarjeta}}/bloqueo",
        f"{BASE}/{{id_tarjeta}}/estado",
    ]:
        assert ruta in rutas


def test_humo_docs_disponible(client):
    assert client.get("/docs").status_code == 200


def test_humo_flujo_completo(client, core):
    core.respuesta = httpx.Response(201, json=TARJETA_CORE)
    assert client.post(f"{BASE}/emision", json=EMISION, headers=HEADERS_EMISION).status_code == 201
    core.respuesta = httpx.Response(200, json=TARJETA_CORE)
    assert client.post(f"{BASE}/{ID}/estado", json={"estado": "ACTIVA"}, headers=AUTH).status_code == 200
    assert client.get(f"{BASE}/{ID}", headers=AUTH).status_code == 200
    core.respuesta = httpx.Response(200, json=[TARJETA_CORE])
    assert client.get(f"{BASE}/cliente/CLI000000001", headers=AUTH).status_code == 200
    core.respuesta = httpx.Response(200, json=TARJETA_CORE)
    assert client.post(f"{BASE}/{ID}/bloqueo", json={"motivo": "Perdida"}, headers=AUTH).status_code == 200
    assert len(core.llamadas) == 5


def test_humo_todas_las_respuestas_traen_envelope(client, core):
    core.respuesta = httpx.Response(200, json=TARJETA_CORE)
    ok = client.get(f"{BASE}/{ID}", headers=AUTH).json()
    assert {"success", "status_code", "message", "data", "metadata"} <= ok.keys()
    mal = client.get("/api/v1/no-existe").json()
    assert {"success", "status_code", "error_code", "message", "details", "metadata"} <= mal.keys()
