"""Bus de Servicios: punto único por el que los canales llegan a los módulos.

/bus/<módulo>/<ruta> se reenvía a <URL del módulo>/<ruta> sin tocar nada: método, ruta y
consulta crudas, cuerpo en bytes, todas las cabeceras (Authorization, X-Idempotency-Key,
X-Correlation-ID, cookies...) salvo las de salto a salto y la credencial del Bus, y de
vuelta el código, las cabeceras y el cuerpo del módulo tal como llegaron. Nunca reintenta:
un POST repetido lo decide el módulo con su llave de idempotencia.

Lo único que el Bus responde por su cuenta: 401 si el consumidor no presenta su
credencial (X-Bus-Token), 404 si el módulo no existe, 503 si el módulo no acepta la
conexión, 504 si no responde a tiempo y 502 si corta la respuesta a medias. Y 403 si el
módulo solo atiende a ciertos consumidores (BUS_PERMITIDOS_<MÓDULO>) y este no es uno.

A un módulo público (BUS_MODULOS_PUBLICOS) se llega sin X-Bus-Token, como consumidor PUBLICO:
es para la app móvil, que no puede guardar un secreto; ese módulo autentica a su usuario.
Una X-Bus-Token presente pero inválida sigue siendo 401.

Si el módulo pide credencial de servicio (BUS_CREDENCIAL_<MÓDULO>), el Bus le presenta la
suya en X-Service-Token, en lugar de la que traiga el consumidor.
"""

import asyncio
import hmac
import json
import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, Response

CABECERA_CREDENCIAL = "x-bus-token"
# Credencial que el Bus presenta a un módulo que la pide (BUS_CREDENCIAL_<MÓDULO>).
CABECERA_SERVICIO = "x-service-token"
# Cabeceras de salto a salto (RFC 9110 §7.6.1): son de cada conexión, no del mensaje.
SALTO_A_SALTO = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
                 "proxy-connection", "te", "trailer", "trailers", "transfer-encoding", "upgrade"}
METODOS = ["GET", "POST", "PUT", "PATCH", "DELETE"]
# Esquema de seguridad del Bus en su OpenAPI (botón Authorize de /docs).
ESQUEMA_BUS = "BusToken"

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
    credenciales = config.credenciales or {}
    permitidos = config.permitidos or {}
    publicos = config.publicos or frozenset()
    reenvios = defaultdict(lambda: defaultdict(int))

    @asynccontextmanager
    async def ciclo(_app):
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

    app = FastAPI(
        title="BNA - Bus de Servicios",
        description="Punto único por el que los canales llegan a los módulos del producto. "
                    "Reenvía sin tocar cabeceras, cuerpo ni códigos.",
        version="1.0.0",
        lifespan=ciclo,
        # /docs y /openapi.json los arma el Bus más abajo, con las rutas de cada módulo.
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
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

    def cabeceras_para(nombre):
        credencial = credenciales.get(nombre)
        return {"X-Service-Token": credencial} if credencial else {}

    async def sondear(nombre, base):
        """Cualquier respuesta HTTP del módulo cuenta como disponible: solo se mira si contesta."""
        inicio = time.monotonic()
        try:
            respuesta = await estado["cliente"].get(base + "/", headers=cabeceras_para(nombre))
            await respuesta.aclose()
        except httpx.HTTPError as falla:
            return nombre, {"estado": "NO_DISPONIBLE", "motivo": type(falla).__name__}
        return nombre, {"estado": "DISPONIBLE", "ms": round((time.monotonic() - inicio) * 1000)}

    @app.get("/modulos", tags=["Sistema"],
             summary="Estado en vivo de cada módulo conectado al Bus")
    async def modulos(request: Request):
        if consumidor(request) is None:
            return error(401, "BUS_CREDENCIAL_INVALIDA", "Credencial del Bus ausente o inválida.", request)
        resultados = await asyncio.gather(*(sondear(n, b) for n, b in sorted(config.modulos.items())))
        return {"modulos": dict(resultados),
                "disponibles": sum(r["estado"] == "DISPONIBLE" for _, r in resultados),
                "total": len(resultados)}

    async def openapi_de(nombre, base):
        try:
            respuesta = await estado["cliente"].get(base + "/openapi.json", headers=cabeceras_para(nombre))
            if respuesta.status_code != 200:
                return nombre, None
            return nombre, respuesta.json()
        except (httpx.HTTPError, ValueError):
            return nombre, None

    def agregar_modulo(combinado, nombre, spec):
        """Publica las rutas del módulo bajo /bus/<módulo>, con sus esquemas renombrados
        (<MÓDULO>__X) para que no choquen con los de otro módulo."""
        prefijo = nombre + "__"
        spec = json.loads(json.dumps(spec).replace('"#/components/schemas/',
                                                   f'"#/components/schemas/{prefijo}'))
        componentes = spec.get("components") or {}
        for clave, valor in (componentes.get("schemas") or {}).items():
            combinado["components"]["schemas"][prefijo + clave] = valor
        for clave, valor in (componentes.get("securitySchemes") or {}).items():
            combinado["components"]["securitySchemes"][prefijo + clave] = valor
        global_seguridad = spec.get("security")
        for ruta, operaciones in (spec.get("paths") or {}).items():
            nuevas = {}
            for metodo, operacion in operaciones.items():
                if metodo.upper() not in METODOS:
                    if metodo == "parameters":
                        nuevas[metodo] = operacion
                    continue
                operacion = dict(operacion)
                operacion["tags"] = [nombre]
                if "operationId" in operacion:
                    operacion["operationId"] = prefijo + operacion["operationId"]
                requisitos = operacion.get("security", global_seguridad) or [{}]
                # El Bus siempre pide su credencial; además, la que pida el módulo.
                operacion["security"] = [{ESQUEMA_BUS: [], **{prefijo + k: v for k, v in r.items()}}
                                         for r in requisitos]
                if nombre in publicos:  # también sin X-Bus-Token (canal PUBLICO)
                    operacion["security"] += [{prefijo + k: v for k, v in r.items()} for r in requisitos]
                nuevas[metodo] = operacion
            combinado["paths"][f"/bus/{nombre.lower()}{ruta}"] = nuevas

    @app.get("/openapi.json", include_in_schema=False)
    async def openapi():
        combinado = get_openapi(title=app.title, version=app.version, description=(
            app.description + "\n\nCada sección es un módulo conectado: sus rutas se leen en vivo "
            "de su propio OpenAPI. Presente su credencial con **Authorize** (X-Bus-Token)."),
            routes=app.routes)
        componentes = combinado.setdefault("components", {})
        componentes.setdefault("schemas", {})
        componentes.setdefault("securitySchemes", {})[ESQUEMA_BUS] = {
            "type": "apiKey", "in": "header", "name": "X-Bus-Token"}
        for ruta in ("/metricas", "/modulos", "/bus/{modulo}/{ruta}"):
            for operacion in combinado["paths"].get(ruta, {}).values():
                operacion["security"] = [{ESQUEMA_BUS: []}]
        etiquetas = [{"name": "Sistema", "description": "Salud, métricas y estado de los módulos."}]
        especificaciones = await asyncio.gather(
            *(openapi_de(n, b) for n, b in sorted(config.modulos.items())))
        for nombre, spec in especificaciones:
            if spec is None:
                etiquetas.append({"name": nombre, "description":
                                  "NO DISPONIBLE: no publicó su /openapi.json. Use el reenvío genérico."})
                continue
            info = spec.get("info") or {}
            etiquetas.append({"name": nombre, "description":
                              f"{info.get('title', nombre)} {info.get('version', '')}".strip()})
            agregar_modulo(combinado, nombre, spec)
        etiquetas.append({"name": "Módulos", "description":
                          "Reenvío genérico /bus/<módulo>/<ruta> (la ruta va tal cual al módulo)."})
        combinado["tags"] = etiquetas
        return JSONResponse(combinado)

    @app.get("/docs", include_in_schema=False)
    def docs():
        return get_swagger_ui_html(openapi_url="/openapi.json", title=app.title,
                                   swagger_ui_parameters={"persistAuthorization": True})

    @app.api_route("/bus/{modulo}/{ruta:path}", methods=METODOS, tags=["Módulos"])
    async def reenviar(modulo: str, ruta: str, request: Request):
        llamador = consumidor(request)
        nombre = modulo.upper()
        if (llamador is None and CABECERA_CREDENCIAL not in request.headers
                and nombre in publicos and modulo == modulo.lower()):
            llamador = "PUBLICO"
        if llamador is None:
            return error(401, "BUS_CREDENCIAL_INVALIDA", "Credencial del Bus ausente o inválida.", request)
        base = config.modulos.get(nombre)
        if base is None or modulo != modulo.lower():
            return error(404, "MODULO_DESCONOCIDO", "El Bus no tiene ese módulo.", request)
        if nombre in permitidos and llamador not in permitidos[nombre]:
            return error(403, "BUS_CONSUMIDOR_NO_AUTORIZADO",
                         f"El consumidor no puede usar el módulo {nombre}.", request, nombre)

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
        credencial = credenciales.get(nombre)
        if credencial:
            excluir.add(CABECERA_SERVICIO)
        cabeceras = [(n, v) for n, v in entrantes if n.decode("latin-1").lower() not in excluir]
        if credencial:
            cabeceras.append((CABECERA_SERVICIO.encode(), credencial.encode()))
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
