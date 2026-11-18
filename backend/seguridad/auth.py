"""Quién llama a Seguridad: personal del banco con su token de COREDB.

Seguridad no tiene usuarios ni contraseñas propios ni conoce la clave que firma los tokens: los
valida COREDB en `GET /coredb/auth/me`, que devuelve el usuario, su rol y sus acciones del mapa
versionado `COREDB/permisos.py`. El perfil se recuerda unos segundos; COREDB vuelve a comprobar
a la persona en cada operación, porque Seguridad le reenvía el token (X-Persona-Token).

Permisos, con las acciones de COREDB: REGISTRAR_MOVIMIENTO evalúa una operación; VER_AUDITORIA
lee y verifica la bitácora y lee los incidentes; GESTIONAR_INCIDENTES los abre y avanza;
BLOQUEAR_TARJETA desbloquea una tarjeta (solo por aquí). Un usuario de servicio no entra.
"""
from __future__ import annotations

import hashlib
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .comun import ErrorSeg
from .coredb import ClienteCoreDb

EVALUAR = "REGISTRAR_MOVIMIENTO"
VER_AUDITORIA = "VER_AUDITORIA"
INCIDENTES = "GESTIONAR_INCIDENTES"
DESBLOQUEAR = "BLOQUEAR_TARJETA"

_bearer = HTTPBearer(auto_error=False, scheme_name="Bearer")


@dataclass(frozen=True)
class Perfil:
    usuario: str
    rol: str
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


class Verificador:
    """Valida tokens con `GET /coredb/auth/me` y recuerda el perfil unos segundos."""

    MAXIMO_EN_MEMORIA = 2000

    def __init__(self, coredb: ClienteCoreDb, recordar_seg: float = 30.0):
        self._coredb = coredb
        self._recordar = recordar_seg
        self._memoria: dict[str, tuple[float, Perfil]] = {}
        self._candado = threading.Lock()

    def perfil(self, token: str) -> Perfil:
        clave = hashlib.sha256(token.encode()).hexdigest()
        ahora = time.monotonic()
        with self._candado:
            guardado = self._memoria.get(clave)
            if guardado and guardado[0] > ahora:
                return guardado[1]
        try:
            datos = self._coredb.como_persona(token, "GET", "/coredb/auth/me")
        except ErrorSeg as exc:
            if exc.estado == 401:
                raise ErrorSeg(401, "SESION_INVALIDA", "La sesión no es válida o ya venció. Inicia sesión otra vez.") from None
            raise
        perfil = Perfil(usuario=str(datos["username"]), rol=str(datos["rol"]),
                        acciones=frozenset(datos.get("acciones") or ()))
        with self._candado:
            if len(self._memoria) >= self.MAXIMO_EN_MEMORIA:
                self._memoria = {k: v for k, v in self._memoria.items() if v[0] > ahora}
            self._memoria[clave] = (ahora + self._recordar, perfil)
        return perfil


def token_de(credenciales: HTTPAuthorizationCredentials | None) -> str:
    if credenciales is None or credenciales.scheme.lower() != "bearer" or not credenciales.credentials.strip():
        raise ErrorSeg(401, "TOKEN_REQUERIDO", "Falta el encabezado Authorization: Bearer <token>.")
    return credenciales.credentials.strip()


def persona(*acciones: str) -> Callable[..., Sesion]:
    """Personal del banco con alguna de `acciones`. Un usuario de servicio no entra."""

    def _dependencia(request: Request,
                     credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> Sesion:
        token = token_de(credenciales)
        perfil = request.app.state.ctx.verificador.perfil(token)
        if perfil.es_servicio or not perfil.puede(*acciones):
            raise ErrorSeg(403, "PERMISO_DENEGADO", "Tu usuario no tiene permiso para esta operación de Seguridad.")
        return Sesion(perfil, token)

    return _dependencia
