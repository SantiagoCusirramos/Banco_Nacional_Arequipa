import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from COREDB.auth import Actor, requiere_permiso
from COREDB.database import db_session
from COREDB.services import usuarios

router = APIRouter(prefix="/coredb/usuarios", tags=["usuarios"])

Rol = Literal["ADMINISTRADOR", "ASESOR", "ANALISTA", "OPERADOR", "AUDITOR"]
Username = Field(min_length=3, max_length=40)


class UsuarioCrear(BaseModel):
    username: str = Username
    nombre: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8)
    rol: Rol
    id_empleado: uuid.UUID | None = None


class ServicioCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    modulo: str = Field(min_length=1, max_length=40)
    username: str = Username
    nombre: str = Field(min_length=1, max_length=100)


class RolAsignar(BaseModel):
    rol: Rol


class EstadoCambiar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activo: bool


class UsuarioRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: uuid.UUID
    username: str
    nombre: str
    rol: str
    modulo: str | None
    id_empleado: uuid.UUID | None
    activo: bool
    creado_en: datetime


class CredencialRespuesta(BaseModel):
    usuario: UsuarioRespuesta
    secreto: str = Field(description="Se muestra solo en esta respuesta; la base guarda su hash.")


def _no_guardar(respuesta: Response) -> None:
    respuesta.headers["Cache-Control"] = "no-store"


@router.get("", response_model=list[UsuarioRespuesta],
            dependencies=[Depends(requiere_permiso("CREAR_USUARIO"))])
def listar(
    limite: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(db_session),
):
    return usuarios.listar(db, limite=limite, offset=offset)


@router.get("/{id_usuario}", response_model=UsuarioRespuesta,
            dependencies=[Depends(requiere_permiso("CREAR_USUARIO"))])
def ver(id_usuario: uuid.UUID, db: Session = Depends(db_session)):
    return usuarios.obtener(db, id_usuario)


@router.post("", response_model=UsuarioRespuesta, status_code=status.HTTP_201_CREATED)
def crear(
    datos: UsuarioCrear,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("CREAR_USUARIO")),
):
    return usuarios.crear(
        db,
        username=datos.username,
        nombre=datos.nombre,
        password=datos.password,
        rol=datos.rol,
        id_empleado=datos.id_empleado,
        actor=actor.usuario,
    )


@router.post("/{id_usuario}/rol", response_model=UsuarioRespuesta)
def asignar_rol(
    id_usuario: uuid.UUID,
    datos: RolAsignar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("ASIGNAR_ROLES")),
):
    return usuarios.asignar_rol(db, id_usuario, rol=datos.rol, actor=actor.usuario)


@router.post("/{id_usuario}/estado", response_model=UsuarioRespuesta)
def cambiar_estado(
    id_usuario: uuid.UUID,
    datos: EstadoCambiar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("CREAR_USUARIO")),
):
    """Desactivar corta el acceso en la siguiente petición, aunque el token no haya vencido."""
    return usuarios.cambiar_estado(db, id_usuario, activo=datos.activo, actor=actor.usuario)


@router.post("/servicios", response_model=CredencialRespuesta, status_code=status.HTTP_201_CREATED)
def crear_servicio(
    datos: ServicioCrear,
    respuesta: Response,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("CREAR_USUARIO")),
):
    """Crea el usuario con el que un módulo (p. ej. CLIENTES) inicia sesión. El secreto se
    entrega solo aquí: hay que guardarlo en el almacén de secretos del módulo."""
    _no_guardar(respuesta)
    usuario, secreto = usuarios.crear_servicio(
        db, modulo=datos.modulo, username=datos.username, nombre=datos.nombre, actor=actor.usuario
    )
    return CredencialRespuesta(usuario=UsuarioRespuesta.model_validate(usuario), secreto=secreto)


@router.post("/{id_usuario}/credencial", response_model=CredencialRespuesta)
def renovar_credencial(
    id_usuario: uuid.UUID,
    respuesta: Response,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("CREAR_USUARIO")),
):
    """Entrega un secreto nuevo, una sola vez; el anterior deja de servir. Solo usuarios de
    servicio (422 BNA-USUARIO-SERVICIO para una persona)."""
    _no_guardar(respuesta)
    usuario, secreto = usuarios.renovar_credencial(db, id_usuario, actor=actor.usuario)
    return CredencialRespuesta(usuario=UsuarioRespuesta.model_validate(usuario), secreto=secreto)
