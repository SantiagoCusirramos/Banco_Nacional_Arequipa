"""Cliente HTTP de COREDB: la única persistencia de Evaluación.

Dos credenciales:
- **El usuario de servicio** (`svc-evaluacion`, `SERVICIO:EVALUACION`) registra el expediente de
  SOL y lee los resultados para CR-INT-03. Su token se pide con el secreto del despliegue y se
  recuerda hasta poco antes de vencer; si COREDB lo rechaza, se pide otro una vez.
- **El token de la persona** (analista, auditor) se reenvía tal cual en lo que hace ella, para que
  la auditoría de COREDB registre a la persona.

Los errores de COREDB (`{"error": {"code", "message"}}`) pasan con su estado y su código; si
COREDB no responde, 503 COREDB_NO_DISPONIBLE.
"""
from __future__ import annotations

import threading
import time
from typing import Any

import httpx

from .comun import ErrorEva, correlacion_actual

MARGEN_VENCIMIENTO_SEG = 60


def _no_disponible() -> ErrorEva:
    return ErrorEva(503, "COREDB_NO_DISPONIBLE", "COREDB no respondió. Intenta de nuevo.")


class ClienteCoreDb:
    def __init__(self, url: str, usuario: str, secreto: str, *, timeout: float = 5.0,
                 transporte: httpx.BaseTransport | None = None):
        self._http = httpx.Client(base_url=url, timeout=timeout, transport=transporte,
                                  follow_redirects=False, trust_env=False)
        self._usuario = usuario
        self._secreto = secreto
        self._token: tuple[str, float] | None = None
        self._candado = threading.Lock()

    def cerrar(self) -> None:
        self._http.close()

    # ------------------------------------------------------------------ Sesión del servicio
    def token_servicio(self, renovar: bool = False) -> str:
        with self._candado:
            if not renovar and self._token and self._token[1] > time.monotonic():
                return self._token[0]
            try:
                r = self._http.post("/coredb/auth/login", json={"username": self._usuario, "password": self._secreto},
                                    headers={"X-Correlation-ID": correlacion_actual()})
            except httpx.HTTPError:
                raise _no_disponible() from None
            if r.status_code != 200:
                # El secreto nunca se repite; el detalle queda en los registros de COREDB.
                raise ErrorEva(503, "SERVICIO_SIN_SESION",
                               "Evaluación no pudo iniciar sesión en COREDB con su usuario de servicio.")
            datos = r.json()
            vence = time.monotonic() + max(0, int(datos.get("expires_in", 0)) - MARGEN_VENCIMIENTO_SEG)
            self._token = (datos["access_token"], vence)
            return self._token[0]

    def como_servicio(self, metodo: str, ruta: str, **opciones) -> tuple[int, Any]:
        r = self._enviar(metodo, ruta, self.token_servicio(), **opciones)
        if r.status_code == 401:
            r = self._enviar(metodo, ruta, self.token_servicio(renovar=True), **opciones)
        return self._resultado(r)

    # ------------------------------------------------------------------ En nombre de una persona
    def como_persona(self, token: str, metodo: str, ruta: str, **opciones) -> tuple[int, Any]:
        return self._resultado(self._enviar(metodo, ruta, token, **opciones))

    def salud(self) -> bool:
        try:
            return self._http.get("/coredb/salud").status_code == 200
        except httpx.HTTPError:
            return False

    # ------------------------------------------------------------------
    def _enviar(self, metodo: str, ruta: str, token: str, **opciones) -> httpx.Response:
        cabeceras = {"Authorization": f"Bearer {token}", "X-Correlation-ID": correlacion_actual()}
        try:
            return self._http.request(metodo, ruta, headers=cabeceras, **opciones)
        except httpx.HTTPError:
            raise _no_disponible() from None

    @staticmethod
    def _resultado(r: httpx.Response) -> tuple[int, Any]:
        if r.is_success:
            return r.status_code, r.json()
        try:
            cuerpo = r.json()
        except ValueError:
            cuerpo = None
        error = cuerpo.get("error") if isinstance(cuerpo, dict) else None
        if r.status_code >= 500 or not isinstance(error, dict):
            if r.status_code == 422:
                # Validación de FastAPI en COREDB: Evaluación valida antes, así que no debería pasar.
                raise ErrorEva(422, "DATOS_RECHAZADOS_POR_COREDB", "COREDB rechazó los datos enviados.")
            raise _no_disponible()
        raise ErrorEva(r.status_code, str(error.get("code", "ERROR_COREDB")), str(error.get("message", "")))
