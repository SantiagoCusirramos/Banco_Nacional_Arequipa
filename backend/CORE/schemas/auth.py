"""Schemas de autenticación (JWT)."""

from pydantic import Field

from CORE.schemas.common import CoreModel
from CORE.schemas.usuarios import UsuarioRespuesta


class LoginRequest(CoreModel):
    username: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=1, max_length=128)


class TokenRespuesta(CoreModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos de vigencia
    usuario: UsuarioRespuesta


class PerfilRespuesta(UsuarioRespuesta):
    acciones: list[str]  # permisos vigentes del rol (rbac.json)
