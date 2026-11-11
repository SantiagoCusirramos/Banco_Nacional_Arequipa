"""Rutas de clientes para el módulo Clientes y el personal. Ver CONTRATO_CLIENTES.md."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from COREDB import permisos
from COREDB.auth import Actor, requiere_permiso
from COREDB.correlacion import correlacion
from COREDB.database import db_session
from COREDB.errores import ErrorCoreDb
from COREDB.services import clientes

router = APIRouter(prefix="/coredb/clientes", tags=["clientes"])

CodCliente = Annotated[str, Path(min_length=1, max_length=12, pattern=r"^[A-Za-z0-9]+$")]
ERRORES_COMUNES = {401: {"description": "Sin token o token no válido"},
                   403: {"description": "PERMISO_DENEGADO"}}
NO_ENCONTRADO = {404: {"description": "CLIENTE_NO_ENCONTRADO"}}


class _Peticion(BaseModel):
    # Un campo desconocido se rechaza y los textos deben ser cadenas JSON.
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class _Documento(_Peticion):
    tipo_documento: str = Field(min_length=1, max_length=10)
    numero_documento: str = Field(min_length=1, max_length=12)

    @field_validator("tipo_documento", "numero_documento")
    @classmethod
    def _mayusculas(cls, valor: str) -> str:
        return valor.upper()


class ClienteRegistrar(_Documento):
    nombres: str = Field(min_length=1, max_length=100)
    apellido_paterno: str = Field(min_length=1, max_length=100)
    apellido_materno: str | None = Field(default=None, max_length=100)
    correo: str = Field(max_length=150, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    celular: str = Field(pattern=r"^9\d{8}$", description="Nueve dígitos, empieza con 9. Sin +51.")
    version_contrato: str = Field(min_length=1, max_length=10)
    estado_habilitante: Literal["HABILITADO", "OBSERVADO"]

    @field_validator("correo")
    @classmethod
    def _minusculas(cls, valor: str) -> str:
        return valor.lower()


class ClienteRegistrado(BaseModel):
    cod_cliente: str
    estado_cliente: str
    estado_habilitante: str
    id_verificacion_captacion: str


class ClienteRespuesta(BaseModel):
    """El cliente, sin datos biométricos."""

    cod_cliente: str
    tipo_documento: str
    numero_documento: str
    nombres: str
    apellido_paterno: str
    apellido_materno: str | None
    correo: str
    celular: str
    estado_cliente: str
    permite_operar: bool
    version_contrato: str
    id_verificacion_captacion: str
    estado_habilitante: str
    fecha_verificacion: str


class ClienteConEstadoAnterior(ClienteRespuesta):
    estado_anterior: str


class DocumentoVerificar(_Documento):
    identidad_verificada: bool
    motivo: str | None = Field(default=None, max_length=60)


class DocumentoVerificado(BaseModel):
    id_validacion: int
    resultado: Literal["APROBADO", "RECHAZADO"]
    motivo: str | None
    cliente: ClienteRespuesta | None


class ValidacionRegistrar(_Peticion):
    tipo_validacion: Literal["HUELLA", "FACIAL", "CELULAR", "CORREO"]
    resultado: Literal["APROBADO", "RECHAZADO"]
    motivo: str | None = Field(default=None, max_length=60)


class ValidacionRegistrada(BaseModel):
    id_validacion: int


class EstadoCambiar(_Peticion):
    estado: str = Field(min_length=1, max_length=25)
    motivo: str = Field(min_length=1, max_length=255)

    @field_validator("estado")
    @classmethod
    def _mayusculas(cls, valor: str) -> str:
        return valor.upper()


@router.post("", response_model=ClienteRegistrado, status_code=status.HTTP_201_CREATED,
             responses={**ERRORES_COMUNES,
                        403: {"description": "PERMISO_DENEGADO o HABILITACION_NO_PERMITIDA"},
                        409: {"description": "CLIENTE_DUPLICADO, CORREO_DUPLICADO o CELULAR_DUPLICADO"}})
def registrar(
    datos: ClienteRegistrar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("CREAR_CLIENTE")),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """Registra un cliente. El código lo genera el CORE. HABILITADO da un cliente ACTIVO y
    OBSERVADO da un cliente OBSERVADO. Solo el usuario de servicio del módulo Clientes
    puede registrar HABILITADO.

    Los 409 revelan que un documento, correo o celular ya pertenece a un cliente: el
    módulo Clientes no debe reenviarlos al usuario final antes de verificar su identidad."""
    if datos.estado_habilitante == "HABILITADO" and not permisos.puede_registrar_habilitado(actor):
        raise ErrorCoreDb(
            "HABILITACION_NO_PERMITIDA",
            "Solo el módulo Clientes registra un cliente HABILITADO; registre OBSERVADO.", 403,
        )
    return clientes.registrar(
        db, **datos.model_dump(), correlation_id=correlation_id, actor=actor.usuario
    )


@router.post("/validaciones/documento", response_model=DocumentoVerificado,
             status_code=status.HTTP_201_CREATED, responses=ERRORES_COMUNES)
def verificar_documento(
    datos: DocumentoVerificar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("VALIDAR_IDENTIDAD")),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """Consulta por documento (RF-CLI-001), después de que quien llama verificó la identidad.
    Responde siempre 201, nunca 404. Sin identidad verificada la respuesta es la misma
    para un cliente y para quien no lo es, salvo `id_validacion`. Con identidad verificada
    aprueba solo a un cliente ACTIVO. Cada llamada queda registrada."""
    return clientes.verificar_documento(
        db, **datos.model_dump(), correlation_id=correlation_id, actor=actor.usuario
    )


@router.post("/{cod_cliente}/validaciones", response_model=ValidacionRegistrada,
             status_code=status.HTTP_201_CREATED, responses={**ERRORES_COMUNES, **NO_ENCONTRADO})
def registrar_validacion(
    cod_cliente: CodCliente,
    datos: ValidacionRegistrar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("VALIDAR_IDENTIDAD")),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """Registra el veredicto de una validación de huella, rostro, celular o correo. La de
    documento se registra con `/coredb/clientes/validaciones/documento`."""
    id_validacion = clientes.registrar_validacion(
        db, cod_cliente=cod_cliente, **datos.model_dump(), correlation_id=correlation_id,
        actor=actor.usuario,
    )
    return ValidacionRegistrada(id_validacion=id_validacion)


@router.get("/{cod_cliente}", response_model=ClienteRespuesta,
            dependencies=[Depends(requiere_permiso("VER_CLIENTE"))],
            responses={**ERRORES_COMUNES, **NO_ENCONTRADO})
def ver(cod_cliente: CodCliente, db: Session = Depends(db_session)):
    return clientes.consultar(db, cod_cliente)


@router.post("/{cod_cliente}/estado", response_model=ClienteConEstadoAnterior,
             responses={**ERRORES_COMUNES, **NO_ENCONTRADO})
def cambiar_estado(
    cod_cliente: CodCliente,
    datos: EstadoCambiar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("MODIFICAR_CLIENTE")),
):
    """Cambia el estado de un cliente; el motivo queda en la bitácora.

    BLOQUEADO o SUSPENDIDO bloquean sus tarjetas activas y por activar, y BAJA las cancela
    todas. Reactivar al cliente no desbloquea sus tarjetas: eso lo hace Seguridad. BAJA es
    final y solo la fija una persona. Pedir el estado que ya tiene no cambia nada."""
    if datos.estado == "BAJA" and not permisos.puede_dar_de_baja(actor):
        raise ErrorCoreDb("PERMISO_DENEGADO", "La baja de un cliente la fija una persona.", 403)
    return clientes.cambiar_estado(
        db, cod_cliente=cod_cliente, estado=datos.estado, motivo=datos.motivo, actor=actor.usuario
    )
