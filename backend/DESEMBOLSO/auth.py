"""Quién llama a Desembolso.

Personal del banco, con su token de COREDB. Desembolso no conoce la clave que lo firma: lo valida
COREDB en `GET /coredb/auth/me`, que devuelve el usuario, su rol y sus acciones del mapa
versionado `COREDB/permisos.py`. El resultado se recuerda unos segundos para no consultar a COREDB
en cada petición; desactivar un usuario surte efecto al vencer ese plazo, y COREDB lo vuelve a
comprobar en cada operación, porque Desembolso le reenvía el mismo token.

Permisos, con las acciones de COREDB: VER_CREDITO consulta órdenes y aprobaciones,
DESEMBOLSAR_CREDITO verifica el documento, prepara, valida, confirma y rechaza, y
GENERAR_REPORTES concilia. Un usuario de servicio no entra en las rutas del personal.
"""
from __future__ import annotations

import hashlib
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .comun import ErrorDes, correlacion_actual

VER = "VER_CREDITO"
DESEMBOLSAR = "DESEMBOLSAR_CREDITO"
CONCILIAR = "GENERAR_REPORTES"
# La verificación del documento en ventanilla (COREDB la exige para registrar la identidad).
VALIDAR_IDENTIDAD = "VALIDAR_IDENTIDAD"

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


@dataclass(frozen=True)
class Sesion:
    """La persona y su token, que se reenvía a COREDB."""
    perfil: Perfil
    token: str


class VerificadorCoreDb:
    """Valida tokens de COREDB con `GET /coredb/auth/me` y recuerda el perfil unos segundos."""

    MAXIMO_EN_MEMORIA = 2000

    def __init__(self, coredb_url: str, timeout: float = 5.0, recordar_seg: float = 30.0,
                 transporte: httpx.BaseTransport | None = None, bus_token: str = ""):
        # Credencial ante el Bus en cada llamada; el Bus no la reenvía a COREDB.
        self._http = httpx.Client(base_url=coredb_url, timeout=timeout, transport=transporte,
                                  follow_redirects=False, trust_env=False,
                                  headers={"X-Bus-Token": bus_token} if bus_token else None)
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
            raise ErrorDes(503, "COREDB_NO_DISPONIBLE", "No se pudo validar la sesión con COREDB.") from None
        if r.status_code == 401:
            raise ErrorDes(401, "SESION_INVALIDA", "La sesión no es válida o ya venció. Inicia sesión otra vez.")
        if r.status_code != 200:
            raise ErrorDes(503, "COREDB_NO_DISPONIBLE", "COREDB no pudo validar la sesión.")
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
        raise ErrorDes(401, "TOKEN_REQUERIDO", "Falta el encabezado Authorization: Bearer <token>.")
    return credenciales.credentials.strip()


def persona(*acciones: str) -> Callable[..., Sesion]:
    """Personal del banco con alguna de `acciones`. Un usuario de servicio no entra aquí."""

    def _dependencia(request: Request,
                     credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> Sesion:
        token = _token(credenciales)
        perfil = request.app.state.ctx.verificador.perfil(token)
        if perfil.es_servicio or not perfil.puede(*acciones):
            raise ErrorDes(403, "PERMISO_DENEGADO", "Tu usuario no tiene permiso para esta operación de Desembolso.")
        return Sesion(perfil, token)

    return _dependencia

