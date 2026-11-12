import json
import logging
from datetime import date

import httpx

from TARJETAS.services import tarjetas as svc

BASE = "/api/v1/tarjetas"
ID = "7e570001-0000-4000-8000-000000000001"
TOKEN = "Bearer token-de-prueba"
AUTH = {"Authorization": TOKEN}

TARJETA_CORE = {
    "id_tarjeta": ID, "bin": "004499", "ultimos4": "0001", "fecha_emision": "2026-01-15",
    "fecha_vencimiento": "2030-01-31", "estado_tarjeta": "ACTIVA", "cod_cliente": "CLI000000001",
}
EMISION = {"cod_cliente": "cli000000001", "num_cuenta": "10100000000001"}
KEY = "550e8400-e29b-41d4-a716-446655440000"
HEADERS_EMISION = {"X-Idempotency-Key": KEY, **AUTH}


def error_core(status, code, message="mensaje de core"):
    return httpx.Response(status, json={"error": {"code": code, "message": message}})


def test_health(client):
    assert client.get("/health").json() == {"status": "healthy", "modulo": "tarjetas"}


def test_tarjetas_del_cliente_formato_de_exito(client, core):
    core.respuesta = httpx.Response(200, json=[TARJETA_CORE])
    r = client.get(f"{BASE}/cliente/cli000000001", headers={"X-Correlation-ID": ID, **AUTH})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["success"] is True
    assert cuerpo["metadata"]["modulo_emisor"] == "TARJETAS"
    assert cuerpo["metadata"]["uuid_transaccion"] == ID
    tarjeta = cuerpo["data"][0]
    assert tarjeta["numero_enmascarado"] == "0044 99** **** 0001"
    assert tarjeta["vencimiento_mm_aa"] == "01/30"
    llamada = core.llamadas[0]
    assert (llamada["metodo"], llamada["ruta"]) == ("GET", "/coredb/tarjetas")
    assert llamada["query"] == {"cod_cliente": "CLI000000001"}
    assert llamada["headers"]["authorization"] == TOKEN
    assert llamada["headers"]["x-correlation-id"] == ID


def test_sin_token_401_sin_llamar_a_core(client, core):
    r = client.get(f"{BASE}/cliente/CLI000000001")
    assert r.status_code == 401
    assert r.json()["error_code"] == "ERR-TAR-TOKEN-REQUERIDO"
    assert core.llamadas == []


def test_token_sin_bearer_401(client, core):
    r = client.get(f"{BASE}/{ID}", headers={"Authorization": "Basic abc"})
    assert r.json()["error_code"] == "ERR-TAR-TOKEN-INVALIDO"


def test_ver_tarjeta(client, core):
    core.respuesta = httpx.Response(200, json=TARJETA_CORE)
    r = client.get(f"{BASE}/{ID}", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["data"]["id_tarjeta"] == ID
    assert core.llamadas[0]["ruta"] == f"/coredb/tarjetas/{ID}"


def test_id_que_no_es_uuid_400_sin_llamar_a_core(client, core):
    r = client.get(f"{BASE}/no-es-uuid", headers=AUTH)
    assert r.status_code == 400
    assert r.json()["error_code"] == "ERR-TAR-ID-INVALIDO"
    assert core.llamadas == []


def test_tarjeta_inexistente_404(client, core):
    core.respuesta = error_core(404, "TARJETA_NO_ENCONTRADA")
    r = client.get(f"{BASE}/{ID}", headers=AUTH)
    assert r.status_code == 404
    assert r.json()["error_code"] == "ERR-TAR-NO-ENCONTRADA"


def test_cliente_inexistente_404(client, core):
    core.respuesta = error_core(404, "CLIENTE_NO_ENCONTRADO")
    r = client.get(f"{BASE}/cliente/NOEXISTE", headers=AUTH)
    assert r.json()["error_code"] == "ERR-CLI-NO-ENCONTRADO"


def test_emision_envia_un_token_y_no_el_pan(client, core):
    core.respuesta = httpx.Response(201, json={**TARJETA_CORE, "estado_tarjeta": "PENDIENTE_ACTIVACION"})
    r = client.post(f"{BASE}/emision", json=EMISION, headers=HEADERS_EMISION)
    assert r.status_code == 201
    assert r.json()["message"] == "Tarjeta emitida, pendiente de activación"
    enviado = core.llamadas[0]["json"]
    assert core.llamadas[0]["ruta"] == "/coredb/tarjetas"
    assert len(enviado["pan_token"]) == 32 and int(enviado["pan_token"], 16) >= 0
    assert enviado["ultimos4"].isdigit() and len(enviado["ultimos4"]) == 4
    assert enviado["cod_cliente"] == "CLI000000001"
    assert enviado["bin"] == "004499"
    assert enviado["fecha_emision"] == date.today().isoformat()
    emision, vencimiento = date.fromisoformat(enviado["fecha_emision"]), date.fromisoformat(enviado["fecha_vencimiento"])
    assert vencimiento.year - emision.year == 4


def test_emision_respeta_las_fechas_y_los_ultimos4(client, core):
    core.respuesta = httpx.Response(201, json=TARJETA_CORE)
    datos = {**EMISION, "fecha_emision": "2026-01-15", "fecha_vencimiento": "2030-01-31", "ultimos4": "1234"}
    client.post(f"{BASE}/emision", json=datos, headers=HEADERS_EMISION)
    enviado = core.llamadas[0]["json"]
    assert (enviado["fecha_emision"], enviado["fecha_vencimiento"], enviado["ultimos4"]) == (
        "2026-01-15", "2030-01-31", "1234")


def test_emision_que_vence_antes_de_emitirse_400(client, core):
    datos = {**EMISION, "fecha_emision": "2026-01-15", "fecha_vencimiento": "2026-01-15"}
    r = client.post(f"{BASE}/emision", json=datos, headers=HEADERS_EMISION)
    assert r.status_code == 400
    assert r.json()["error_code"] == "ERR-VALIDACION-ESQUEMA"
    assert core.llamadas == []


def test_emision_con_un_pan_se_rechaza(client, core):
    r = client.post(f"{BASE}/emision", json={**EMISION, "pan": "4111111111111111"}, headers=HEADERS_EMISION)
    assert r.status_code == 400
    assert "4111111111111111" not in r.text
    assert core.llamadas == []


def test_emision_sin_llave_400_sin_llamar_a_core(client, core):
    r = client.post(f"{BASE}/emision", json=EMISION, headers=AUTH)
    assert r.status_code == 400
    assert r.json()["error_code"] == "ERR-TAR-HEADER-REQUERIDO"
    assert core.llamadas == []


def test_emision_con_llave_que_no_es_uuid4_400(client, core):
    r = client.post(f"{BASE}/emision", json=EMISION, headers={**AUTH, "X-Idempotency-Key": "abc"})
    assert r.json()["error_code"] == "ERR-TAR-HEADER-INVALIDO"
    assert core.llamadas == []


def test_el_id_de_la_tarjeta_sale_de_la_llave(client, core):
    core.respuesta = httpx.Response(201, json=TARJETA_CORE)
    client.post(f"{BASE}/emision", json=EMISION, headers=HEADERS_EMISION)
    otra = "6fa459ea-ee8a-4ca4-894e-db77e160355e"
    client.post(f"{BASE}/emision", json=EMISION, headers={**AUTH, "X-Idempotency-Key": otra})
    primera, segunda = (c["json"]["id_tarjeta"] for c in core.llamadas)
    assert primera == svc.id_de_emision(KEY) != segunda == svc.id_de_emision(otra)
    assert svc.id_de_emision(KEY) == svc.id_de_emision(KEY)


def test_emision_repetida_devuelve_la_tarjeta_original(client, core):
    core.respuesta = [error_core(409, "REGISTRO_DUPLICADO"), httpx.Response(200, json=TARJETA_CORE)]
    r = client.post(f"{BASE}/emision", json=EMISION, headers=HEADERS_EMISION)
    assert r.status_code == 201
    assert r.json()["message"].startswith("Emision ya procesada antes")
    assert r.json()["data"]["id_tarjeta"] == ID
    emision, lectura = core.llamadas
    assert (emision["metodo"], lectura["metodo"]) == ("POST", "GET")
    assert lectura["ruta"] == f"/coredb/tarjetas/{svc.id_de_emision(KEY)}"


def test_la_misma_llave_con_otros_datos_409(client, core):
    otra = {**TARJETA_CORE, "cod_cliente": "CLI000000002"}
    core.respuesta = [error_core(409, "REGISTRO_DUPLICADO"), httpx.Response(200, json=otra)]
    r = client.post(f"{BASE}/emision", json=EMISION, headers=HEADERS_EMISION)
    assert r.status_code == 409
    assert r.json()["error_code"] == "ERR-TAR-IDEMPOTENCIA"


def test_emision_cuenta_de_otro_titular(client, core):
    core.respuesta = error_core(422, "ERR-TAR-001", "no se emite tarjeta al cliente")
    r = client.post(f"{BASE}/emision", json=EMISION, headers=HEADERS_EMISION)
    assert r.status_code == 400
    assert r.json()["error_code"] == "ERR-TAR-001"


def test_emision_sobre_cuenta_ajena_400(client, core):
    core.respuesta = error_core(422, "BNA-TARJETA", "BNA-TARJETA: el cliente no es titular de la cuenta")
    r = client.post(f"{BASE}/emision", json=EMISION, headers=HEADERS_EMISION)
    assert r.status_code == 400
    assert r.json()["error_code"] == "ERR-TAR-CUENTA-INVALIDA"
    assert "no es titular" in r.json()["message"]


def test_bloqueo_envia_estado_y_motivo(client, core):
    core.respuesta = httpx.Response(200, json={**TARJETA_CORE, "estado_tarjeta": "BLOQUEADA"})
    r = client.post(f"{BASE}/{ID}/bloqueo", json={"motivo": "Robo reportado"}, headers=AUTH)
    assert r.status_code == 200
    assert r.json()["message"] == "Tarjeta bloqueada"
    llamada = core.llamadas[0]
    assert llamada["ruta"] == f"/coredb/tarjetas/{ID}/estado"
    assert llamada["json"] == {"estado": "BLOQUEADA", "motivo": "Robo reportado"}


def test_bloqueo_exige_motivo(client, core):
    r = client.post(f"{BASE}/{ID}/bloqueo", json={}, headers=AUTH)
    assert r.status_code == 400
    assert core.llamadas == []


def test_cambio_de_estado_sin_motivo(client, core):
    core.respuesta = httpx.Response(200, json={**TARJETA_CORE, "estado_tarjeta": "CANCELADA"})
    r = client.post(f"{BASE}/{ID}/estado", json={"estado": "ANULADA"}, headers=AUTH)
    assert r.json()["message"] == "Tarjeta en estado CANCELADA"
    assert core.llamadas[0]["json"] == {"estado": "ANULADA"}


def test_estado_desconocido_400(client, core):
    r = client.post(f"{BASE}/{ID}/estado", json={"estado": "EMBARGO"}, headers=AUTH)
    assert r.status_code == 400
    assert core.llamadas == []


def test_desbloqueo_rechazado_403(client, core):
    core.respuesta = error_core(403, "BNA-DESBLOQUEO", "pendiente de un cliente de Seguridad")
    r = client.post(f"{BASE}/{ID}/estado", json={"estado": "ACTIVA"}, headers=AUTH)
    assert r.status_code == 403
    assert r.json()["error_code"] == "ERR-TAR-DESBLOQUEO-NO-PERMITIDO"


def test_permiso_denegado_403(client, core):
    core.respuesta = error_core(403, "PERMISO_DENEGADO")
    r = client.get(f"{BASE}/cliente/CLI000000001", headers=AUTH)
    assert r.json()["error_code"] == "ERR-TAR-PERMISO-DENEGADO"


def test_core_caido_503(client, core):
    core.excepcion = httpx.ConnectError("sin conexion")
    r = client.get(f"{BASE}/{ID}", headers=AUTH)
    assert r.status_code == 503
    assert r.json()["error_code"] == "ERR-COR-NO-DISPONIBLE"


def test_core_lento_504(client, core):
    core.excepcion = httpx.ReadTimeout("lento")
    r = client.get(f"{BASE}/{ID}", headers=AUTH)
    assert r.status_code == 504


def test_correlacion_que_no_es_uuid_se_reemplaza(client, core):
    core.respuesta = httpx.Response(200, json=TARJETA_CORE)
    client.get(f"{BASE}/{ID}", headers={"X-Correlation-ID": "no-uuid", **AUTH})
    enviado = core.llamadas[0]["headers"]["x-correlation-id"]
    assert enviado != "no-uuid" and len(enviado) == 36


def test_log_en_json_con_el_modulo(client, core, caplog):
    core.respuesta = httpx.Response(200, json=TARJETA_CORE)
    with caplog.at_level(logging.INFO, logger="BNA_SERVICE_LOGGER"):
        client.get(f"{BASE}/{ID}", headers=AUTH)
    registro = json.loads(caplog.records[-1].getMessage())
    assert registro["modulo"] == "TARJETAS"
    assert registro["endpoint"] == f"GET {BASE}/{ID}"
    assert TOKEN not in caplog.text
