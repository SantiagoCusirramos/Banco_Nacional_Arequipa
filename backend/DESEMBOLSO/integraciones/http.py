"""Cliente HTTP hacia un módulo del producto: correlación, tiempos de espera, reintentos y latencias.

Todavía no hay Bus de Servicios: cada módulo se llama directamente dentro de la red de Docker.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict

import httpx

from ..core.correlacion import correlation_id
from ..core.errores import DependenciaNoDisponible


class Latencias:
    """Llamadas y segundos acumulados por dependencia, para /metrics (AC-42)."""

    def __init__(self):
        self._candado = threading.Lock()
        self._datos: dict[str, list[float]] = defaultdict(lambda: [0, 0.0])

    def registrar(self, dependencia: str, segundos: float) -> None:
        with self._candado:
            acumulado = self._datos[dependencia]
            acumulado[0] += 1
            acumulado[1] += segundos

    def items(self):
        with self._candado:
            return [(k, tuple(v)) for k, v in self._datos.items()]


class ClienteHttp:
    def __init__(self, modulo: str, base_url: str, timeout: float, latencias: Latencias,
                 transporte: httpx.BaseTransport | None = None):
        self.modulo = modulo
        self._latencias = latencias
        self._timeout = timeout
        self._http = httpx.Client(base_url=base_url or "http://no-configurado.invalid", timeout=timeout,
                                  transport=transporte, follow_redirects=False, trust_env=False)

    def cerrar(self) -> None:
        self._http.close()

    def solicitar(self, metodo: str, ruta: str, *, json: dict | None = None, params: dict | None = None,
                  cabeceras: dict | None = None, timeout: float | None = None, reintentos: int = 0) -> httpx.Response:
        """Envía la petición. Solo reintenta si `reintentos` > 0 (consultas); nunca en el abono (RT-04).

        Un tiempo agotado, una falla de red o un 5xx se informan como DependenciaNoDisponible(incierto=True)."""
        todas = {"X-Correlation-ID": correlation_id(), **(cabeceras or {})}
        intento = 0
        while True:
            inicio = time.perf_counter()
            try:
                respuesta = self._http.request(metodo, ruta, json=json, params=params, headers=todas,
                                               timeout=timeout or self._timeout)
                error = None
                if respuesta.status_code >= 500:
                    error = DependenciaNoDisponible(self.modulo, incierto=True, causa=f"HTTP_{respuesta.status_code}")
            except httpx.TimeoutException:
                error = DependenciaNoDisponible(self.modulo, incierto=True, causa="TIEMPO_AGOTADO")
            except httpx.TransportError as exc:
                error = DependenciaNoDisponible(self.modulo, incierto=True, causa=type(exc).__name__)
            finally:
                self._latencias.registrar(self.modulo.lower(), time.perf_counter() - inicio)
            if error is None:
                return respuesta
            if intento >= reintentos:
                raise error
            intento += 1
            time.sleep(min(0.2 * 2 ** intento, 2.0))


def cuerpo(respuesta: httpx.Response) -> dict:
    try:
        datos = respuesta.json()
    except ValueError:
        return {"texto": respuesta.text[:200]}
    return datos if isinstance(datos, dict) else {"datos": datos}
