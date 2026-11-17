import hashlib
import logging

import httpx

from TARJETAS.services import tarjetas as svc

BASE = "/api/v1/tarjetas"
ID = "7e570001-0000-4000-8000-000000000001"
AUT = "5a1f0c3e-0000-4000-8000-000000000001"
AUTH = {"Authorization": "Bearer token-de-prueba"}
KEY = "550e8400-e29b-41d4-a716-446655440000"
HEADERS = {"X-Idempotency-Key": KEY, **AUTH}
RETIRO = {"num_cuenta": "10100000000001", "monto": "150.00", "id_terminal": "DEV-ATM-01"}


def _huella(valor: str) -> str:
    return hashlib.sha256(valor.encode()).hexdigest()


def autorizacion_core(estado="AUTORIZADA", codigo="00", motivo=None):
    return {
        "uuid_autorizacion": AUT, "id_tarjeta": ID, "num_cuenta": "10100000000001", "id_canal": None,
        "id_terminal": "DEV-ATM-01", "tipo_operacion": "RETIRO", "monto": "150.00",
        "estado_autorizacion": estado, "codigo_respuesta": codigo, "motivo_rechazo": motivo,
        "uuid_transaccion": None, "fecha_hora": "2026-11-15T10:00:00Z",
        "fecha_actualizacion": "2026-11-15T10:00:00Z",
    }


def error_core(status, code, message="mensaje de core"):
    return httpx.Response(status, json={"error": {"code": code, "message": message}})


def test_autorizar_envia_el_uuid_de_la_llave(client, core):
    core.respuesta = httpx.Response(201, json=autorizacion_core())
    r = client.post(f"{BASE}/{ID}/autorizaciones", json=RETIRO, headers=HEADERS)
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["message"] == "Operación autorizada"
    assert cuerpo["data"]["aprobada"] is True
    assert cuerpo["data"]["codigo_respuesta"] == "00"
    assert cuerpo["data"]["uuid_transaccion"] is None
    llamada = core.llamadas[0]
    assert (llamada["metodo"], llamada["ruta"]) == ("POST", "/coredb/autorizaciones")
    assert llamada["json"] == {
        "uuid_autorizacion": svc.id_de_autorizacion(KEY), "id_tarjeta": ID, "num_cuenta": "10100000000001",
        "tipo_operacion": "RETIRO", "monto": "150.00", "id_terminal": "DEV-ATM-01",
    }


def test_la_misma_llave_da_el_mismo_uuid_y_distinto_al_de_la_emision():
    assert svc.id_de_autorizacion(KEY) == svc.id_de_autorizacion(KEY)
    assert svc.id_de_autorizacion(KEY) != svc.id_de_emision(KEY)


def test_un_rechazo_responde_201_con_su_codigo(client, core):
    core.respuesta = httpx.Response(201, json=autorizacion_core("RECHAZADA", "51", "BNA-SALDO: saldo disponible insuficiente"))
    r = client.post(f"{BASE}/{ID}/autorizaciones", json=RETIRO, headers=HEADERS)
    assert r.status_code == 201
    assert r.json()["message"] == "Operación rechazada (código 51)"
    assert r.json()["data"]["aprobada"] is False


def test_autorizar_sin_llave_400_sin_llamar_a_core(client, core):
    r = client.post(f"{BASE}/{ID}/autorizaciones", json=RETIRO, headers=AUTH)
    assert r.status_code == 400
    assert r.json()["error_code"] == "ERR-TAR-HEADER-REQUERIDO"
    assert core.llamadas == []


def test_canal_y_terminal_a_la_vez_400(client, core):
    r = client.post(f"{BASE}/{ID}/autorizaciones", json={**RETIRO, "id_canal": "ATM"}, headers=HEADERS)
    assert r.status_code == 400
    assert core.llamadas == []


def test_una_operacion_de_credito_no_se_autoriza(client, core):
    r = client.post(f"{BASE}/{ID}/autorizaciones", json={**RETIRO, "tipo_operacion": "DEPOSITO"}, headers=HEADERS)
    assert r.status_code == 400
    assert core.llamadas == []


def test_la_llave_con_otros_datos_409(client, core):
    core.respuesta = error_core(409, "BNA-IDEMPOTENCIA")
    r = client.post(f"{BASE}/{ID}/autorizaciones", json=RETIRO, headers=HEADERS)
    assert r.status_code == 409
    assert r.json()["error_code"] == "ERR-TAR-IDEMPOTENCIA"


def test_una_cuenta_que_la_tarjeta_no_opera_400(client, core):
    core.respuesta = error_core(422, "BNA-TARJETA")
    r = client.post(f"{BASE}/{ID}/autorizaciones", json=RETIRO, headers=HEADERS)
    assert (r.status_code, r.json()["error_code"]) == (400, "ERR-TAR-CUENTA-INVALIDA")


def test_extornar(client, core):
    core.respuesta = httpx.Response(200, json=autorizacion_core("EXTORNADA", "EXT"))
    r = client.post(f"{BASE}/autorizaciones/{AUT}/extorno", json={"motivo": "Cajero sin efectivo"}, headers=AUTH)
    assert r.status_code == 200
    assert r.json()["message"] == "Operación extornada"
    assert core.llamadas[0]["ruta"] == f"/coredb/autorizaciones/{AUT}/extorno"
    assert core.llamadas[0]["json"] == {"motivo": "Cajero sin efectivo"}


def test_extornar_una_ya_contabilizada_409(client, core):
    core.respuesta = error_core(409, "BNA-EXTORNO")
    r = client.post(f"{BASE}/autorizaciones/{AUT}/extorno", json={"motivo": "xyz"}, headers=AUTH)
    assert (r.status_code, r.json()["error_code"]) == (409, "ERR-TAR-EXTORNO-NO-PERMITIDO")


def test_extornar_una_que_no_existe_404(client, core):
    core.respuesta = error_core(404, "BNA-AUTORIZACION")
    r = client.post(f"{BASE}/autorizaciones/{AUT}/extorno", json={"motivo": "xyz"}, headers=AUTH)
    assert (r.status_code, r.json()["error_code"]) == (404, "ERR-TAR-AUTORIZACION-NO-ENCONTRADA")


def test_ver_autorizacion(client, core):
    core.respuesta = httpx.Response(200, json=autorizacion_core())
    r = client.get(f"{BASE}/autorizaciones/{AUT}", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["data"]["uuid_autorizacion"] == AUT


def test_un_id_de_autorizacion_invalido_400_sin_llamar_a_core(client, core):
    r = client.get(f"{BASE}/autorizaciones/no-es-uuid", headers=AUTH)
    assert (r.status_code, r.json()["error_code"]) == (400, "ERR-TAR-ID-INVALIDO")
    assert core.llamadas == []


def test_registrar_un_pin(client, core):
    core.respuesta = httpx.Response(204)
    r = client.put(f"{BASE}/{ID}/credenciales/PIN_ATM", json={"valor": "4821"}, headers=AUTH)
    assert r.status_code == 200
    assert r.json()["message"] == "Clave registrada"
    assert (core.llamadas[0]["metodo"], core.llamadas[0]["ruta"]) == ("PUT", f"/coredb/tarjetas/{ID}/credenciales/PIN_ATM")
    assert core.llamadas[0]["json"] == {"valor": "4821"}


def test_validar_un_pin_equivocado(client, core):
    core.respuesta = httpx.Response(200, json={"resultado": "FALLIDO", "intentos_restantes": 2})
    r = client.post(f"{BASE}/{ID}/credenciales/PIN_ATM/validacion",
                    json={"valor": "0000", "id_terminal": "DEV-ATM-01"}, headers=AUTH)
    assert r.status_code == 200
    assert r.json()["message"] == "Clave incorrecta"
    assert r.json()["data"] == {"resultado": "FALLIDO", "intentos_restantes": 2}
    enviado = core.llamadas[0]["json"]
    assert (enviado["valor"], enviado["id_terminal"]) == ("0000", "DEV-ATM-01")


def test_una_clave_con_letras_400_sin_repetirla_ni_llamar_a_core(client, core, caplog):
    caplog.set_level(logging.DEBUG)
    r = client.put(f"{BASE}/{ID}/credenciales/PIN_ATM", json={"valor": "48a1"}, headers=AUTH)
    assert r.status_code == 400
    assert "48a1" not in r.text
    assert "48a1" not in caplog.text
    assert core.llamadas == []


def test_un_tipo_de_credencial_desconocido_400(client, core):
    r = client.put(f"{BASE}/{ID}/credenciales/TOKEN_MATRIZ", json={"valor": "1234"}, headers=AUTH)
    assert r.status_code == 400
    assert core.llamadas == []


def test_una_clave_de_otra_longitud_que_rechaza_core(client, core):
    core.respuesta = error_core(422, "BNA-CREDENCIAL", "BNA-CREDENCIAL: PIN_ATM debe tener 4 dígitos")
    r = client.put(f"{BASE}/{ID}/credenciales/PIN_ATM", json={"valor": "48219"}, headers=AUTH)
    assert (r.status_code, r.json()["error_code"]) == (400, "ERR-TAR-CREDENCIAL-INVALIDA")


def test_validar_con_la_tarjeta_bloqueada_400(client, core):
    core.respuesta = error_core(422, "ERR-TAR-003", "ERR-TAR-003: la tarjeta no es operativa (estado BLOQUEADA)")
    r = client.post(f"{BASE}/{ID}/credenciales/PIN_ATM/validacion",
                    json={"valor": "4821", "id_canal": "ATM"}, headers=AUTH)
    assert (r.status_code, r.json()["error_code"]) == (400, "ERR-TAR-003")


def autorizacion_confirmada():
    base = autorizacion_core()
    base.update({
        "estado_autorizacion": "DISPENSADA",
        "uuid_transaccion": AUT,
    })
    return base


def test_confirmar_envia_llave_y_huella(client, core):
    core.respuesta = httpx.Response(200, json=autorizacion_confirmada())
    llave = "550e8400-e29b-41d4-a716-446655440001"
    r = client.post(f"{BASE}/autorizaciones/{AUT}/confirmacion", json={
        "llave_idempotencia": llave, "huella": _huella(llave), "id_terminal": "DEV-ATM-01"
    }, headers=AUTH)
    assert r.status_code == 200
    assert r.json()["message"] == "Operación confirmada"
    assert r.json()["data"]["estado_autorizacion"] == "DISPENSADA"
    assert r.json()["data"]["uuid_transaccion"] == AUT
    llamada = core.llamadas[0]
    assert (llamada["metodo"], llamada["ruta"]) == ("POST", f"/coredb/autorizaciones/{AUT}/confirmacion")
    assert llamada["json"] == {
        "llave_idempotencia": llave, "huella": _huella(llave), "id_terminal": "DEV-ATM-01",
    }


def test_confirmar_con_id_canal(client, core):
    core.respuesta = httpx.Response(200, json=autorizacion_confirmada())
    llave = "550e8400-e29b-41d4-a716-446655440002"
    r = client.post(f"{BASE}/autorizaciones/{AUT}/confirmacion", json={
        "llave_idempotencia": llave, "huella": _huella(llave), "id_canal": "ATM"
    }, headers=AUTH)
    assert r.status_code == 200
    llamada = core.llamadas[0]
    assert llamada["json"] == {
        "llave_idempotencia": llave, "huella": _huella(llave), "id_canal": "ATM",
    }


def test_confirmar_sin_llave_400_sin_llamar_a_core(client, core):
    r = client.post(f"{BASE}/autorizaciones/{AUT}/confirmacion", json={
        "huella": _huella("x"), "id_terminal": "DEV-ATM-01"
    }, headers=AUTH)
    assert r.status_code == 400
    assert r.json()["error_code"] == "ERR-VALIDACION-ESQUEMA"
    assert core.llamadas == []


def test_confirmar_sin_canal_ni_terminal_400_sin_llamar_a_core(client, core):
    llave = "550e8400-e29b-41d4-a716-446655440003"
    r = client.post(f"{BASE}/autorizaciones/{AUT}/confirmacion", json={
        "llave_idempotencia": llave, "huella": _huella(llave)
    }, headers=AUTH)
    assert r.status_code == 400
    assert r.json()["error_code"] == "ERR-VALIDACION-ESQUEMA"
    assert core.llamadas == []


def test_confirmar_huella_invalida_400_sin_llamar_a_core(client, core):
    llave = "550e8400-e29b-41d4-a716-446655440004"
    r = client.post(f"{BASE}/autorizaciones/{AUT}/confirmacion", json={
        "llave_idempotencia": llave, "huella": "no-es-hex", "id_terminal": "DEV-ATM-01"
    }, headers=AUTH)
    assert r.status_code == 400
    assert r.json()["error_code"] == "ERR-VALIDACION-ESQUEMA"
    assert core.llamadas == []


def test_confirmar_autorizacion_inexistente_404(client, core):
    core.respuesta = error_core(404, "BNA-AUTORIZACION")
    llave = "550e8400-e29b-41d4-a716-446655440005"
    r = client.post(f"{BASE}/autorizaciones/{AUT}/confirmacion", json={
        "llave_idempotencia": llave, "huella": _huella(llave), "id_terminal": "DEV-ATM-01"
    }, headers=AUTH)
    assert (r.status_code, r.json()["error_code"]) == (404, "ERR-TAR-AUTORIZACION-NO-ENCONTRADA")


def test_confirmar_ya_dispensada_409(client, core):
    core.respuesta = error_core(409, "BNA-CONFIRMACION", "BNA-CONFIRMACION: la autorización no está en estado vigente")
    llave = "550e8400-e29b-41d4-a716-446655440006"
    r = client.post(f"{BASE}/autorizaciones/{AUT}/confirmacion", json={
        "llave_idempotencia": llave, "huella": _huella(llave), "id_terminal": "DEV-ATM-01"
    }, headers=AUTH)
    assert (r.status_code, r.json()["error_code"]) == (409, "ERR-TAR-CONFIRMACION-NO-PERMITIDA")


def test_confirmar_extornada_409(client, core):
    core.respuesta = error_core(409, "BNA-CONFIRMACION", "BNA-CONFIRMACION: la autorización no está en estado vigente")
    llave = "550e8400-e29b-41d4-a716-446655440007"
    r = client.post(f"{BASE}/autorizaciones/{AUT}/confirmacion", json={
        "llave_idempotencia": llave, "huella": _huella(llave), "id_terminal": "DEV-ATM-01"
    }, headers=AUTH)
    assert (r.status_code, r.json()["error_code"]) == (409, "ERR-TAR-CONFIRMACION-NO-PERMITIDA")


def test_confirmar_canal_no_coincide_409(client, core):
    core.respuesta = error_core(409, "BNA-CONFIRMACION", "BNA-CONFIRMACION: el canal no coincide con la autorización")
    llave = "550e8400-e29b-41d4-a716-446655440008"
    r = client.post(f"{BASE}/autorizaciones/{AUT}/confirmacion", json={
        "llave_idempotencia": llave, "huella": _huella(llave), "id_canal": "VEN"
    }, headers=AUTH)
    assert (r.status_code, r.json()["error_code"]) == (409, "ERR-TAR-CONFIRMACION-NO-PERMITIDA")


def test_confirmar_terminal_no_coincide_409(client, core):
    core.respuesta = error_core(409, "BNA-CONFIRMACION", "BNA-CONFIRMACION: la terminal no coincide con la autorización")
    llave = "550e8400-e29b-41d4-a716-446655440009"
    r = client.post(f"{BASE}/autorizaciones/{AUT}/confirmacion", json={
        "llave_idempotencia": llave, "huella": _huella(llave), "id_terminal": "OTRA-TERMINAL"
    }, headers=AUTH)
    assert (r.status_code, r.json()["error_code"]) == (409, "ERR-TAR-CONFIRMACION-NO-PERMITIDA")


def test_confirmar_idempotencia_conflicto_409(client, core):
    core.respuesta = error_core(409, "BNA-IDEMPOTENCIA", "BNA-IDEMPOTENCIA: la llave se usó en otra operación")
    llave = "550e8400-e29b-41d4-a716-446655440010"
    r = client.post(f"{BASE}/autorizaciones/{AUT}/confirmacion", json={
        "llave_idempotencia": llave, "huella": _huella(llave), "id_terminal": "DEV-ATM-01"
    }, headers=AUTH)
    assert (r.status_code, r.json()["error_code"]) == (409, "ERR-TAR-IDEMPOTENCIA")


def test_un_id_de_autorizacion_invalido_en_confirmacion_400_sin_llamar_a_core(client, core):
    llave = "550e8400-e29b-41d4-a716-446655440011"
    r = client.post(f"{BASE}/autorizaciones/no-es-uuid/confirmacion", json={
        "llave_idempotencia": llave, "huella": _huella(llave), "id_terminal": "DEV-ATM-01"
    }, headers=AUTH)
    assert (r.status_code, r.json()["error_code"]) == (400, "ERR-TAR-ID-INVALIDO")
    assert core.llamadas == []
