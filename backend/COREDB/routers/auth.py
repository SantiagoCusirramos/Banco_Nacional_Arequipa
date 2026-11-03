"""POST /coredb/auth/login y GET /coredb/auth/me."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from COREDB import permisos, tokens
from COREDB.auth import Actor, actor_actual
from COREDB.database import db_session
from COREDB.errores import ErrorAutenticacion, ErrorCoreDb
from COREDB.services import usuarios

router = APIRouter(prefix="/coredb/auth", tags=["autenticación"])

# Ninguno se distingue en la respuesta: ver CORE/AUTENTICACION.md.
FALLOS_DE_LOGIN = {"CREDENCIALES_INVALIDAS", "USUARIO_INACTIVO", "PASSWORD_NO_ADMITIDA", "BNA-USUARIO"}


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
    """Usuario inexistente, clave incorrecta, usuario inactivo y contraseña no admitida
    responden el mismo 401. Un login exitoso queda en la bitácora (LOGIN)."""
    try:
        usuario = usuarios.autenticar(db, username=datos.username, password=datos.password)
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
def me(actor: Actor = Depends(actor_actual)):
    return PerfilRespuesta(
        id_usuario=actor.id_usuario,
        username=actor.usuario,
        rol=actor.rol,
        modulo=actor.modulo,
        acciones=sorted(permisos.acciones_de(actor)),
    )
