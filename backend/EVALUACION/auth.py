"""Quién llama a Evaluación.

- Personal del banco y módulos: token de COREDB. Evaluación no conoce la clave que lo firma: lo
  valida COREDB en `GET /coredb/auth/me`, que devuelve el usuario, su rol y sus acciones del mapa
  versionado `COREDB/permisos.py`. El resultado se recuerda unos segundos para no consultar a
  COREDB en cada petición; desactivar un usuario surte efecto al vencer ese plazo.
- SOL: el token de servicio de CR-INT-02 (su SOL_BUS_TOKEN), solo en las rutas de recepción.

Permisos, con las acciones de COREDB: EVALUAR_CREDITO registra la situación financiera,
APROBAR_CREDITO decide y revoca, y VER_AUDITORIA consulta. Desembolso entra con su usuario de
servicio (rol SERVICIO, módulo DESEMBOLSO).
"""
from __future__ import annotations

import hashlib
import hmac
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .comun import ErrorEva, correlacion_actual

EVALUAR = "EVALUAR_CREDITO"
DECIDIR = "APROBAR_CREDITO"
AUDITAR = "VER_AUDITORIA"
LECTURA = (EVALUAR, DECIDIR, AUDITAR)
MODULO_DESEMBOLSO = "DESEMBOLSO"

_bearer = HTTPBearer(auto_error=False, scheme_name="Bearer")


@dataclass(frozen=True)
class Perfil:
    usuario: str
    rol: str
    modulo: str | None
    acciones: frozenset[str]

    @property
    def es_servicio(self) -> bool:
        return self.rol == "SERVICIO"

    def puede(self, *acciones: str) -> bool:
        return any(a in self.acciones for a in acciones)


class VerificadorCoreDb:
    """Valida tokens de COREDB con `GET /coredb/auth/me` y recuerda el perfil unos segundos."""

    MAXIMO_EN_MEMORIA = 2000

    def __init__(self, coredb_url: str, timeout: float = 3.0, recordar_seg: float = 30.0,
                 transporte: httpx.BaseTransport | None = None):
        self._http = httpx.Client(base_url=coredb_url, timeout=timeout, transport=transporte,
                                  follow_redirects=False, trust_env=False)
        self._recordar = recordar_seg
        self._memoria: dict[str, tuple[float, Perfil]] = {}
        self._candado = threading.Lock()

    def cerrar(self) -> None:
        self._http.close()

    def perfil(self, token: str) -> Perfil:
        clave = hashlib.sha256(token.encode()).hexdigest()
        ahora = time.monotonic()
        with self._candado:
            guardado = self._memoria.get(clave)
            if guardado and guardado[0] > ahora:
                return guardado[1]
        try:
            r = self._http.get("/coredb/auth/me", headers={"Authorization": f"Bearer {token}",
                                                           "X-Correlation-ID": correlacion_actual()})
        except httpx.HTTPError:
            raise ErrorEva(503, "COREDB_NO_DISPONIBLE", "No se pudo validar la sesión con COREDB.") from None
        if r.status_code == 401:
            raise ErrorEva(401, "SESION_INVALIDA", "La sesión no es válida o ya venció. Inicia sesión otra vez.")
        if r.status_code != 200:
            raise ErrorEva(503, "COREDB_NO_DISPONIBLE", "COREDB no pudo validar la sesión.")
        datos = r.json()
        perfil = Perfil(usuario=str(datos["username"]), rol=str(datos["rol"]), modulo=datos.get("modulo"),
                        acciones=frozenset(datos.get("acciones") or ()))
        with self._candado:
            if len(self._memoria) >= self.MAXIMO_EN_MEMORIA:
                self._memoria = {k: v for k, v in self._memoria.items() if v[0] > ahora}
            self._memoria[clave] = (ahora + self._recordar, perfil)
        return perfil


def _token(credenciales: HTTPAuthorizationCredentials | None) -> str:
    if credenciales is None or credenciales.scheme.lower() != "bearer" or not credenciales.credentials.strip():
        raise ErrorEva(401, "TOKEN_REQUERIDO", "Falta el encabezado Authorization: Bearer <token>.")
    return credenciales.credentials.strip()


def perfil_actual(request: Request, credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> Perfil:
    return request.app.state.ctx.verificador.perfil(_token(credenciales))


def _denegado() -> ErrorEva:
    return ErrorEva(403, "PERMISO_DENEGADO", "Tu usuario no tiene permiso para esta operación de Evaluación.")


def persona(*acciones: str) -> Callable[..., Perfil]:
    """Personal del banco con alguna de `acciones`. Un usuario de servicio no entra aquí."""

    def _dependencia(perfil: Perfil = Depends(perfil_actual)) -> Perfil:
        if perfil.es_servicio or not perfil.puede(*acciones):
            raise _denegado()
        return perfil

    return _dependencia


def lector_aprobaciones(perfil: Perfil = Depends(perfil_actual)) -> Perfil:
    """Desembolso (su usuario de servicio) o personal con permiso de lectura."""
    if perfil.es_servicio and perfil.modulo == MODULO_DESEMBOLSO:
        return perfil
    if not perfil.es_servicio and perfil.puede(*LECTURA):
        return perfil
    raise _denegado()


def servicio_desembolso(perfil: Perfil = Depends(perfil_actual)) -> Perfil:
    if perfil.es_servicio and perfil.modulo == MODULO_DESEMBOLSO:
        return perfil
    raise _denegado()


def canal_sol(request: Request, credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    """CR-INT-02: solo el token de servicio de SOL. Una sesión de persona no sirve aquí."""
    token = _token(credenciales)
    esperado = request.app.state.ctx.config.token_sol
    if not esperado or not hmac.compare_digest(token.encode(), esperado.encode()):
        raise ErrorEva(401, "TOKEN_INVALIDO", "Credencial de servicio no válida para CR-INT-02.")
    return "SOL"
