"""Bus de Servicios: punto único por el que los canales llegan a los módulos.

/bus/<módulo>/<ruta> se reenvía a <URL del módulo>/<ruta> sin tocar nada: método, ruta y
consulta crudas, cuerpo en bytes, todas las cabeceras (Authorization, X-Idempotency-Key,
X-Correlation-ID, cookies...) salvo las de salto a salto y la credencial del Bus, y de
vuelta el código, las cabeceras y el cuerpo del módulo tal como llegaron. Nunca reintenta:
un POST repetido lo decide el módulo con su llave de idempotencia.

Lo único que el Bus responde por su cuenta: 401 si el consumidor no presenta su
credencial (X-Bus-Token), 404 si el módulo no existe, 503 si el módulo no acepta la
conexión, 504 si no responde a tiempo y 502 si corta la respuesta a medias.
"""

import hmac
import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from BUS_SERVICIOS import registros

CABECERA_CREDENCIAL = "x-bus-token"
# Cabeceras de salto a salto (RFC 9110 §7.6.1): son de cada conexión, no del mensaje.
SALTO_A_SALTO = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
                 "proxy-connection", "te", "trailer", "trailers", "transfer-encoding", "upgrade"}
METODOS = ["GET", "POST", "PUT", "PATCH", "DELETE"]

log = logging.getLogger("bna.bus")


def _de_salto(cabeceras):
    """Nombres que no se reenvían: los de salto a salto y los que lista Connection."""
    nombres = set(SALTO_A_SALTO)
    for nombre, valor in cabeceras:
        if nombre.lower() == "connection":
            nombres.update(n.strip().lower() for n in valor.split(",") if n.strip())
    return nombres


def crear_app(config, transport=None):
    estado = {"cliente": None}
    reenvios = defaultdict(lambda: defaultdict(int))

    @asynccontextmanager
    async def ciclo(_app):
        quitar_filtro = registros.proteger()
        estado["cliente"] = httpx.AsyncClient(
            transport=transport,
            timeout=httpx.Timeout(config.timeout, connect=config.timeout_conexion),
            follow_redirects=False,
            trust_env=False,
        )
        try:
            yield
        finally:
            await estado["cliente"].aclose()
            quitar_filtro()

    app = FastAPI(
        title="BNA - Bus de Servicios",
        description="Punto único por el que los canales llegan a los módulos del producto. "
                    "Reenvía sin tocar cabeceras, cuerpo ni códigos.",
        version="1.0.0",
        lifespan=ciclo,
    )

    def error(codigo_http, codigo, detalle, request, modulo=None):
        cuerpo = {"detail": detalle, "codigo": codigo}
        if modulo:
            cuerpo["modulo"] = modulo
        cabeceras = {}
        correlacion = request.headers.get("x-correlation-id")
        if correlacion:
            cabeceras["X-Correlation-ID"] = correlacion
        return JSONResponse(cuerpo, status_code=codigo_http, headers=cabeceras)

    def consumidor(request):
        presentado = request.headers.get(CABECERA_CREDENCIAL, "").encode()
        encontrado = None
        for token, nombre in config.consumidores.items():
            if hmac.compare_digest(presentado, token.encode()):
                encontrado = nombre
        return encontrado

    @app.get("/salud", tags=["Sistema"])
    def salud():
        return {"modulo": "Bus de Servicios", "estado": "operativo", "modulos": sorted(config.modulos)}

    @app.get("/metricas", tags=["Sistema"])
    def metricas(request: Request):
        if consumidor(request) is None:
            return error(401, "BUS_CREDENCIAL_INVALIDA", "Credencial del Bus ausente o inválida.", request)
        return {"reenvios": {c: dict(m) for c, m in reenvios.items()}}

    @app.api_route("/bus/{modulo}/{ruta:path}", methods=METODOS, tags=["Módulos"])
    async def reenviar(modulo: str, ruta: str, request: Request):
        llamador = consumidor(request)
        if llamador is None:
            return error(401, "BUS_CREDENCIAL_INVALIDA", "Credencial del Bus ausente o inválida.", request)
        nombre = modulo.upper()
        base = config.modulos.get(nombre)
        if base is None or modulo != modulo.lower():
            return error(404, "MODULO_DESCONOCIDO", "El Bus no tiene ese módulo.", request)

        # Ruta y consulta crudas: lo que sigue a /bus/<módulo>, sin decodificar.
        # (uvicorn deja la consulta fuera de raw_path; el cliente de pruebas de Starlette, no).
        crudo = request.scope["raw_path"].split(b"?", 1)[0].split(b"/", 3)
        resto = b"/" + (crudo[3] if len(crudo) > 3 else b"")
        url = base + resto.decode("latin-1")
        consulta = request.scope.get("query_string", b"")
        if consulta:
            url += "?" + consulta.decode("latin-1")

        entrantes = request.headers.raw
        excluir = _de_salto((n.decode("latin-1"), v.decode("latin-1")) for n, v in entrantes)
        excluir |= {"host", "content-length", CABECERA_CREDENCIAL}
        cabeceras = [(n, v) for n, v in entrantes if n.decode("latin-1").lower() not in excluir]
        cuerpo = await request.body()

        cliente = estado["cliente"]
        peticion = cliente.build_request(request.method, url, headers=cabeceras, content=cuerpo or None)
        # httpx agrega sus cabeceras por omisión (User-Agent, Accept...): fuera las que no traía.
        traidas = {n.decode("latin-1").lower() for n, _ in cabeceras} | {"host", "content-length"}
        for extra in [n for n in peticion.headers if n.lower() not in traidas]:
            del peticion.headers[extra]

        reenvios[llamador][nombre] += 1
        inicio = time.monotonic()
        try:
            respuesta = await cliente.send(peticion, stream=True)
            try:
                contenido = b"".join([parte async for parte in respuesta.aiter_raw()])
            finally:
                await respuesta.aclose()
        except (httpx.ConnectError, httpx.ConnectTimeout):
            resultado = error(503, "MODULO_NO_DISPONIBLE", f"No se pudo contactar al módulo {nombre}.",
                              request, nombre)
        except httpx.TimeoutException:
            resultado = error(504, "MODULO_SIN_RESPUESTA",
                              f"El módulo {nombre} no respondió en {config.timeout:g} s.", request, nombre)
        except httpx.HTTPError:
            resultado = error(502, "MODULO_RESPUESTA_INVALIDA",
                              f"El módulo {nombre} cortó la respuesta.", request, nombre)
        else:
            resultado = Response(content=contenido, status_code=respuesta.status_code)
            quitar = _de_salto(respuesta.headers.multi_items()) | {"content-length"}
            resultado.raw_headers = [
                (n, v) for n, v in respuesta.headers.raw if n.decode("latin-1").lower() not in quitar
            ] + [(b"content-length", str(len(contenido)).encode())]

        # Solo metadatos: nunca cuerpo, consulta ni cabeceras.
        log.info("%s %s %s -> %s en %d ms (correlación %s)", llamador, request.method, nombre,
                 resultado.status_code, (time.monotonic() - inicio) * 1000,
                 request.headers.get("x-correlation-id", "-"))
        return resultado

    return app
