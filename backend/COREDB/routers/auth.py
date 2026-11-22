"""POST /coredb/auth/login, GET /coredb/auth/me y POST /coredb/auth/clave."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from COREDB import permisos, tokens
from COREDB.auth import Actor, usuario_de_la_sesion
from COREDB.database import db_session
from COREDB.errores import ErrorAutenticacion, ErrorCoreDb
from COREDB.models import Usuario
from COREDB.services import usuarios

router = APIRouter(prefix="/coredb/auth", tags=["autenticación"])

# Ninguno se distingue en la respuesta: ver CORE/AUTENTICACION.md.
FALLOS_DE_LOGIN = {
    "CREDENCIALES_INVALIDAS", "USUARIO_INACTIVO", "PASSWORD_NO_ADMITIDA", "BNA-USUARIO",
    "LOGIN_BLOQUEADO", "BNA-LOGIN-BLOQUEADO",
}


class LoginPeticion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=40)
    # Acota el trabajo de bcrypt; una contraseña más larga nunca es válida.
    password: str = Field(min_length=1, max_length=256)


class UsuarioSesion(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: uuid.UUID
    username: str
    nombre: str
    rol: str
    modulo: str | None
    activo: bool
    creado_en: datetime
    # bd-v1.17: con la contraseña inicial o renovada, solo puede cambiarla (POST /coredb/auth/clave).
    debe_cambiar_clave: bool


class TokenRespuesta(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    usuario: UsuarioSesion


class PerfilRespuesta(BaseModel):
    id_usuario: uuid.UUID
    username: str
    rol: str
    modulo: str | None
    acciones: list[str]
    debe_cambiar_clave: bool


class CambioClave(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actual: str = Field(min_length=1, max_length=256)
    nueva: str = Field(min_length=8, max_length=256)


class ClaveCambiada(BaseModel):
    debe_cambiar_clave: bool


def _credenciales_invalidas() -> ErrorAutenticacion:
    return ErrorAutenticacion("CREDENCIALES_INVALIDAS", "Usuario o contraseña incorrectos.")


def _correlacion(valor: str | None) -> uuid.UUID | None:
    # La envía el cliente: una que no sea un UUID no debe impedir el login.
    try:
        return uuid.UUID(valor) if valor else None
    except ValueError:
        return None


@router.post("/login", response_model=TokenRespuesta,
             responses={401: {"description": "CREDENCIALES_INVALIDAS, para todo fallo"}})
def login(
    datos: LoginPeticion,
    db: Session = Depends(db_session),
    x_correlation_id: str | None = Header(default=None),
):
    """Usuario inexistente, clave incorrecta, usuario inactivo, login bloqueado y contraseña
    no admitida responden el mismo 401. Un login exitoso queda en la bitácora (LOGIN); cada
    fallo de un usuario que existe, como LOGIN_FALLIDO. Cinco fallos seguidos bloquean a una
    persona 15 minutos (BLOQUEAR_LOGIN); los usuarios de servicio no se bloquean."""
    try:
        usuario = usuarios.autenticar(
            db, username=datos.username, password=datos.password,
            correlation_id=_correlacion(x_correlation_id),
        )
        token, vigencia = tokens.crear_token(
            id_usuario=usuario.id_usuario, username=usuario.username, rol=usuario.rol,
            modulo=usuario.modulo,
        )
        usuarios.registrar_login(db, usuario, _correlacion(x_correlation_id))
    except ErrorCoreDb as exc:
        if exc.code in FALLOS_DE_LOGIN:
            raise _credenciales_invalidas() from None
        raise
    return TokenRespuesta(
        access_token=token, expires_in=vigencia, usuario=UsuarioSesion.model_validate(usuario)
    )


@router.get("/me", response_model=PerfilRespuesta)
def me(usuario: Usuario = Depends(usuario_de_la_sesion)):
    """También con el cambio de contraseña pendiente: así la pantalla sabe que debe pedirlo."""
    actor = Actor(usuario.id_usuario, usuario.username, usuario.rol, usuario.modulo)
    return PerfilRespuesta(
        id_usuario=actor.id_usuario,
        username=actor.usuario,
        rol=actor.rol,
        modulo=actor.modulo,
        acciones=[] if usuario.debe_cambiar_clave else sorted(permisos.acciones_de(actor)),
        debe_cambiar_clave=usuario.debe_cambiar_clave,
    )


@router.post("/clave", response_model=ClaveCambiada,
             responses={422: {"description": "CLAVE_ACTUAL_INCORRECTA o CLAVE_NO_ADMITIDA"}})
def cambiar_clave(
    datos: CambioClave,
    usuario: Usuario = Depends(usuario_de_la_sesion),
    db: Session = Depends(db_session),
    x_correlation_id: str | None = Header(default=None),
):
    """La persona cambia su contraseña (obligatorio con la inicial o una renovada). La actual se
    comprueba como en el login: un fallo cuenta para el bloqueo tras cinco seguidos."""
    if usuario.rol == "SERVICIO":
        raise ErrorCoreDb("USUARIO_SERVICIO", "Un usuario de servicio renueva su secreto con /credencial.", 422)
    cambiado = usuarios.cambiar_clave_propia(
        db, usuario.id_usuario, actual=datos.actual, nueva=datos.nueva,
        correlation_id=_correlacion(x_correlation_id),
    )
    return ClaveCambiada(debe_cambiar_clave=cambiado.debe_cambiar_clave)
