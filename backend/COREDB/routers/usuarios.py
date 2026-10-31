import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from COREDB.auth import Actor, actor_actual
from COREDB.database import db_session
from COREDB.services import usuarios

router = APIRouter(prefix="/coredb/usuarios", tags=["usuarios"])

Rol = Literal["ADMINISTRADOR", "ASESOR", "ANALISTA", "OPERADOR", "AUDITOR"]


class UsuarioCrear(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    nombre: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8)
    rol: Rol
    id_empleado: uuid.UUID | None = None


class RolAsignar(BaseModel):
    rol: Rol


class UsuarioRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: uuid.UUID
    username: str
    nombre: str
    rol: str
    id_empleado: uuid.UUID | None
    activo: bool
    creado_en: datetime


@router.get("", response_model=list[UsuarioRespuesta])
def listar(
    limite: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(db_session),
):
    return usuarios.listar(db, limite=limite, offset=offset)


@router.get("/{id_usuario}", response_model=UsuarioRespuesta)
def ver(id_usuario: uuid.UUID, db: Session = Depends(db_session)):
    return usuarios.obtener(db, id_usuario)


@router.post("", response_model=UsuarioRespuesta, status_code=status.HTTP_201_CREATED)
def crear(
    datos: UsuarioCrear,
    db: Session = Depends(db_session),
    actor: Actor = Depends(actor_actual),
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
    actor: Actor = Depends(actor_actual),
):
    return usuarios.asignar_rol(db, id_usuario, rol=datos.rol, actor=actor.usuario)
