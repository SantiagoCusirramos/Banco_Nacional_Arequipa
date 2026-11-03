"""Clientes HTTP hacia los otros servicios: RENIEC (directo) y Core (SIEMPRE a través del Bus)."""
import logging
import time
from typing import Any

import httpx

from shared.comun import ApiError

from . import config

log = logging.getLogger("clientes.http")

_reniec = httpx.AsyncClient(timeout=httpx.Timeout(config.RENIEC_TIMEOUT_SEG, connect=3.0))
_bus = httpx.AsyncClient(timeout=httpx.Timeout(config.BUS_TIMEOUT_SEG, connect=3.0))


async def cerrar() -> None:
    await _reniec.aclose()
    await _bus.aclose()


# ----------------------------------------------------------------- RENIEC
class ReniecNoDisponible(Exception):
    pass


async def reniec_post(ruta: str, cuerpo: dict) -> dict:
    """POST a RENIEC. Falla de red/5xx -> ReniecNoDisponible; 4xx -> ApiError con el código de RENIEC."""
    try:
        r = await _reniec.post(config.RENIEC_URL + ruta, json=cuerpo, headers={"X-Service-Token": config.RENIEC_SERVICE_TOKEN})
    except httpx.HTTPError as e:
        log.warning("RENIEC no disponible (%s)", type(e).__name__)
        raise ReniecNoDisponible()
    if r.status_code >= 500:
        log.warning("RENIEC respondió %s", r.status_code)
        raise ReniecNoDisponible()
    datos = _json(r)
    if r.status_code >= 400:
        raise ApiError(r.status_code if r.status_code != 401 else 502, datos.get("codigo", "RENIEC_ERROR"),
                       datos.get("mensaje", "RENIEC rechazó la solicitud"))
    return datos


async def reniec_salud() -> str:
    try:
        r = await _reniec.get(config.RENIEC_URL + "/salud", timeout=3.0)
        return "ok" if r.status_code == 200 else "error"
    except httpx.HTTPError:
        return "caido"


# ----------------------------------------------------------------- Bus / Core
def _json(r: httpx.Response) -> Any:
    try:
        return r.json()
    except ValueError:
        return {"codigo": "RESPUESTA_INVALIDA", "mensaje": "El servicio devolvió una respuesta que no es JSON"}


def _cabeceras() -> dict:
    return {"X-Service-Token": config.BUS_TOKEN}


async def core(metodo: str, ruta: str, cuerpo: dict | None = None, params: dict | None = None) -> Any:
    """Llama al Core a través del Bus (/bus/core/<ruta>). Los errores se propagan con su código."""
    try:
        r = await _bus.request(metodo, f"{config.BUS_URL}/bus/core/{ruta}", json=cuerpo, params=params, headers=_cabeceras())
    except httpx.HTTPError as e:
        log.warning("Bus no disponible (%s)", type(e).__name__)
        raise ApiError(503, "BUS_NO_DISPONIBLE", "No se pudo contactar al Bus de Servicios")
    datos = _json(r)
    if r.status_code >= 400:
        raise ApiError(r.status_code, datos.get("codigo", "ERROR_CORE"), datos.get("mensaje", "Error en el Core"))
    return datos


async def bus_publico(operacion: str, cuerpo: dict) -> tuple[int, Any, int]:
    """Laboratorio: invoca una operación de Clientes ENTRANDO por el Bus, como lo haría otro módulo.

    Devuelve (http, respuesta, milisegundos); un error de conexión se devuelve como respuesta 503 para mostrarlo en consola.
    """
    inicio = time.perf_counter()
    try:
        r = await _bus.post(f"{config.BUS_URL}/bus/clientes/{operacion}", json=cuerpo, headers=_cabeceras())
        status, datos = r.status_code, _json(r)
    except httpx.HTTPError:
        status, datos = 503, {"correcto": False, "codigo": "BUS_NO_DISPONIBLE", "mensaje": "No se pudo contactar al Bus de Servicios"}
    return status, datos, int((time.perf_counter() - inicio) * 1000)


async def bus_salud() -> dict:
    try:
        r = await _bus.get(config.BUS_URL + "/salud", timeout=5.0)
        d = _json(r)
        return {"bus": "ok", "core": d.get("core", "desconocido")}
    except httpx.HTTPError:
        return {"bus": "caido", "core": "desconocido"}
