"""Empleados del banco. Solo el ADMINISTRADOR, con el permiso propio REGISTRAR_EMPLEADO."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from COREDB.auth import Actor, requiere_permiso
from COREDB.database import db_session
from COREDB.permisos import REGISTRAR_EMPLEADO
from COREDB.services import empleados

router = APIRouter(prefix="/coredb/empleados", tags=["empleados"])

# El cargo se guarda en mayúsculas, como lo normaliza core.registrar_empleado.
Cargo = Annotated[str, Field(min_length=1, max_length=30), AfterValidator(str.upper)]


class EmpleadoRegistrar(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    codigo_empleado: str = Field(min_length=1, max_length=20)
    nombre_completo: str = Field(min_length=1, max_length=100)
    cargo: Cargo
    id_agencia: str | None = Field(default=None, min_length=1, max_length=10)
    id_usuario: uuid.UUID | None = Field(
        default=None, description="Una persona sin empleado; se liga al empleado nuevo.")


class EmpleadoRegistrado(BaseModel):
    """Sin el nombre: no hace falta repetirlo y es un dato personal."""

    id_empleado: uuid.UUID
    codigo_empleado: str
    cargo: str
    id_agencia: str | None
    id_usuario: uuid.UUID | None
    activo: bool


@router.post(
    "", response_model=EmpleadoRegistrado, status_code=status.HTTP_201_CREATED,
    responses={401: {"description": "Sin token o token no válido"},
               403: {"description": "PERMISO_DENEGADO"},
               404: {"description": "USUARIO_NO_ENCONTRADO"},
               409: {"description": "EMPLEADO_DUPLICADO o USUARIO_NO_ADMITIDO (de servicio o ya ligado)"},
               422: {"description": "AGENCIA_NO_ENCONTRADA o datos inválidos"}},
)
def registrar(
    datos: EmpleadoRegistrar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso(REGISTRAR_EMPLEADO)),
):
    """Registra un empleado activo y, si se indica, lo liga a un usuario. Para que decida
    créditos: usuario ANALISTA ligado y `POST /coredb/creditos/analistas` con este
    `id_empleado`."""
    id_empleado = empleados.registrar(
        db,
        codigo_empleado=datos.codigo_empleado,
        nombre_completo=datos.nombre_completo,
        cargo=datos.cargo,
        id_agencia=datos.id_agencia,
        id_usuario=datos.id_usuario,
        actor=actor.usuario,
    )
    return EmpleadoRegistrado(id_empleado=id_empleado, codigo_empleado=datos.codigo_empleado, cargo=datos.cargo,
                              id_agencia=datos.id_agencia, id_usuario=datos.id_usuario, activo=True)
