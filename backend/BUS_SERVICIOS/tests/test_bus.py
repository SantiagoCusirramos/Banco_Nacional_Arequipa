"""Pruebas del Bus de Servicios: reenvía sin tocar, no reintenta y falla claro.

Los módulos se simulan con httpx.MockTransport (se ve exactamente lo que les llega)
y, para la caída y el tiempo de espera, con sockets reales en 127.0.0.1.
"""

import gzip
import os
import socket
import subprocess
import sys
import threading
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from BUS_SERVICIOS.config import MODULOS, ConfiguracionInvalida, cargar
from BUS_SERVICIOS.proxy import crear_app

TOKEN_FRONTEND = "f" * 48
TOKEN_PRUEBAS = "p" * 48


def entorno(**cambios):
    valores = {f"BUS_URL_{m}": f"http://{m.lower()}.interno:9000" for m in MODULOS}
    valores.update({
        "BUS_CONSUMIDORES": "FRONTEND,PRUEBAS",
        "BUS_TOKEN_FRONTEND": TOKEN_FRONTEND,
        "BUS_TOKEN_PRUEBAS": TOKEN_PRUEBAS,
    })
    valores.update(cambios)
    return {k: v for k, v in valores.items() if v is not None}


class Modulo:
    """Módulo simulado: guarda cada petición que recibe y responde lo que se le pida."""

    def __init__(self, *respuestas):
        self.recibidas = []
        self.respuestas = list(respuestas) or [httpx.Response(200, json={"ok": True})]

    def __call__(self, peticion):
        peticion.read()
        self.recibidas.append(peticion)
        return self.respuestas.pop(0) if len(self.respuestas) > 1 else self.respuestas[0]


def cliente(modulo, **cambios):
    app = crear_app(cargar(entorno(**cambios)), transport=httpx.MockTransport(modulo))
    return TestClient(app, raise_server_exceptions=True)


AUT = {"X-Bus-Token": TOKEN_PRUEBAS}


# ── Configuración: sin claves por omisión ────────────────────────────────

def test_carga_una_ruta_por_modulo_incluido_coredb():
    config = cargar(entorno())
    assert set(config.modulos) == set(MODULOS)
    assert "COREDB" in config.modulos
    assert set(config.consumidores.values()) == {"FRONTEND", "PRUEBAS"}


@pytest.mark.parametrize("variable", [f"BUS_URL_{m}" for m in MODULOS]
                         + ["BUS_CONSUMIDORES", "BUS_TOKEN_FRONTEND", "BUS_TOKEN_PRUEBAS"])
def test_sin_una_variable_no_arranca(variable):
    with pytest.raises(ConfiguracionInvalida) as error:
        cargar(entorno(**{variable: None}))
    assert variable in str(error.value)


@pytest.mark.parametrize("cambios", [
    {"BUS_TOKEN_FRONTEND": "corto"},
    {"BUS_TOKEN_FRONTEND": TOKEN_PRUEBAS},
    {"BUS_TOKEN_FRONTEND": "f" * 40 + " " + "f" * 7},
    {"BUS_CONSUMIDORES": ""},
    {"BUS_CONSUMIDORES": "front-end"},
    {"BUS_URL_COREDB": "ftp://coredb:8012"},
    {"BUS_URL_COREDB": "http://usuario:clave@coredb:8012"},
    {"BUS_URL_COREDB": "http://coredb:8012?x=1"},
    {"BUS_URL_COREDB": "coredb:8012"},
    {"BUS_TIMEOUT_SEG": "0"},
    {"BUS_TIMEOUT_SEG": "nada"},
])
def test_rechaza_configuracion_invalida(cambios):
    with pytest.raises(ConfiguracionInvalida):
        cargar(entorno(**cambios))


def test_el_servicio_no_arranca_sin_configuracion():
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    limpio = {k: v for k, v in os.environ.items() if not k.startswith("BUS_")}
    resultado = subprocess.run([sys.executable, "-c", "import BUS_SERVICIOS.main"],
                               cwd=raiz, env=limpio, capture_output=True, text=True, timeout=60)
    assert resultado.returncode != 0
    assert "BUS_URL_COREDB" in resultado.stderr
    assert "BUS_CONSUMIDORES" in resultado.stderr


# ── Credencial del consumidor ────────────────────────────────────────────

def test_salud_sin_credencial():
    modulo = Modulo()
    with cliente(modulo) as c:
        respuesta = c.get("/salud")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "operativo"
    assert modulo.recibidas == []


@pytest.mark.parametrize("cabeceras", [{}, {"X-Bus-Token": "x" * 48}, {"X-Bus-Token": ""}])
def test_sin_credencial_valida_responde_401_y_no_reenvia(cabeceras):
    modulo = Modulo()
    with cliente(modulo) as c:
        respuesta = c.get("/bus/coredb/coredb/salud", headers=cabeceras)
    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "BUS_CREDENCIAL_INVALIDA"
    assert modulo.recibidas == []


def test_modulo_desconocido_404_sin_reenviar():
    modulo = Modulo()
    with cliente(modulo) as c:
        respuesta = c.get("/bus/clientes/registrar", headers=AUT)
    assert respuesta.status_code == 404
    assert modulo.recibidas == []


@pytest.mark.parametrize("modulo_nombre", MODULOS)
def test_cada_modulo_va_a_su_direccion(modulo_nombre):
    modulo = Modulo()
    with cliente(modulo) as c:
        respuesta = c.get(f"/bus/{modulo_nombre.lower()}/ruta/de/prueba", headers=AUT)
    assert respuesta.status_code == 200
    assert str(modulo.recibidas[0].url) == f"http://{modulo_nombre.lower()}.interno:9000/ruta/de/prueba"


def test_respeta_el_prefijo_de_la_direccion_del_modulo():
    modulo = Modulo()
    with cliente(modulo, BUS_URL_CUENTAS="http://cuentas:8001/base/") as c:
        c.get("/bus/cuentas/api/v1/cuentas/123", headers=AUT)
    assert str(modulo.recibidas[0].url) == "http://cuentas:8001/base/api/v1/cuentas/123"


# ── Reenvía sin tocar ────────────────────────────────────────────────────

CABECERAS = {
    "Authorization": "Bearer jwt.de.prueba",
    "X-Idempotency-Key": "123e4567-e89b-42d3-a456-426614174000",
    "X-Correlation-ID": "flujo-e2e-0001",
    "X-Channel-ID": "HB",
    "X-Request-Timestamp": "2026-11-16T21:00:00-05:00",
    "Cookie": "bna_sol_session=abc",
    "Content-Type": "application/json; charset=utf-8",
    "Accept": "application/json",
}


@pytest.mark.parametrize("metodo", ["GET", "POST", "PUT", "PATCH", "DELETE"])
def test_cabeceras_cuerpo_y_metodo_llegan_iguales(metodo):
    modulo = Modulo()
    cuerpo = b'{"monto": "100.00", "nota": "\xc3\xb1and\xc3\xba"}'
    with cliente(modulo) as c:
        c.request(metodo, "/bus/cuentas/api/v1/cuentas/deposito",
                  headers={**CABECERAS, **AUT}, content=None if metodo == "GET" else cuerpo)
    recibida = modulo.recibidas[0]
    assert recibida.method == metodo
    for nombre, valor in CABECERAS.items():
        assert recibida.headers[nombre] == valor
    assert recibida.content == (b"" if metodo == "GET" else cuerpo)


def test_no_reenvia_su_credencial_ni_agrega_cabeceras():
    modulo = Modulo()
    with cliente(modulo) as c:
        c.get("/bus/coredb/coredb/salud", headers={**AUT, "Accept": "*/*"})
    recibida = modulo.recibidas[0]
    assert "x-bus-token" not in recibida.headers
    # Ni una correlación inventada ni las cabeceras por omisión de httpx.
    assert "x-correlation-id" not in recibida.headers
    assert "python-httpx" not in recibida.headers.get("user-agent", "")
    nombres = {n.lower() for n in recibida.headers}
    permitidas = {"host", "accept", "accept-encoding", "connection", "user-agent", "content-length"}
    assert nombres <= permitidas, nombres - permitidas


def test_ruta_y_consulta_crudas():
    modulo = Modulo()
    with cliente(modulo) as c:
        c.get("/bus/sol/gateway/sol/clientes/A%2FB?search=caf%C3%A9&a=1&a=2&vacio=", headers=AUT)
    url = modulo.recibidas[0].url
    assert url.raw_path == b"/gateway/sol/clientes/A%2FB?search=caf%C3%A9&a=1&a=2&vacio="


def test_cabeceras_de_respuesta_iguales_y_set_cookie_repetida():
    modulo = Modulo(httpx.Response(
        200, content=b'{"ok":true}',
        headers=[("Content-Type", "application/json"), ("X-Correlation-ID", "del-modulo"),
                 ("Set-Cookie", "a=1; HttpOnly"), ("Set-Cookie", "b=2; HttpOnly"),
                 ("Cache-Control", "no-store"), ("Idempotent-Replayed", "true")]))
    with cliente(modulo) as c:
        respuesta = c.get("/bus/sol/gateway/sol/auth/me", headers=AUT)
    assert respuesta.headers["x-correlation-id"] == "del-modulo"
    assert respuesta.headers.get_list("set-cookie") == ["a=1; HttpOnly", "b=2; HttpOnly"]
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.headers["idempotent-replayed"] == "true"
    assert respuesta.headers["content-type"] == "application/json"
    assert respuesta.content == b'{"ok":true}'


def test_no_sigue_redirecciones():
    modulo = Modulo(httpx.Response(307, headers={"Location": "http://otro:1/x"}))
    with cliente(modulo) as c:
        respuesta = c.get("/bus/coredb/docs", headers=AUT, follow_redirects=False)
    assert respuesta.status_code == 307
    assert respuesta.headers["location"] == "http://otro:1/x"
    assert len(modulo.recibidas) == 1


def test_cuerpo_comprimido_pasa_tal_cual():
    original = b'{"datos": "' + b"x" * 2000 + b'"}'
    comprimido = gzip.compress(original)
    modulo = Modulo(httpx.Response(200, content=comprimido,
                                   headers={"Content-Encoding": "gzip", "Content-Type": "application/json"}))
    with cliente(modulo) as c:
        respuesta = c.get("/bus/coredb/x", headers={**AUT, "Accept-Encoding": "gzip"})
    assert respuesta.headers["content-encoding"] == "gzip"
    assert respuesta.content == original  # el cliente de prueba descomprime lo que recibió


# ── Errores con su código original ───────────────────────────────────────

@pytest.mark.parametrize("estado", [400, 401, 403, 404, 409, 422, 429, 500, 502, 503])
def test_errores_del_modulo_con_su_codigo_y_cuerpo(estado):
    cuerpo = b'{"detail": "mensaje del modulo", "codigo": "X"}'
    modulo = Modulo(httpx.Response(estado, content=cuerpo, headers={"Content-Type": "application/json"}))
    with cliente(modulo) as c:
        respuesta = c.post("/bus/desembolso/api/v1/ordenes", headers={**AUT, "X-Idempotency-Key": "k1"},
                           content=b"{}")
    assert respuesta.status_code == estado
    assert respuesta.content == cuerpo
    assert len(modulo.recibidas) == 1  # nunca reintenta


def test_cuerpo_que_no_es_json_pasa_igual():
    modulo = Modulo(httpx.Response(500, content=b"Internal Server Error",
                                   headers={"Content-Type": "text/plain; charset=utf-8"}))
    with cliente(modulo) as c:
        respuesta = c.get("/bus/tarjetas/x", headers=AUT)
    assert respuesta.status_code == 500
    assert respuesta.text == "Internal Server Error"
    assert respuesta.headers["content-type"] == "text/plain; charset=utf-8"


# ── Idempotencia ─────────────────────────────────────────────────────────

def test_repeticion_idempotente_llega_igual_y_la_respuesta_del_modulo_no_cambia():
    primera = httpx.Response(201, json={"uuid_transaccion": "t-1", "repetida": False})
    segunda = httpx.Response(200, json={"uuid_transaccion": "t-1", "repetida": True},
                             headers={"Idempotent-Replayed": "true"})
    modulo = Modulo(primera, segunda)
    cabeceras = {**AUT, "Authorization": "Bearer t", "X-Idempotency-Key": "op-123"}
    cuerpo = b'{"num_cuenta": "001", "monto": "10.00"}'
    with cliente(modulo) as c:
        r1 = c.post("/bus/coredb/coredb/cuentas/deposito", headers=cabeceras, content=cuerpo)
        r2 = c.post("/bus/coredb/coredb/cuentas/deposito", headers=cabeceras, content=cuerpo)
    assert (r1.status_code, r1.json()) == (201, {"uuid_transaccion": "t-1", "repetida": False})
    assert (r2.status_code, r2.json()) == (200, {"uuid_transaccion": "t-1", "repetida": True})
    assert r2.headers["idempotent-replayed"] == "true"
    assert len(modulo.recibidas) == 2
    assert [p.headers["x-idempotency-key"] for p in modulo.recibidas] == ["op-123", "op-123"]
    assert [p.content for p in modulo.recibidas] == [cuerpo, cuerpo]


# ── Módulo caído o colgado: error claro, sin colgar, sin reintentar ──────

def puerto_cerrado():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    puerto = s.getsockname()[1]
    s.close()
    return puerto


def test_modulo_caido_responde_503_claro():
    url = f"http://127.0.0.1:{puerto_cerrado()}"
    app = crear_app(cargar(entorno(BUS_URL_CUENTAS=url)))
    inicio = time.monotonic()
    with TestClient(app) as c:
        respuesta = c.post("/bus/cuentas/api/v1/cuentas/deposito",
                           headers={**AUT, "X-Correlation-ID": "c-1"}, content=b"{}")
    assert time.monotonic() - inicio < 5
    assert respuesta.status_code == 503
    assert respuesta.json()["codigo"] == "MODULO_NO_DISPONIBLE"
    assert respuesta.json()["modulo"] == "CUENTAS"
    assert "CUENTAS" in respuesta.json()["detail"]
    assert respuesta.headers["x-correlation-id"] == "c-1"


class Colgado:
    """Acepta conexiones y nunca responde. Cuenta cuántas recibió."""

    def __init__(self):
        self.servidor = socket.socket()
        self.servidor.bind(("127.0.0.1", 0))
        self.servidor.listen()
        self.conexiones = []
        threading.Thread(target=self._aceptar, daemon=True).start()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.servidor.getsockname()[1]}"

    def _aceptar(self):
        while True:
            try:
                conexion, _ = self.servidor.accept()
            except OSError:
                return
            self.conexiones.append(conexion)

    def cerrar(self):
        for conexion in self.conexiones:
            conexion.close()
        self.servidor.close()


def test_modulo_colgado_responde_504_sin_colgar_ni_reintentar():
    colgado = Colgado()
    try:
        app = crear_app(cargar(entorno(BUS_URL_DESEMBOLSO=colgado.url, BUS_TIMEOUT_SEG="0.5")))
        inicio = time.monotonic()
        with TestClient(app) as c:
            respuesta = c.post("/bus/desembolso/api/v1/confirmaciones",
                               headers={**AUT, "X-Idempotency-Key": "op-9"}, content=b"{}")
        assert time.monotonic() - inicio < 5
        assert respuesta.status_code == 504
        assert respuesta.json()["codigo"] == "MODULO_SIN_RESPUESTA"
        assert respuesta.json()["modulo"] == "DESEMBOLSO"
        assert len(colgado.conexiones) == 1
    finally:
        colgado.cerrar()


# ── Métricas: qué consumidor pasó por qué módulo ─────────────────────────

def test_metricas_por_consumidor_y_modulo():
    modulo = Modulo()
    with cliente(modulo) as c:
        c.get("/bus/coredb/a", headers={"X-Bus-Token": TOKEN_FRONTEND})
        c.get("/bus/coredb/b", headers={"X-Bus-Token": TOKEN_FRONTEND})
        c.get("/bus/cuentas/c", headers=AUT)
        assert c.get("/metricas").status_code == 401
        metricas = c.get("/metricas", headers=AUT).json()
    assert metricas["reenvios"]["FRONTEND"] == {"COREDB": 2}
    assert metricas["reenvios"]["PRUEBAS"] == {"CUENTAS": 1}
