"""Pruebas del Bus de Servicios: reenvía sin tocar, no reintenta y falla claro.

Los módulos se simulan con httpx.MockTransport (se ve exactamente lo que les llega)
y, para la caída y el tiempo de espera, con sockets reales en 127.0.0.1.
"""

import gzip
import json
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


class Flujo(httpx.AsyncByteStream):
    """Cuerpo que llega por partes, como por la red (httpx lee de una vez un cuerpo en bytes)."""

    def __init__(self, contenido):
        self.contenido = contenido

    async def __aiter__(self):
        for i in range(0, len(self.contenido), 512):
            yield self.contenido[i:i + 512]


def R(estado, content=b"", json=None, headers=()):
    """Respuesta del módulo simulado; se arma de nuevo en cada petición."""
    return estado, content, json, headers


class Modulo:
    """Módulo simulado: guarda cada petición que recibe y responde lo que se le pida."""

    def __init__(self, *respuestas):
        self.recibidas = []
        self.respuestas = list(respuestas) or [R(200, json={"ok": True})]

    def __call__(self, peticion):
        peticion.read()
        self.recibidas.append(peticion)
        estado, contenido, cuerpo_json, cabeceras = (
            self.respuestas.pop(0) if len(self.respuestas) > 1 else self.respuestas[0])
        cabeceras = list(cabeceras.items()) if isinstance(cabeceras, dict) else list(cabeceras)
        if cuerpo_json is not None:
            contenido = json.dumps(cuerpo_json).encode()
            cabeceras.append(("Content-Type", "application/json"))
        return httpx.Response(estado, headers=cabeceras, stream=Flujo(contenido))


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
    modulo = Modulo(R(
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
    modulo = Modulo(R(307, headers={"Location": "http://otro:1/x"}))
    with cliente(modulo) as c:
        respuesta = c.get("/bus/coredb/docs", headers=AUT, follow_redirects=False)
    assert respuesta.status_code == 307
    assert respuesta.headers["location"] == "http://otro:1/x"
    assert len(modulo.recibidas) == 1


def test_cuerpo_comprimido_pasa_tal_cual():
    original = b'{"datos": "' + b"x" * 2000 + b'"}'
    comprimido = gzip.compress(original)
    modulo = Modulo(R(200, content=comprimido,
                                   headers={"Content-Encoding": "gzip", "Content-Type": "application/json"}))
    with cliente(modulo) as c:
        respuesta = c.get("/bus/coredb/x", headers={**AUT, "Accept-Encoding": "gzip"})
    assert respuesta.headers["content-encoding"] == "gzip"
    assert respuesta.content == original  # el cliente de prueba descomprime lo que recibió


# ── Errores con su código original ───────────────────────────────────────

@pytest.mark.parametrize("estado", [400, 401, 403, 404, 409, 422, 429, 500, 502, 503])
def test_errores_del_modulo_con_su_codigo_y_cuerpo(estado):
    cuerpo = b'{"detail": "mensaje del modulo", "codigo": "X"}'
    modulo = Modulo(R(estado, content=cuerpo, headers={"Content-Type": "application/json"}))
    with cliente(modulo) as c:
        respuesta = c.post("/bus/desembolso/api/v1/ordenes", headers={**AUT, "X-Idempotency-Key": "k1"},
                           content=b"{}")
    assert respuesta.status_code == estado
    assert respuesta.content == cuerpo
    assert len(modulo.recibidas) == 1  # nunca reintenta


def test_cuerpo_que_no_es_json_pasa_igual():
    modulo = Modulo(R(500, content=b"Internal Server Error",
                                   headers={"Content-Type": "text/plain; charset=utf-8"}))
    with cliente(modulo) as c:
        respuesta = c.get("/bus/tarjetas/x", headers=AUT)
    assert respuesta.status_code == 500
    assert respuesta.text == "Internal Server Error"
    assert respuesta.headers["content-type"] == "text/plain; charset=utf-8"


# ── Idempotencia ─────────────────────────────────────────────────────────

def test_repeticion_idempotente_llega_igual_y_la_respuesta_del_modulo_no_cambia():
    primera = R(201, json={"uuid_transaccion": "t-1", "repetida": False})
    segunda = R(200, json={"uuid_transaccion": "t-1", "repetida": True},
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


# ── Con sockets reales: uvicorn delante y un módulo HTTP de verdad detrás ─

def test_por_la_red_real_llega_y_vuelve_igual():
    import http.server
    import json as js

    import uvicorn

    class Eco(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            cuerpo = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            respuesta = js.dumps({"ruta": self.path, "cuerpo": cuerpo.decode(),
                                  "cabeceras": {k.lower(): v for k, v in self.headers.items()}}).encode()
            self.send_response(409)
            self.send_header("Content-Type", "application/json")
            self.send_header("Set-Cookie", "a=1")
            self.send_header("Set-Cookie", "b=2")
            self.send_header("X-Correlation-ID", "eco")
            self.send_header("Content-Length", str(len(respuesta)))
            self.end_headers()
            self.wfile.write(respuesta)

        def log_message(self, *args):
            pass

    modulo = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Eco)
    threading.Thread(target=modulo.serve_forever, daemon=True).start()
    puerto = puerto_cerrado()
    app = crear_app(cargar(entorno(BUS_URL_SOL=f"http://127.0.0.1:{modulo.server_address[1]}/gateway")))
    servidor = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=puerto, log_level="warning"))
    hilo = threading.Thread(target=servidor.run, daemon=True)
    hilo.start()
    try:
        for _ in range(100):
            if servidor.started:
                break
            time.sleep(0.05)
        respuesta = httpx.post(
            f"http://127.0.0.1:{puerto}/bus/sol/sol/A%2FB?search=caf%C3%A9&a=1&a=2",
            headers={**AUT, "Authorization": "Bearer t", "X-Idempotency-Key": "k-7",
                     "X-Correlation-ID": "c-7", "Content-Type": "application/json"},
            content=b'{"x": 1}', timeout=10)
    finally:
        servidor.should_exit = True
        hilo.join(10)
        modulo.shutdown()
    assert respuesta.status_code == 409
    assert respuesta.headers.get_list("set-cookie") == ["a=1", "b=2"]
    assert respuesta.headers["x-correlation-id"] == "eco"
    eco = respuesta.json()
    assert eco["ruta"] == "/gateway/sol/A%2FB?search=caf%C3%A9&a=1&a=2"
    assert eco["cuerpo"] == '{"x": 1}'
    assert eco["cabeceras"]["authorization"] == "Bearer t"
    assert eco["cabeceras"]["x-idempotency-key"] == "k-7"
    assert eco["cabeceras"]["x-correlation-id"] == "c-7"
    assert "x-bus-token" not in eco["cabeceras"]


# ── Módulos de bna-bus-servicios: CLIENTES, CORE y BILLETERA ──────────────────

CRED_CLIENTES = "c" * 40
CRED_CORE = "k" * 40


def test_modulos_opcionales_solo_si_tienen_url():
    assert "CLIENTES" not in cargar(entorno()).modulos
    config = cargar(entorno(BUS_URL_CLIENTES="http://clientes:8000", BUS_URL_CORE="http://core:8000"))
    assert config.modulos["CLIENTES"] == "http://clientes:8000"
    assert config.modulos["CORE"] == "http://core:8000"
    assert "BILLETERA" not in config.modulos


def test_modulo_opcional_sin_url_es_desconocido():
    modulo = Modulo()
    with cliente(modulo) as c:
        respuesta = c.post("/bus/clientes/clientes/registrar", headers=AUT)
    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "MODULO_DESCONOCIDO"
    assert modulo.recibidas == []


def test_presenta_credencial_de_servicio_y_descarta_la_del_consumidor():
    modulo = Modulo(R(201, json={"correcto": True}))
    with cliente(modulo, BUS_URL_CLIENTES="http://clientes:8000", BUS_CREDENCIAL_CLIENTES=CRED_CLIENTES) as c:
        respuesta = c.post("/bus/clientes/clientes/registrar",
                           headers={**AUT, "X-Service-Token": "falsificada", "X-Correlation-ID": "c-1"},
                           json={"dni": "12345678"})
    assert respuesta.status_code == 201
    peticion = modulo.recibidas[0]
    assert str(peticion.url) == "http://clientes:8000/clientes/registrar"
    assert peticion.headers.get_list("x-service-token") == [CRED_CLIENTES]
    assert peticion.headers["x-correlation-id"] == "c-1"
    assert "x-bus-token" not in peticion.headers


def test_sin_credencial_de_servicio_reenvia_la_cabecera_tal_cual():
    modulo = Modulo()
    with cliente(modulo) as c:
        c.get("/bus/cuentas/x", headers={**AUT, "X-Service-Token": "del-consumidor"})
    assert modulo.recibidas[0].headers["x-service-token"] == "del-consumidor"


def test_modulo_restringido_a_ciertos_consumidores():
    modulo = Modulo()
    with cliente(modulo, BUS_CONSUMIDORES="FRONTEND,PRUEBAS,CLIENTES", BUS_TOKEN_CLIENTES="q" * 48,
                 BUS_URL_CORE="http://core:8000", BUS_CREDENCIAL_CORE=CRED_CORE,
                 BUS_PERMITIDOS_CORE="CLIENTES") as c:
        negado = c.get("/bus/core/interno/solicitudes-registro", headers=AUT)
        aceptado = c.get("/bus/core/interno/solicitudes-registro", headers={"X-Bus-Token": "q" * 48})
    assert negado.status_code == 403
    assert negado.json() == {"detail": "El consumidor no puede usar el módulo CORE.",
                             "codigo": "BUS_CONSUMIDOR_NO_AUTORIZADO", "modulo": "CORE"}
    assert len(modulo.recibidas) == 1  # solo la aceptada

    assert aceptado.status_code == 200
    assert str(modulo.recibidas[0].url) == "http://core:8000/interno/solicitudes-registro"
    assert modulo.recibidas[0].headers["x-service-token"] == CRED_CORE


@pytest.mark.parametrize("cambios, mensaje", [
    ({"BUS_CREDENCIAL_CORE": CRED_CORE}, "BUS_CREDENCIAL_CORE: el módulo CORE no tiene BUS_URL_CORE"),
    ({"BUS_URL_CORE": "http://core:8000", "BUS_CREDENCIAL_CORE": "corta"}, "BUS_CREDENCIAL_CORE: al menos"),
    ({"BUS_URL_CORE": "http://core:8000", "BUS_CREDENCIAL_CORE": TOKEN_PRUEBAS},
     "BUS_CREDENCIAL_CORE: repite el token"),
    ({"BUS_PERMITIDOS_CUENTAS": "FRONTEND,NADIE"}, "BUS_PERMITIDOS_CUENTAS: no están en BUS_CONSUMIDORES: NADIE"),
    ({"BUS_URL_BILLETERA": "ftp://billetera"}, "BUS_URL_BILLETERA: URL http(s)"),
])
def test_configuracion_de_modulos_extra_invalida(cambios, mensaje):
    with pytest.raises(ConfiguracionInvalida, match=mensaje.replace("(", r"\(").replace(")", r"\)")):
        cargar(entorno(**cambios))


# ── Swagger combinado y estado de los módulos ─────────────────────────────────

def openapi_modulo(titulo, rutas):
    return {"openapi": "3.1.0", "info": {"title": titulo, "version": "1.0"},
            "paths": rutas,
            "components": {"schemas": {"Cuenta": {"type": "object"}},
                           "securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}}}


def test_docs_publica_las_rutas_de_cada_modulo():
    def modulo(peticion):
        if peticion.url.host == "cuentas.interno" and peticion.url.path == "/openapi.json":
            return httpx.Response(200, json=openapi_modulo("CUENTAS", {
                "/api/v1/cuentas/{num}": {"get": {
                    "operationId": "leer", "tags": ["cuentas"], "security": [{"bearer": []}],
                    "responses": {"200": {"content": {"application/json": {
                        "schema": {"$ref": "#/components/schemas/Cuenta"}}}}}}}}))
        return httpx.Response(404)

    app = crear_app(cargar(entorno()), transport=httpx.MockTransport(modulo))
    with TestClient(app) as c:
        spec = c.get("/openapi.json").json()
        assert c.get("/docs").status_code == 200

    operacion = spec["paths"]["/bus/cuentas/api/v1/cuentas/{num}"]["get"]
    assert operacion["tags"] == ["CUENTAS"]
    assert operacion["operationId"] == "CUENTAS__leer"
    assert operacion["security"] == [{"BusToken": [], "CUENTAS__bearer": []}]
    esquema = operacion["responses"]["200"]["content"]["application/json"]["schema"]
    assert esquema == {"$ref": "#/components/schemas/CUENTAS__Cuenta"}
    assert "CUENTAS__Cuenta" in spec["components"]["schemas"]
    assert spec["components"]["securitySchemes"]["BusToken"] == {
        "type": "apiKey", "in": "header", "name": "X-Bus-Token"}
    etiquetas = {e["name"]: e["description"] for e in spec["tags"]}
    assert etiquetas["CUENTAS"] == "CUENTAS 1.0"
    assert etiquetas["SOL"].startswith("NO DISPONIBLE")
    assert spec["paths"]["/metricas"]["get"]["security"] == [{"BusToken": []}]


def test_modulos_dice_cual_contesta_y_cual_no():
    def modulo(peticion):
        if peticion.url.host == "tarjetas.interno":
            raise httpx.ConnectError("caído", request=peticion)
        return httpx.Response(404)

    app = crear_app(cargar(entorno()), transport=httpx.MockTransport(modulo))
    with TestClient(app) as c:
        assert c.get("/modulos").status_code == 401
        cuerpo = c.get("/modulos", headers=AUT).json()

    assert cuerpo["total"] == len(MODULOS)
    assert cuerpo["disponibles"] == len(MODULOS) - 1
    assert cuerpo["modulos"]["TARJETAS"] == {"estado": "NO_DISPONIBLE", "motivo": "ConnectError"}
    assert cuerpo["modulos"]["CUENTAS"]["estado"] == "DISPONIBLE"


# ── Canal público (app móvil): solo a los módulos de BUS_MODULOS_PUBLICOS ─────

def test_modulo_publico_sin_credencial_llega_como_publico():
    modulo = Modulo(R(200, json={"token": "t"}))
    with cliente(modulo, BUS_URL_BILLETERA="http://billetera:3000", BUS_MODULOS_PUBLICOS="BILLETERA") as c:
        respuesta = c.post("/bus/billetera/api/login", json={"celular": "900000001"},
                           headers={"Authorization": "Bearer usuario", "Idempotency-Key": "k-1"})
        assert respuesta.status_code == 200
        peticion = modulo.recibidas[0]
        assert str(peticion.url) == "http://billetera:3000/api/login"
        assert peticion.headers["authorization"] == "Bearer usuario"
        assert peticion.headers["idempotency-key"] == "k-1"
        # Los demás módulos siguen exigiendo credencial, y una credencial falsa no se tolera.
        assert c.get("/bus/cuentas/x").status_code == 401
        assert c.get("/bus/billetera/api/me", headers={"X-Bus-Token": "falsa"}).status_code == 401
        assert c.get("/bus/BILLETERA/api/me").status_code == 401
        assert c.get("/metricas", headers=AUT).json()["reenvios"]["PUBLICO"] == {"BILLETERA": 1}


def test_sin_modulos_publicos_todo_exige_credencial():
    with cliente(Modulo(), BUS_URL_BILLETERA="http://billetera:3000") as c:
        assert c.get("/bus/billetera/api/salud").status_code == 401


@pytest.mark.parametrize("cambios, mensaje", [
    ({"BUS_MODULOS_PUBLICOS": "BILLETERA"}, "BUS_MODULOS_PUBLICOS: el módulo BILLETERA no está en el Bus"),
    ({"BUS_MODULOS_PUBLICOS": "CUENTAS", "BUS_PERMITIDOS_CUENTAS": "FRONTEND"},
     "BUS_MODULOS_PUBLICOS: CUENTAS tiene BUS_PERMITIDOS_CUENTAS"),
    ({"BUS_CONSUMIDORES": "FRONTEND,PUBLICO", "BUS_TOKEN_PUBLICO": "u" * 40}, "PUBLICO está reservado"),
])
def test_configuracion_publica_invalida(cambios, mensaje):
    with pytest.raises(ConfiguracionInvalida, match=mensaje):
        cargar(entorno(**cambios))


def test_consumidores_extra_se_suman_a_la_lista():
    config = cargar(entorno(BUS_CONSUMIDORES_EXTRA="CLIENTES,PRUEBAS", BUS_TOKEN_CLIENTES="q" * 48))
    assert sorted(config.consumidores.values()) == ["CLIENTES", "FRONTEND", "PRUEBAS"]
    with pytest.raises(ConfiguracionInvalida, match="faltan BUS_TOKEN_CLIENTES"):
        cargar(entorno(BUS_CONSUMIDORES_EXTRA="CLIENTES"))


def test_varios_modulos_publicos():
    with cliente(Modulo(), BUS_URL_BILLETERA="http://billetera:3000",
                 BUS_MODULOS_PUBLICOS="BILLETERA, seguridad") as c:
        assert c.get("/bus/billetera/api/salud").status_code == 200
        assert c.get("/bus/seguridad/").status_code == 200
        assert c.get("/bus/cuentas/health").status_code == 401
        assert c.get("/metricas", headers=AUT).json()["reenvios"]["PUBLICO"] == {"BILLETERA": 1, "SEGURIDAD": 1}
