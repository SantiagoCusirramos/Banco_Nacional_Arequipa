"""Dependencias de FastAPI: servicios, usuario autenticado, permisos e idempotencia."""
from __future__ import annotations

import re
from collections.abc import Callable

from fastapi import Depends, Header, Request

from ..core.errores import ErrorNegocio
from ..core.seguridad import Usuario

PATRON_CLAVE = re.compile(r"^[0-9a-fA-F-]{36}$")


def servicios(request: Request):
    return request.app.state.servicios


def usuario_actual(request: Request, authorization: str | None = Header(default=None)) -> Usuario:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ErrorNegocio(401, "NO_AUTENTICADO", "Se requiere el token de sesión de COREDB")
    return request.app.state.servicios.modulos.sesiones.verificar(authorization[7:].strip())


def requiere(permiso: str | None = None, roles: set[str] | None = None) -> Callable[..., Usuario]:
    def dependencia(request: Request, usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if (permiso and not usuario.tiene(permiso)) or (roles and usuario.rol not in roles):
            ip = request.client.host if request.client else None
            request.app.state.servicios.auditor.denegado(usuario, f"{request.method} {request.url.path}", ip)
            raise ErrorNegocio(403, "PERMISO_DENEGADO", "No tiene permiso para esta operación",
                               {"requerido": permiso or sorted(roles or [])})
        return usuario
    return dependencia


def clave_idempotencia(x_idempotency_key: str | None = Header(default=None)) -> str:
    if not x_idempotency_key:
        raise ErrorNegocio(400, "IDEMPOTENCIA_REQUERIDA", "Falta la cabecera X-Idempotency-Key")
    if not PATRON_CLAVE.match(x_idempotency_key):
        raise ErrorNegocio(400, "IDEMPOTENCIA_INVALIDA", "X-Idempotency-Key debe ser un UUID")
    return x_idempotency_key.lower()
