"""La pantalla del cajero se sirve sin abrir archivos fuera de static/ (K-1, S-1), un retiro
exige una sesión abierta con el PIN de esa tarjeta (K-3) y el registro del canal exige la
credencial del operador (P-3)."""

import time
from pathlib import Path

import httpx
import pytest

from ATM.tests.conftest import ID_TARJETA_PRUEBA as ID_TARJETA, UUID_AUT_PRUEBA as UUID_AUT

AUTH = {"Authorization": "Bearer token-de-prueba"}
KEY = {"X-Idempotency-Key": "550e8400-e29b-41d4-a716-446655440000"}
STATIC = Path(__file__).resolve().parents[1] / "static"
RETIRO = {"id_tarjeta": ID_TARJETA, "num_cuenta": "10100000000001", "moneda": "PEN", "monto": "50.00",
          "id_terminal": "ATM-AQP-001", "uuid_transaccion": "5a1f0c3e-0000-4000-8000-000000000002"}


# ── Pantalla y archivos estáticos ─────────────────────────────────────────

def test_la_pantalla_y_el_panel_tecnico_se_sirven(client):
    r = client.get("/")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    assert "Inserte su tarjeta" in r.text
    assert client.get("/tecnico.html").status_code == 200
    logo = client.get("/logo.png")
    assert logo.status_code == 200 and logo.headers["content-type"] == "image/png"


def test_la_api_y_la_salud_siguen_respondiendo(client):
    assert client.get("/health").json()["modulo"] == "atm"
    assert client.get("/api/config").status_code == 200


@pytest.mark.parametrize("ruta", [
    "/..%2Fconfig.py",
    "/%2e%2e/config.py",
    "/%2e%2e%2fconfig.py",
    "/fuentes/..%2F..%2Fconfig.py",
    "/..%2F..%2F..%2F..%2Fproc%2Fself%2Fenviron",
    "/..%2F..%2F..%2F..%2Fetc%2Fpasswd",
    "/api/static/..%2Fconfig.py",
    "/api/static/..%2F..%2F..%2Fproc%2Fself%2Fenviron",
    "/static/..%2Fconfig.py",
])
def test_ninguna_ruta_lee_fuera_de_static(client, ruta):
    r = client.get(ruta)
    assert r.status_code == 404, (ruta, r.status_code)
    assert "BaseSettings" not in r.text and "BUS_TOKEN" not in r.text and "root:" not in r.text


def test_la_pantalla_usa_el_id_real_la_sesion_y_el_token():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert "tok_" not in html                      # K-2: nada de ids inventados
    assert "token_sesion" in html and "X-ATM-Sesion" in html
    assert "Authorization" in html and "/api/apertura" in html
    tecnico = (STATIC / "tecnico.html").read_text(encoding="utf-8")
    assert "Authorization" in tecnico


# ── Sesión de la tarjeta: sin PIN no hay saldo ni retiro (K-3) ─────────────

def test_validar_pin_exitoso_abre_una_sesion_y_el_fallido_no(client, core):
    core.respuesta = httpx.Response(200, json={"resultado": "EXITOSO", "intentos_restantes": 3})
    pin = {"id_tarjeta": ID_TARJETA, "pin": "4821", "id_terminal": "ATM-AQP-001"}
    r = client.post("/api/validar-pin", json=pin, headers=AUTH)
    token = r.json()["data"]["token_sesion"]
    assert isinstance(token, str) and len(token) >= 32
    core.respuesta = httpx.Response(200, json={"resultado": "FALLIDO", "intentos_restantes": 2})
    r = client.post("/api/validar-pin", json={**pin, "pin": "0000"}, headers=AUTH)
    assert r.json()["data"]["token_sesion"] is None


@pytest.mark.parametrize("ruta,metodo,cuerpo", [
    ("/api/autorizar", "post", RETIRO),
    ("/api/saldo?id_tarjeta=" + ID_TARJETA, "get", None),
    ("/api/confirmar", "post", {"uuid_autorizacion": UUID_AUT, "id_terminal": "ATM-AQP-001", "resultado": "DISPENSADO"}),
    ("/api/extornar", "post", {"uuid_autorizacion": UUID_AUT, "motivo": "Cliente desiste"}),
    ("/api/movimientos?num_cuenta=10100000000001", "get", None),
])
def test_sin_sesion_de_pin_no_hay_operacion(client, core, ruta, metodo, cuerpo):
    # Un token del personal no basta: K-3.
    r = getattr(client, metodo)(ruta, **({"json": cuerpo} if cuerpo else {}), headers={**AUTH, **KEY})
    assert r.status_code == 401 and r.json()["error_code"] == "ERR-ATM-SESION-REQUERIDA"
    r = getattr(client, metodo)(ruta, **({"json": cuerpo} if cuerpo else {}),
                                headers={**AUTH, **KEY, "X-ATM-Sesion": "inventada" * 5})
    assert r.status_code == 401
    assert core.llamadas == []


def test_la_sesion_es_de_una_sola_tarjeta(client, core, sesion):
    otra = {**RETIRO, "id_tarjeta": "7e570001-0000-4000-8000-000000000999"}
    r = client.post("/api/autorizar", json=otra, headers={**AUTH, **KEY, **sesion})
    assert r.status_code == 403 and r.json()["error_code"] == "ERR-ATM-SESION-OTRA-TARJETA"
    r = client.get("/api/saldo", params={"id_tarjeta": otra["id_tarjeta"]}, headers={**AUTH, **sesion})
    assert r.status_code == 403
    assert core.llamadas == []


def test_solo_la_sesion_que_autorizo_confirma_o_extorna(client, core, sesion):
    confirmar = {"uuid_autorizacion": UUID_AUT, "id_terminal": "ATM-AQP-001", "resultado": "DISPENSADO"}
    r = client.post("/api/confirmar", json=confirmar, headers={**AUTH, **KEY, **sesion})
    assert r.status_code == 403 and r.json()["error_code"] == "ERR-ATM-AUTORIZACION-AJENA"
    r = client.post("/api/extornar", json={"uuid_autorizacion": UUID_AUT, "motivo": "Cliente desiste"},
                    headers={**AUTH, **sesion})
    assert r.status_code == 403
    assert core.llamadas == []


def test_la_sesion_vence(client, core, sesion, monkeypatch):
    from ATM import sesiones
    ahora = time.monotonic()
    monkeypatch.setattr(sesiones.time, "monotonic", lambda: ahora + sesiones.DURACION_S + 1)
    r = client.post("/api/autorizar", json=RETIRO, headers={**AUTH, **KEY, **sesion})
    assert r.status_code == 401 and r.json()["error_code"] == "ERR-ATM-SESION-REQUERIDA"
    assert core.llamadas == []


def test_retiro_con_sesion_autoriza_y_confirma(client, core, autorizada):
    core.respuesta = httpx.Response(200, json={
        "uuid_autorizacion": UUID_AUT, "id_tarjeta": ID_TARJETA, "num_cuenta": "10100000000001", "id_canal": None,
        "id_terminal": "ATM-AQP-001", "tipo_operacion": "RETIRO", "monto": "150.00",
        "estado_autorizacion": "DISPENSADA", "codigo_respuesta": "00", "motivo_rechazo": None})
    r = client.post("/api/confirmar", json={"uuid_autorizacion": UUID_AUT, "id_terminal": "ATM-AQP-001",
                                            "resultado": "DISPENSADO"}, headers={**AUTH, **KEY, **autorizada})
    assert r.status_code == 200 and r.json()["data"]["estado_autorizacion"] == "DISPENSADA"
    assert core.llamadas[0]["headers"]["authorization"] == "Bearer token-de-prueba"


def test_cerrar_la_sesion_la_invalida(client, core, sesion):
    assert client.post("/api/cerrar-sesion", headers=sesion).status_code == 200
    r = client.post("/api/autorizar", json=RETIRO, headers={**AUTH, **KEY, **sesion})
    assert r.status_code == 401


# ── Apertura del cajero y registro del canal (P-3) ─────────────────────────

def test_apertura_inicia_sesion_del_operador_en_coredb_por_el_bus(client, core):
    core.respuesta = httpx.Response(200, json={"access_token": "token-del-operador", "token_type": "bearer"})
    r = client.post("/api/apertura", json={"username": "cajero", "password": "clave-secreta"})
    assert r.status_code == 200 and r.json()["data"]["access_token"] == "token-del-operador"
    assert core.llamadas[0]["ruta"] == "/bus/coredb/coredb/auth/login"
    assert core.llamadas[0]["json"] == {"username": "cajero", "password": "clave-secreta"}


def test_apertura_con_credenciales_erradas_401(client, core):
    core.respuesta = httpx.Response(401, json={"error": {"code": "CREDENCIALES_INVALIDAS", "message": "No"}})
    r = client.post("/api/apertura", json={"username": "cajero", "password": "errada"})
    assert r.status_code == 401


def test_el_registro_del_canal_exige_al_operador(client, core):
    evento = {"tipo": "RETIRO", "estado": "OK", "correlationId": "c-1", "tarjeta": "0001"}
    assert client.get("/api/registro").status_code == 401
    assert client.post("/api/registrar", json=evento).status_code == 401
    assert core.llamadas == []
    core.respuesta = httpx.Response(401, json={"error": {"code": "TOKEN_INVALIDO", "message": "No"}})
    assert client.get("/api/registro", headers={"Authorization": "Bearer vencido"}).status_code == 401
    core.respuesta = httpx.Response(200, json={"username": "cajero", "rol": "CAJERO"})
    operador = {"Authorization": "Bearer token-del-operador"}
    assert client.post("/api/registrar", json=evento, headers=operador).status_code == 200
    r = client.get("/api/registro", headers=operador)
    assert r.status_code == 200 and r.json()[-1]["correlationId"] == "c-1"
    assert any(c["ruta"] == "/bus/coredb/coredb/auth/me" for c in core.llamadas)


def test_el_registro_no_guarda_el_id_completo_de_la_tarjeta(client, core):
    core.respuesta = httpx.Response(200, json={"username": "cajero", "rol": "CAJERO"})
    evento = {"tipo": "RETIRO", "estado": "OK", "correlationId": "c-2", "tarjeta": ID_TARJETA}
    r = client.post("/api/registrar", json=evento, headers={"Authorization": "Bearer token-del-operador"})
    assert r.status_code == 400


def test_la_pantalla_manda_la_llave_de_idempotencia_al_retirar():
    # /api/autorizar y /api/confirmar exigen X-Idempotency-Key (UUIDv4): sin ella, el retiro desde la
    # pantalla respondía 400 ERR-ATM-HEADER-REQUERIDO.
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert "apiPost('/api/autorizar', solicitud, 30000, {'X-Idempotency-Key': llaveAutorizar})" in html
    assert "apiPost('/api/confirmar', solicitud, 30000, {'X-Idempotency-Key': llaveConfirmar})" in html
    # Fuera de localhost (http) no hay crypto.randomUUID: la alternativa también es un UUIDv4.
    assert "Math.random" not in html and "crypto.getRandomValues" in html
    # La validación del monto lee el saldo con el nombre que devuelve /api/saldo.
    assert "saldoDisponible" not in html


def test_la_pantalla_no_muestra_el_id_completo_de_la_tarjeta():
    # El menú y el comprobante muestran solo los últimos 4 caracteres, como la pantalla de la clave.
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert "(tarjeta || '----')" not in html
