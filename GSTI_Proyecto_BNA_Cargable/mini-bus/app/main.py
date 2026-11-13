"""Mini-Bus de Servicios: solo ENRUTA peticiones JSON entre módulos. No tiene BD ni lógica de negocio.

Tabla de rutas (pública -> destino). Para cambiar al Bus oficial basta con apuntar BUS_URL a él
desde Clientes; este archivo no contiene reglas del banco.

REGLA: el Bus nunca llama a RENIEC (ni siquiera conoce su dirección).
"""
import logging
import time
import uuid

import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.responses import Response

from shared.comun import configurar_logging, entorno, instalar_manejadores, requerir_token, respuesta_error

configurar_logging()
log = logging.getLogger("bus")

BUS_TOKEN = entorno("BUS_TOKEN")
DESTINOS = {
    "CLIENTES": (entorno("CLIENTES_URL"), entorno("CLIENTES_TOKEN")),
    "CORE": (entorno("CORE_URL"), entorno("CORE_TOKEN")),
}
TIMEOUT = httpx.Timeout(float(entorno("BUS_TIMEOUT_SEG", "30")), connect=3.0)

# (método, ruta pública del Bus) -> (destino, ruta en el destino)
RUTAS = [
    # Otros módulos del banco -> módulo de Clientes
    ("POST", "/bus/clientes/registrar", "CLIENTES", "/clientes/registrar"),
    ("POST", "/bus/clientes/validar-documento", "CLIENTES", "/clientes/validar-documento"),
    ("POST", "/bus/clientes/validar-biometria", "CLIENTES", "/clientes/validar-biometria"),
    # Módulo de Clientes -> Core
    ("POST", "/bus/core/registrar-cliente", "CORE", "/interno/registrar-cliente"),
    ("POST", "/bus/core/auditar-registro", "CORE", "/interno/auditar-registro"),
    ("POST", "/bus/core/validar-documento", "CORE", "/interno/validar-documento"),
    ("POST", "/bus/core/validar-biometria", "CORE", "/interno/validar-biometria"),
    ("GET", "/bus/core/solicitudes-registro", "CORE", "/interno/solicitudes-registro"),
    ("GET", "/bus/core/solicitudes-validacion", "CORE", "/interno/solicitudes-validacion"),
]

app = FastAPI(title="Mini-Bus de Servicios (BNA)", version="1.0",
              description="Intermediario HTTP/JSON entre los módulos. Todas las rutas /bus/* exigen X-Service-Token.")
instalar_manejadores(app)
cliente_http: httpx.AsyncClient | None = None


@app.on_event("startup")
async def _inicio():
    global cliente_http
    cliente_http = httpx.AsyncClient(timeout=TIMEOUT)


@app.on_event("shutdown")
async def _fin():
    await cliente_http.aclose()


def _crear_ruta(metodo: str, ruta_publica: str, destino: str, ruta_destino: str) -> None:
    base, token = DESTINOS[destino]

    async def reenviar(request: Request) -> Response:
        inicio = time.perf_counter()
        id_peticion = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        cabeceras = {"X-Service-Token": token, "X-Request-ID": id_peticion}
        if metodo == "POST":
            cabeceras["Content-Type"] = "application/json"
        try:
            r = await cliente_http.request(metodo, base + ruta_destino, content=await request.body() if metodo == "POST" else None,
                                           params=dict(request.query_params), headers=cabeceras)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.RemoteProtocolError, httpx.PoolTimeout) as e:
            log.warning("%s %s -> %s NO DISPONIBLE (%s)", metodo, ruta_publica, destino, type(e).__name__)
            return respuesta_error(503, "SERVICIO_NO_DISPONIBLE", f"El Bus no pudo contactar al servicio {destino}", destino=destino)
        # Solo se registra metadata: nunca el cuerpo (podría contener plantillas biométricas).
        log.info("%s %s -> %s %s %s %dms id=%s", metodo, ruta_publica, destino, ruta_destino, r.status_code,
                 (time.perf_counter() - inicio) * 1000, id_peticion)
        return Response(content=r.content, status_code=r.status_code, media_type="application/json",
                        headers={"X-Request-ID": id_peticion})

    extra = {"requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}}} if metodo == "POST" else None
    app.add_api_route(ruta_publica, reenviar, methods=[metodo], dependencies=[Depends(requerir_token(BUS_TOKEN))],
                      tags=[f"Hacia {destino}"], summary=f"{metodo} {ruta_destino}", openapi_extra=extra)


for _m, _pub, _dest, _rd in RUTAS:
    _crear_ruta(_m, _pub, _dest, _rd)


@app.get("/salud", tags=["Estado"])
async def salud():
    """Estado del Bus y de los servicios que enruta (sin autenticación, no revela datos)."""
    estado = {"servicio": "mini-bus", "estado": "ok"}
    for nombre, (base, _) in DESTINOS.items():
        try:
            r = await cliente_http.get(base + "/salud", timeout=httpx.Timeout(3.0))
            estado[nombre.lower()] = "ok" if r.status_code == 200 else "error"
        except httpx.HTTPError:
            estado[nombre.lower()] = "caido"
    return estado
