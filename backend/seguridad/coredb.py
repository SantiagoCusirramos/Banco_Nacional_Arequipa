"""Cliente HTTP de COREDB, a través del Bus: la única persistencia de Seguridad.

- **El usuario de servicio** (`svc-seguridad`, `SERVICIO:SEGURIDAD`: `OPERAR_SEGURIDAD` y
  `VER_AUDITORIA`) sella y verifica la bitácora. Su token se pide con el secreto del despliegue y
  se recuerda hasta poco antes de vencer; si COREDB lo rechaza, se pide otro una vez.
- **Por una persona** (`por_persona`): el token del servicio en Authorization y el de la persona
  en X-Persona-Token. COREDB exige los dos, comprueba el permiso de la persona y la registra
  como actor. Así lo que hace Seguridad siempre tiene una persona responsable.
- **Como la persona** (`como_persona`): su token tal cual, para lo que COREDB ya le permite
  (iniciar sesión, su perfil, la bitácora).

Los errores de COREDB (`{"error": {"code", "message"}}`) pasan con su estado y su código; si
COREDB no responde, 503 COREDB_NO_DISPONIBLE.
"""
from __future__ import annotations

import threading
import time
from typing import Any

import httpx

from .comun import ErrorSeg, correlacion_actual

MARGEN_VENCIMIENTO_SEG = 60


def _no_disponible() -> ErrorSeg:
    return ErrorSeg(503, "COREDB_NO_DISPONIBLE", "COREDB no respondió. Intenta de nuevo.")


class ClienteCoreDb:
    def __init__(self, url: str, usuario: str, secreto: str, *, timeout: float = 5.0,
                 transporte: httpx.BaseTransport | None = None, bus_token: str = ""):
        # Credencial ante el Bus en cada llamada; el Bus no la reenvía a COREDB.
        self._http = httpx.Client(base_url=url, timeout=timeout, transport=transporte,
                                  follow_redirects=False, trust_env=False,
                                  headers={"X-Bus-Token": bus_token} if bus_token else None)
        self._usuario = usuario
        self._secreto = secreto
        self._token: tuple[str, float] | None = None
        self._candado = threading.Lock()

    def cerrar(self) -> None:
        self._http.close()

    # ------------------------------------------------------------------ sesión del servicio
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
                raise ErrorSeg(503, "SERVICIO_SIN_SESION",
                               "Seguridad no pudo iniciar sesión en COREDB con su usuario de servicio.")
            datos = r.json()
            vence = time.monotonic() + max(0, int(datos.get("expires_in", 0)) - MARGEN_VENCIMIENTO_SEG)
            self._token = (datos["access_token"], vence)
            return self._token[0]

    def como_servicio(self, metodo: str, ruta: str, **opciones) -> Any:
        return self._con_servicio(metodo, ruta, {}, **opciones)

    def por_persona(self, token_persona: str, metodo: str, ruta: str, **opciones) -> Any:
        return self._con_servicio(metodo, ruta, {"X-Persona-Token": token_persona}, **opciones)

    def como_persona(self, token: str | None, metodo: str, ruta: str, **opciones) -> Any:
        cabeceras = {"Authorization": f"Bearer {token}"} if token else {}
        return self._resultado(self._enviar(metodo, ruta, cabeceras, **opciones))

    def salud(self) -> bool:
        try:
            return self._http.get("/coredb/salud").status_code == 200
        except httpx.HTTPError:
            return False

    # ------------------------------------------------------------------
    def _con_servicio(self, metodo: str, ruta: str, extra: dict, **opciones) -> Any:
        r = self._enviar(metodo, ruta, {**extra, "Authorization": f"Bearer {self.token_servicio()}"}, **opciones)
        if r.status_code == 401 and self._codigo(r) in {"TOKEN_EXPIRADO", "TOKEN_INVALIDO", "USUARIO_NO_VIGENTE"}:
            r = self._enviar(metodo, ruta,
                             {**extra, "Authorization": f"Bearer {self.token_servicio(renovar=True)}"}, **opciones)
        return self._resultado(r)

    def _enviar(self, metodo: str, ruta: str, cabeceras: dict, **opciones) -> httpx.Response:
        try:
            return self._http.request(metodo, ruta, headers={**cabeceras, "X-Correlation-ID": correlacion_actual()},
                                      **opciones)
        except httpx.HTTPError:
            raise _no_disponible() from None

    @staticmethod
    def _codigo(r: httpx.Response) -> str | None:
        try:
            error = r.json().get("error")
        except (ValueError, AttributeError):
            return None
        return error.get("code") if isinstance(error, dict) else None

    @staticmethod
    def _resultado(r: httpx.Response) -> Any:
        if r.is_success:
            return r.json()
        try:
            cuerpo = r.json()
        except ValueError:
            cuerpo = None
        error = cuerpo.get("error") if isinstance(cuerpo, dict) else None
        if r.status_code >= 500 or not isinstance(error, dict):
            if r.status_code == 422:
                # Validación de FastAPI en COREDB: Seguridad valida antes, así que no debería pasar.
                raise ErrorSeg(422, "DATOS_RECHAZADOS_POR_COREDB", "COREDB rechazó los datos enviados.")
            raise _no_disponible()
        raise ErrorSeg(r.status_code, str(error.get("code", "ERROR_COREDB")), str(error.get("message", "")))
