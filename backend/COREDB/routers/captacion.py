"""Captación: el expediente del prospecto antes de ser cliente (clientes.*_captacion).

Lo usa el módulo CAPTACION con el token del asesor (lo que hace una persona) o con su
usuario de servicio (ligar el cliente que registró y leer las referencias de SOL). Leer
exige VER_CLIENTE; escribir, CREAR_CLIENTE (ASESOR, ADMINISTRADOR y SERVICIO:CLIENTES).
El cliente HABILITADO lo sigue registrando solo el módulo Clientes (`POST /coredb/clientes`,
punto R-01); aquí se liga al caso. Cada escritura devuelve el expediente completo.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from COREDB.auth import Actor, requiere_permiso
from COREDB.correlacion import correlacion
from COREDB.database import db_session
from COREDB.services import captacion

router = APIRouter(prefix="/coredb/captacion", tags=["captación"])

IdCaso = Annotated[uuid.UUID, Path(description="Identificador del caso")]
EstadoCaso = Literal["INICIADO", "EN_VALIDACION", "OBSERVADO", "APROBADO", "HABILITADO", "RECHAZADO", "REVOCADO"]
ERRORES = {401: {"description": "Sin token o token no válido"}, 403: {"description": "PERMISO_DENEGADO"}}
ERRORES_CASO = {**ERRORES, 404: {"description": "CASO_NO_ENCONTRADO"},
                409: {"description": "CASO_CERRADO"}}
lector = requiere_permiso("VER_CLIENTE")
escritor = requiere_permiso("CREAR_CLIENTE")


class _Peticion(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ── Modelos ─────────────────────────────────────────────────────────────────


class SolicitanteCaptacionRegistrar(_Peticion):
    tipo_documento: str = Field(min_length=1, max_length=10)
    numero_documento: str = Field(min_length=1, max_length=12)
    nombres: str = Field(min_length=1, max_length=100)
    apellido_paterno: str = Field(min_length=1, max_length=100)
    apellido_materno: str | None = Field(default=None, max_length=100)
    celular: str = Field(pattern=r"^9\d{8}$", description="Nueve dígitos, empieza con 9. Sin +51.")
    correo: str = Field(max_length=150, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    @field_validator("tipo_documento", "numero_documento")
    @classmethod
    def _mayusculas(cls, valor: str) -> str:
        return valor.upper()


class SolicitantesCaptacionBuscar(_Peticion):
    """La búsqueda va en el cuerpo: un documento en la consulta quedaría en los registros de acceso."""
    documento: str | None = Field(default=None, max_length=12, description="Parte del número de documento.")
    texto: str | None = Field(default=None, max_length=100, description="Documento, nombres o apellidos.")
    con_cliente: bool = Field(default=False, description="Solo los que ya tienen un cliente ligado.")
    limite: int = Field(default=50, ge=1, le=200)


class SolicitanteCaptacion(BaseModel):
    id_solicitante: str
    tipo_documento: str
    numero_documento: str
    nombres: str
    apellido_paterno: str
    apellido_materno: str | None
    celular: str
    correo: str
    cod_cliente: str | None
    creado_por: str
    fecha_registro: datetime


class SolicitanteCaptacionRegistrado(BaseModel):
    solicitante: SolicitanteCaptacion
    duplicado: bool


class CasoCaptacionAbrir(_Peticion):
    id_solicitante: uuid.UUID
    canal: Literal["AGENCIA", "WEB", "MOVIL", "AGENTE", "CAMPANA"]
    id_agencia: str | None = Field(default=None, min_length=1, max_length=10)
    producto_interes: str | None = Field(default=None, max_length=60)


class CasoCaptacion(BaseModel):
    id_caso: str
    id_solicitante: str
    canal: str
    id_agencia: str | None
    producto_interes: str | None
    estado: str
    observacion: str | None
    motivo_cierre: str | None
    cod_cliente: str | None
    cliente_nuevo: bool | None
    id_verificacion_captacion: str | None = Field(description="La del cliente ligado, en COREDB.")
    estado_cliente: str | None = Field(description="El estado vigente del cliente ligado.")
    fecha_verificacion: date | None
    vigente_hasta: date | None
    creado_por: str
    fecha_apertura: datetime
    fecha_cierre: datetime | None
    faltantes: list[str] = Field(description="Lo que falta para habilitar; vacío si está listo o cerrado.")


class CasoCaptacionEnBandeja(CasoCaptacion):
    solicitante: SolicitanteCaptacion


class ConsentimientoCaptacion(BaseModel):
    tipo: str
    aceptado: bool
    medio: str
    version: str | None
    registrado_por: str
    fecha: datetime


class OtpCaptacion(BaseModel):
    """Sin el hash del código."""

    id_otp: str
    canal: str
    estado: str
    intentos_fallidos: int
    fecha_emision: datetime
    fecha_expiracion: datetime


class ValidacionCaptacion(BaseModel):
    tipo: str
    resultado: str
    proveedor: str
    detalle: str | None
    registrado_por: str
    fecha: datetime


class ConsultaRiesgoCaptacion(BaseModel):
    central: str
    calificacion: str
    deuda_total: Decimal
    entidades: int
    dias_mora: int
    fuente: str
    registrado_por: str
    fecha: datetime


class PerfilRiesgoCaptacion(BaseModel):
    puntaje: int
    calificacion: str
    observacion: str | None
    registrado_por: str
    fecha: datetime
    vigente: bool = Field(description="Falso si hay una consulta a una central posterior al perfil.")


class ExpedienteCaptacion(CasoCaptacion):
    solicitante: SolicitanteCaptacion
    consentimientos: list[ConsentimientoCaptacion]
    otps: list[OtpCaptacion]
    validaciones: list[ValidacionCaptacion]
    consultas: list[ConsultaRiesgoCaptacion]
    perfil: PerfilRiesgoCaptacion | None = Field(description="El último perfil calculado.")
    listo_para_habilitar: bool


class ConsentimientoCaptacionItem(_Peticion):
    tipo: Literal["TRATAMIENTO_DATOS", "CONSULTA_BUROS", "TERMINOS", "BIOMETRIA"]
    aceptado: bool
    medio: Literal["DIGITAL", "FISICO", "BIOMETRICO"] = "DIGITAL"


class ConsentimientosCaptacion(_Peticion):
    consentimientos: list[ConsentimientoCaptacionItem] = Field(min_length=1, max_length=4)
    version_terminos: str | None = Field(default=None, min_length=1, max_length=10,
                                         description="Obligatoria si viene TERMINOS.")


Hmac = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$", description="HMAC-SHA256 en hexadecimal, calculado por CAPTACION.")]


class OtpCaptacionEmitir(_Peticion):
    id_otp: uuid.UUID
    canal: Literal["SMS", "EMAIL"]
    codigo_hmac: Hmac


class OtpCaptacionVerificar(_Peticion):
    codigo_hmac: Hmac


class OtpCaptacionVerificado(BaseModel):
    estado_codigo: Literal["USADO", "PENDIENTE", "BLOQUEADO", "EXPIRADO"]
    intentos_restantes: int
    estado: str = Field(description="El estado del caso después de verificar.")


class ValidacionCaptacionRegistrar(_Peticion):
    tipo: Literal["RENIEC", "LISTAS_NEGRAS", "PEP", "BIOMETRIA"]
    resultado: Literal["APROBADO", "OBSERVADO", "RECHAZADO"]
    proveedor: str = Field(min_length=1, max_length=40, description="SIMULADO, el del proveedor o MANUAL.")
    detalle: str | None = Field(default=None, max_length=200)


class ConsultaRiesgoCaptacionRegistrar(_Peticion):
    central: Literal["SBS", "INFOCORP", "SENTINEL", "EQUIFAX"]
    calificacion: Literal["NORMAL", "CPP", "DEFICIENTE", "DUDOSO", "PERDIDA"]
    deuda_total: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    entidades: int = Field(ge=0, le=99)
    dias_mora: int = Field(ge=0, le=9999)
    fuente: Literal["SIMULADO", "MANUAL"]


class PerfilCaptacionRegistrar(_Peticion):
    puntaje: int = Field(ge=0, le=1000)
    calificacion: Literal["BAJO", "MEDIO", "ALTO", "MUY_ALTO"]
    observacion: str | None = Field(default=None, max_length=200)


class EstadoCaptacionCambiar(_Peticion):
    accion: Literal["OBSERVAR", "LEVANTAR_OBSERVACION", "RECHAZAR", "REVOCAR"]
    motivo: str = Field(min_length=3, max_length=255)


class ClienteCaptacionLigar(_Peticion):
    cod_cliente: str = Field(min_length=1, max_length=12, pattern=r"^[A-Za-z0-9]+$")
    cliente_nuevo: bool


class HabilitacionCaptacion(_Peticion):
    vigencia_dias: int = Field(ge=1, le=365, description="Días de vigencia de la referencia desde hoy (Lima).")


# ── Solicitantes ────────────────────────────────────────────────────────────


@router.post("/solicitantes", response_model=SolicitanteCaptacionRegistrado, status_code=status.HTTP_201_CREATED,
             responses={**ERRORES, 200: {"description": "El documento ya estaba registrado (duplicado)"},
                        422: {"description": "DOCUMENTO_INVALIDO o DATOS_INVALIDOS"}})
def registrar_solicitante(
    datos: SolicitanteCaptacionRegistrar,
    response: Response,
    db: Session = Depends(db_session),
    actor: Actor = Depends(escritor),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """Registra al prospecto. Un documento ya registrado devuelve el mismo solicitante, sin
    cambiar sus datos, con 200 y `duplicado: true`."""
    solicitante, duplicado = captacion.registrar_solicitante(
        db, datos.model_dump(), correlation_id=correlation_id, actor=actor.usuario)
    if duplicado:
        response.status_code = status.HTTP_200_OK
    return {"solicitante": solicitante, "duplicado": duplicado}


@router.post("/solicitantes/busqueda", response_model=list[SolicitanteCaptacion], responses=ERRORES,
             dependencies=[Depends(lector)])
def buscar_solicitantes(datos: SolicitantesCaptacionBuscar, db: Session = Depends(db_session)):
    return captacion.buscar_solicitantes(db, documento=datos.documento, texto=datos.texto,
                                         con_cliente=datos.con_cliente, limite=datos.limite)


@router.get("/solicitantes/{id_solicitante}", response_model=SolicitanteCaptacion,
            responses={**ERRORES, 404: {"description": "SOLICITANTE_NO_ENCONTRADO"}},
            dependencies=[Depends(lector)])
def ver_solicitante(id_solicitante: uuid.UUID, db: Session = Depends(db_session)):
    return captacion.ver_solicitante(db, id_solicitante)


# ── Casos ───────────────────────────────────────────────────────────────────


@router.post("/casos", response_model=CasoCaptacion, status_code=status.HTTP_201_CREATED,
             responses={**ERRORES, 404: {"description": "SOLICITANTE_NO_ENCONTRADO"},
                        409: {"description": "CASO_ABIERTO"}, 422: {"description": "AGENCIA_NO_ENCONTRADA"}})
def abrir_caso(
    datos: CasoCaptacionAbrir,
    db: Session = Depends(db_session),
    actor: Actor = Depends(escritor),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """Abre el caso INICIADO. Un solicitante tiene a lo sumo un caso abierto."""
    return captacion.abrir_caso(db, datos.model_dump(), correlation_id=correlation_id, actor=actor.usuario)


@router.get("/casos", response_model=list[CasoCaptacionEnBandeja], responses=ERRORES, dependencies=[Depends(lector)])
def listar_casos(
    estado: EstadoCaso | None = None,
    id_solicitante: uuid.UUID | None = None,
    cod_cliente: str | None = Query(default=None, max_length=12),
    limite: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(db_session),
):
    """La bandeja, del caso más reciente al más antiguo, con los datos del solicitante."""
    return captacion.listar_casos(db, estado=estado, id_solicitante=id_solicitante, cod_cliente=cod_cliente,
                                  limite=limite, offset=offset)


@router.get("/casos/{id_caso}", response_model=ExpedienteCaptacion,
            responses={**ERRORES, 404: {"description": "CASO_NO_ENCONTRADO"}}, dependencies=[Depends(lector)])
def ver_expediente(id_caso: IdCaso, db: Session = Depends(db_session)):
    """El expediente completo y lo que falta para habilitarlo."""
    return captacion.expediente(db, id_caso)


@router.post("/casos/{id_caso}/consentimientos", response_model=ExpedienteCaptacion,
             status_code=status.HTTP_201_CREATED, responses={**ERRORES_CASO, 422: {"description": "DATOS_INVALIDOS"}})
def registrar_consentimientos(
    id_caso: IdCaso,
    datos: ConsentimientosCaptacion,
    db: Session = Depends(db_session),
    actor: Actor = Depends(escritor),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """Vale el último consentimiento de cada tipo; la versión se guarda solo en TERMINOS."""
    captacion.registrar_consentimientos(db, id_caso, [c.model_dump() for c in datos.consentimientos],
                                        datos.version_terminos, correlation_id=correlation_id, actor=actor.usuario)
    return captacion.expediente(db, id_caso)


@router.post("/casos/{id_caso}/otps", response_model=OtpCaptacion, status_code=status.HTTP_201_CREATED,
             responses={**ERRORES_CASO, 422: {"description": "CONSENTIMIENTO_REQUERIDO"}})
def emitir_otp(
    id_caso: IdCaso,
    datos: OtpCaptacionEmitir,
    db: Session = Depends(db_session),
    actor: Actor = Depends(escritor),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """Guarda un OTP nuevo (el HMAC del código, que CAPTACION calcula con su clave y el
    `id_otp`) y vence el pendiente anterior del mismo canal. Vencimiento e intentos salen de
    clientes.tipo_contacto. Exige el consentimiento TRATAMIENTO_DATOS."""
    return captacion.emitir_otp(db, id_caso, id_otp=datos.id_otp, canal=datos.canal, codigo_hmac=datos.codigo_hmac,
                                correlation_id=correlation_id, actor=actor.usuario)


@router.post("/casos/{id_caso}/otps/{id_otp}/verificacion", response_model=OtpCaptacionVerificado,
             responses={**ERRORES_CASO, 404: {"description": "CASO_NO_ENCONTRADO u OTP_NO_ENCONTRADO"}})
def verificar_otp(
    id_caso: IdCaso,
    id_otp: uuid.UUID,
    datos: OtpCaptacionVerificar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(escritor),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """Compara el HMAC con el del OTP pendiente. El correcto deja el código USADO y verifica
    el celular (SMS) o el correo (EMAIL); el errado suma un intento y el último lo bloquea;
    vencido queda EXPIRADO. Un código ya usado, vencido o bloqueado es OTP_NO_ENCONTRADO."""
    return captacion.verificar_otp(db, id_caso, id_otp, datos.codigo_hmac, correlation_id=correlation_id,
                                   actor=actor.usuario)


@router.post("/casos/{id_caso}/validaciones", response_model=ExpedienteCaptacion,
             status_code=status.HTTP_201_CREATED,
             responses={**ERRORES_CASO, 422: {"description": "CONSENTIMIENTO_REQUERIDO o DATOS_INVALIDOS"}})
def registrar_validacion(
    id_caso: IdCaso,
    datos: ValidacionCaptacionRegistrar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(escritor),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """RENIEC, listas, PEP o biometría (con su consentimiento), del proveedor o manual: la
    última de cada tipo vale. Una RECHAZADA cierra el caso; una OBSERVADA lo detiene."""
    captacion.registrar_validacion(db, id_caso, datos.model_dump(), correlation_id=correlation_id,
                                   actor=actor.usuario)
    return captacion.expediente(db, id_caso)


@router.post("/casos/{id_caso}/consultas-riesgo", response_model=ExpedienteCaptacion,
             status_code=status.HTTP_201_CREATED, responses={**ERRORES_CASO, 422: {"description": "CONSENTIMIENTO_REQUERIDO"}})
def registrar_consulta(
    id_caso: IdCaso,
    datos: ConsultaRiesgoCaptacionRegistrar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(escritor),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """La respuesta de una central de riesgo. Exige CONSULTA_BUROS."""
    captacion.registrar_consulta(db, id_caso, datos.model_dump(), correlation_id=correlation_id, actor=actor.usuario)
    return captacion.expediente(db, id_caso)


@router.post("/casos/{id_caso}/perfil", response_model=ExpedienteCaptacion, status_code=status.HTTP_201_CREATED,
             responses={**ERRORES_CASO, 422: {"description": "SIN_CONSULTA"}})
def registrar_perfil(
    id_caso: IdCaso,
    datos: PerfilCaptacionRegistrar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(escritor),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """El perfil de 0 a 1000 que calcula CAPTACION. Exige una consulta; MUY_ALTO rechaza el caso."""
    captacion.registrar_perfil(db, id_caso, datos.model_dump(), correlation_id=correlation_id, actor=actor.usuario)
    return captacion.expediente(db, id_caso)


@router.post("/casos/{id_caso}/estado", response_model=ExpedienteCaptacion,
             responses={**ERRORES_CASO, 409: {"description": "CASO_CERRADO o ESTADO_INVALIDO"}})
def cambiar_estado(
    id_caso: IdCaso,
    datos: EstadoCaptacionCambiar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(escritor),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """Observar o levantar la observación de un caso abierto, rechazarlo, o revocar uno HABILITADO."""
    captacion.cambiar_estado(db, id_caso, datos.accion, datos.motivo, correlation_id=correlation_id,
                             actor=actor.usuario)
    return captacion.expediente(db, id_caso)


@router.post("/casos/{id_caso}/cliente", response_model=ExpedienteCaptacion,
             responses={**ERRORES_CASO, 404: {"description": "CASO_NO_ENCONTRADO o CLIENTE_NO_ENCONTRADO"},
                        409: {"description": "CASO_CERRADO o CASO_CON_OTRO_CLIENTE"},
                        422: {"description": "CASO_NO_LISTO, CLIENTE_NO_COINCIDE o CLIENTE_NO_ACTIVO"}})
def ligar_cliente(
    id_caso: IdCaso,
    datos: ClienteCaptacionLigar,
    db: Session = Depends(db_session),
    actor: Actor = Depends(escritor),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """Liga al caso APROBADO el cliente ACTIVO con el documento del solicitante, que quien
    verificó la identidad registró o encontró antes. Ligar otra vez el mismo no cambia nada."""
    captacion.vincular_cliente(db, id_caso, datos.cod_cliente, datos.cliente_nuevo, correlation_id=correlation_id,
                               actor=actor.usuario)
    return captacion.expediente(db, id_caso)


@router.post("/casos/{id_caso}/habilitacion", response_model=ExpedienteCaptacion,
             responses={**ERRORES_CASO, 422: {"description": "CASO_NO_LISTO o CLIENTE_NO_ACTIVO"}})
def habilitar(
    id_caso: IdCaso,
    datos: HabilitacionCaptacion,
    db: Session = Depends(db_session),
    actor: Actor = Depends(escritor),
    correlation_id: uuid.UUID = Depends(correlacion),
):
    """HABILITADO con el cliente ligado, vigente `vigencia_dias` desde hoy (Lima). Las
    verificaciones de contacto quedan también en el cliente. Repetirlo no cambia nada."""
    captacion.habilitar(db, id_caso, datos.vigencia_dias, correlation_id=correlation_id, actor=actor.usuario)
    return captacion.expediente(db, id_caso)
