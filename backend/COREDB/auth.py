"""Autenticación y permisos de COREDB.

`actor_actual` exige `Authorization: Bearer <jwt>`, valida el token y vuelve a leer el
usuario: si se desactivó o cambió de rol, el efecto es inmediato aunque el token no
haya vencido. `requiere_permiso(accion)` agrega el permiso del mapa de permisos.py.
El actor de la auditoría y el origen de un cambio de tarjeta salen del token, nunca
de la petición. Sigue siendo una dependencia reemplazable:

    app.dependency_overrides[actor_actual] = otra_dependencia
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from COREDB import permisos, tokens
from COREDB.auth_tipos import Actor
from COREDB.database import db_session
from COREDB.errores import ErrorAutenticacion, ErrorCoreDb
from COREDB.models import Usuario

__all__ = ["Actor", "ClienteBilletera", "PersonaSeguridad", "actor_actual", "cliente_actual", "persona_por_seguridad",
           "requiere_permiso"]

_bearer = HTTPBearer(auto_error=False, scheme_name="JWT")


def actor_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(db_session),
) -> Actor:
    if credenciales is None or credenciales.scheme.lower() != "bearer":
        raise ErrorAutenticacion(
            "TOKEN_REQUERIDO", "Falta el encabezado Authorization: Bearer <token>."
        )
    claims = tokens.decodificar(credenciales.credentials)
    usuario = db.get(Usuario, uuid.UUID(claims["sub"]))
    if usuario is None or not usuario.activo:
        raise ErrorAutenticacion("USUARIO_NO_VIGENTE", "El usuario ya no está habilitado.")
    return Actor(usuario.id_usuario, usuario.username, usuario.rol, usuario.modulo)


def requiere_permiso(accion: str) -> Callable[..., Actor]:
    """Dependencia que exige `accion`. Uso: actor: Actor = Depends(requiere_permiso("X"))."""
    if accion not in permisos.ACCIONES:
        raise ValueError(f"Acción desconocida: {accion}")

    def _dependencia(actor: Actor = Depends(actor_actual)) -> Actor:
        if not permisos.puede(actor, accion):
            raise ErrorCoreDb(
                "PERMISO_DENEGADO", f"El rol {actor.clave_permisos} no puede ejecutar {accion}.", 403
            )
        return actor

    _dependencia.accion = accion  # lo lee la prueba que exige un permiso en cada escritura
    return _dependencia


@dataclass(frozen=True)
class ClienteBilletera:
    """El cliente de la Billetera Digital por el que actúa el módulo BILLETERA (bd-v1.9)."""

    cod_cliente: str
    num_cuenta: str
    servicio: Actor

    @property
    def actor(self) -> str:
        """El actor de la bitácora: el cliente, no el usuario de servicio."""
        return f"cliente:{self.cod_cliente}"


def cliente_actual(
    servicio: Actor = Depends(requiere_permiso("OPERAR_BILLETERA")),
    x_cliente_token: str | None = Header(default=None, alias="X-Cliente-Token"),
    db: Session = Depends(db_session),
) -> ClienteBilletera:
    """Exige el token del módulo (Authorization, con OPERAR_BILLETERA) y el del cliente
    (X-Cliente-Token, que emite POST /coredb/billetera/acceso). Vuelve a leer la afiliación:
    una billetera bloqueada o reafiliada a otra cuenta corta la sesión en la siguiente petición."""
    if not x_cliente_token:
        raise ErrorAutenticacion(
            "CLIENTE_TOKEN_REQUERIDO", "Falta el encabezado X-Cliente-Token del cliente."
        )
    claims = tokens.decodificar_cliente(x_cliente_token)
    fila = db.execute(
        text("SELECT num_cuenta, estado FROM billetera.v_afiliacion_api WHERE cod_cliente = :c"),
        {"c": claims["sub"]},
    ).first()
    if fila is None or fila.estado != "ACTIVA":
        raise ErrorAutenticacion("CLIENTE_NO_VIGENTE", "La billetera del cliente no está activa.")
    return ClienteBilletera(claims["sub"], fila.num_cuenta, servicio)


@dataclass(frozen=True)
class PersonaSeguridad:
    """La persona por la que actúa el módulo Seguridad (bd-v1.13) y el servicio que la trae."""

    persona: Actor
    servicio: Actor

    @property
    def actor(self) -> str:
        """El actor de la bitácora: la persona, no el usuario de servicio."""
        return self.persona.usuario


def persona_por_seguridad(*acciones: str) -> Callable[..., PersonaSeguridad]:
    """Exige el token del módulo Seguridad (Authorization, con OPERAR_SEGURIDAD) y el de la
    persona por la que actúa (X-Persona-Token), con alguna de `acciones`. Como en
    `actor_actual`, la persona se relee: desactivarla corta el acceso en la siguiente petición.
    Un usuario de servicio no puede ser la persona."""
    if not acciones or any(a not in permisos.ACCIONES for a in acciones):
        raise ValueError(f"Acciones desconocidas: {acciones}")

    def _dependencia(
        servicio: Actor = Depends(requiere_permiso(permisos.OPERAR_SEGURIDAD)),
        x_persona_token: str | None = Header(default=None, alias="X-Persona-Token"),
        db: Session = Depends(db_session),
    ) -> PersonaSeguridad:
        if not x_persona_token:
            raise ErrorAutenticacion(
                "PERSONA_TOKEN_REQUERIDO", "Falta el encabezado X-Persona-Token de la persona."
            )
        claims = tokens.decodificar(x_persona_token)
        usuario = db.get(Usuario, uuid.UUID(claims["sub"]))
        if usuario is None or not usuario.activo or usuario.rol == "SERVICIO":
            raise ErrorAutenticacion("PERSONA_NO_VIGENTE", "La persona ya no está habilitada.")
        persona = Actor(usuario.id_usuario, usuario.username, usuario.rol, usuario.modulo)
        if not any(permisos.puede(persona, accion) for accion in acciones):
            raise ErrorCoreDb(
                "PERMISO_DENEGADO", f"El rol {persona.rol} no puede ejecutar {' ni '.join(acciones)}.", 403
            )
        return PersonaSeguridad(persona, servicio)

    _dependencia.accion = permisos.OPERAR_SEGURIDAD  # lo lee la prueba de permisos de escritura
    return _dependencia
