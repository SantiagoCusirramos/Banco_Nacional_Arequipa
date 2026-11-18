"""Billetera Digital «Chaski» (bd-v1.9): /coredb/billetera/*.

Dos clases de rutas:

- Del banco: afiliar a un cliente (le fija su PIN y su cuenta) y afiliar un comercio. Con
  el token de una persona con AFILIAR_BILLETERA o REGISTRAR_COMERCIO.
- Del cliente: las llama el módulo BILLETERA con su token de servicio (OPERAR_BILLETERA) y
  el token del cliente en X-Cliente-Token, que entrega POST /coredb/billetera/acceso tras
  validar celular y PIN. El cliente sale de ese token, nunca del cuerpo: rol CLIENTE,
  limitado a su billetera.

El celular va siempre en el cuerpo, nunca en la ruta ni en la consulta (quedan en los
registros de acceso), y ninguna respuesta lo devuelve. Las operaciones de dinero exigen
X-Idempotency-Key: repetirla devuelve la misma operación (`repetido`) sin segundo débito.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from COREDB import tokens
from COREDB.auth import Actor, ClienteBilletera, cliente_actual, requiere_permiso
from COREDB.database import db_session
from COREDB.errores import ErrorAutenticacion, ErrorCoreDb
from COREDB.services import billetera

router = APIRouter(prefix="/coredb/billetera", tags=["billetera"])

Monto = Annotated[Decimal, Field(gt=0, max_digits=15, decimal_places=2)]
Celular = Annotated[str, Field(pattern=r"^9[0-9]{8}$", description="El celular de clientes.cliente.")]
Pin = Annotated[str, Field(pattern=r"^[0-9]{6}$")]
Limite = Annotated[int, Query(ge=1, le=100)]
LlaveIdempotencia = Annotated[uuid.UUID, Header(alias="X-Idempotency-Key")]


def _correlacion(valor: str | None) -> uuid.UUID | None:
    try:
        return uuid.UUID(valor) if valor else None
    except ValueError:
        return None


# --- Modelos ------------------------------------------------------------------------

class AccesoPeticion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    celular: Celular
    pin: Pin


class ClienteSesion(BaseModel):
    cod_cliente: str
    nombre_corto: str


class AccesoRespuesta(BaseModel):
    access_token: str = Field(description="Va en X-Cliente-Token; no sirve como Authorization.")
    token_type: str = "bearer"
    expires_in: int
    cliente: ClienteSesion


class PinPeticion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pin: Pin


class PinRespuesta(BaseModel):
    valido: bool


class AfiliacionPeticion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cod_cliente: str = Field(min_length=1, max_length=12)
    num_cuenta: str = Field(min_length=1, max_length=20)
    pin: Pin


class AfiliacionRespuesta(BaseModel):
    cod_cliente: str
    num_cuenta: str
    estado: str
    nueva: bool = Field(description="False si ya estaba afiliado: cambió el PIN o la cuenta y quedó ACTIVA.")


class ComercioPeticion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ruc: str = Field(pattern=r"^(10|15|17|20)[0-9]{9}$")
    razon_social: str = Field(min_length=1, max_length=150)
    num_cuenta: str = Field(min_length=1, max_length=20)


class ComercioRespuesta(BaseModel):
    id_comercio: uuid.UUID
    ruc: str
    razon_social: str
    num_cuenta: str
    estado: str
    id_qr: uuid.UUID | None


class ComercioPublico(BaseModel):
    id_comercio: uuid.UUID
    razon_social: str
    id_qr: uuid.UUID


class PerfilRespuesta(BaseModel):
    cod_cliente: str
    nombre_corto: str
    num_cuenta: str
    estado: str
    saldo_disponible: Decimal
    tope_diario: Decimal | None
    consumido_hoy: Decimal
    disponible_hoy: Decimal | None
    notificaciones_sin_leer: int
    solicitudes_pendientes: int


class MovimientoRespuesta(BaseModel):
    uuid_transaccion: uuid.UUID
    num_cuenta: str
    tipo_operacion: str
    naturaleza: str
    monto: Decimal
    moneda: str
    glosa: str
    id_canal: str | None
    estado_transaccion: str
    fecha_hora: datetime


class OperacionRespuesta(BaseModel):
    id_operacion: uuid.UUID
    tipo: str
    sentido: Literal["ENVIADA", "RECIBIDA"]
    nombre_origen: str
    nombre_destino: str
    monto: Decimal
    referencia: str | None
    id_qr: uuid.UUID | None
    id_solicitud: uuid.UUID | None
    uuid_debito: uuid.UUID
    fecha_hora: datetime


class OperacionCreada(OperacionRespuesta):
    repetido: bool = Field(description="True si la llave ya se había usado: es la misma operación.")


class ContactoPeticion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    celular: Celular


class ContactoRespuesta(BaseModel):
    nombre: str


class TransferenciaPeticion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    celular_destino: Celular
    monto: Monto
    referencia: str | None = Field(default=None, max_length=100)


class QrPeticion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monto: Monto | None = Field(default=None, description="Sin monto: el QR estático del cliente.")
    minutos: int | None = Field(default=None, ge=1, le=60, description="Vigencia del QR dinámico (15).")


class QrRespuesta(BaseModel):
    id_qr: uuid.UUID
    tipo: str
    monto: Decimal | None
    estado: str
    beneficiario: str
    es_comercio: bool
    fecha_expiracion: datetime | None


class PagoQrPeticion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monto: Monto | None = Field(default=None, description="Obligatorio en un QR estático.")


class SolicitudPeticion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    celular: Celular
    monto: Monto
    concepto: str | None = Field(default=None, max_length=100)


class SolicitudRespuesta(BaseModel):
    id_solicitud: uuid.UUID
    nombre_solicitante: str
    nombre_pagador: str
    monto: Decimal
    concepto: str | None
    estado: str
    fecha_solicitud: datetime
    fecha_vencimiento: datetime
    fecha_respuesta: datetime | None


class SolicitudesRespuesta(BaseModel):
    recibidas: list[SolicitudRespuesta]
    enviadas: list[SolicitudRespuesta]


class RespuestaPeticion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accion: Literal["ACEPTAR", "RECHAZAR", "CANCELAR"]


class RespuestaSolicitud(BaseModel):
    estado: str
    operacion: OperacionCreada | None


class NotificacionRespuesta(BaseModel):
    id_notificacion: int
    tipo: str
    mensaje: str
    leida: bool
    id_operacion: uuid.UUID | None
    id_solicitud: uuid.UUID | None
    fecha_hora: datetime


class MarcadasRespuesta(BaseModel):
    marcadas: int


def _creada(db: Session, id_operacion: uuid.UUID, cliente: ClienteBilletera, repetido: bool) -> OperacionCreada:
    return OperacionCreada(**billetera.operacion(db, id_operacion, cliente.cod_cliente), repetido=repetido)


# --- Rutas del banco ----------------------------------------------------------------

@router.post("/afiliaciones", response_model=AfiliacionRespuesta, status_code=status.HTTP_201_CREATED,
             responses={422: {"description": "BNA-BILLETERA-*, BNA-CLIENTE-NO-ACTIVO"}})
def afiliar(
    datos: AfiliacionPeticion,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("AFILIAR_BILLETERA")),
    x_correlation_id: str | None = Header(default=None),
):
    """Afilia a un cliente ACTIVO que ya existe (punto R-01: la billetera no crea clientes)
    con una cuenta individual en soles suya y su PIN de 6 dígitos. Repetirlo cambia el PIN o
    la cuenta y reactiva una billetera bloqueada."""
    nueva = billetera.afiliar(db, datos.cod_cliente, datos.num_cuenta, datos.pin, actor.usuario,
                              _correlacion(x_correlation_id))
    fila = billetera.afiliacion(db, datos.cod_cliente)
    return AfiliacionRespuesta(cod_cliente=fila["cod_cliente"], num_cuenta=fila["num_cuenta"],
                               estado=fila["estado"], nueva=nueva)


@router.post("/comercios", response_model=ComercioRespuesta, status_code=status.HTTP_201_CREATED,
             responses={409: {"description": "BNA-COMERCIO-DUPLICADO"}})
def registrar_comercio(
    datos: ComercioPeticion,
    db: Session = Depends(db_session),
    actor: Actor = Depends(requiere_permiso("REGISTRAR_COMERCIO")),
    x_correlation_id: str | None = Header(default=None),
):
    """Afilia un comercio con su cuenta de abono en soles y le genera su QR estático."""
    id_comercio = billetera.registrar_comercio(db, datos.ruc, datos.razon_social, datos.num_cuenta,
                                               actor.usuario, _correlacion(x_correlation_id))
    return billetera.comercio(db, id_comercio)


# --- Acceso del cliente -------------------------------------------------------------

@router.post("/acceso", response_model=AccesoRespuesta,
             responses={401: {"description": "CREDENCIALES_INVALIDAS: PIN equivocado o celular sin billetera"},
                        403: {"description": "BILLETERA_BLOQUEADA (tercer PIN equivocado), BILLETERA_NO_DISPONIBLE"}})
def acceso(
    datos: AccesoPeticion,
    db: Session = Depends(db_session),
    _servicio: Actor = Depends(requiere_permiso("OPERAR_BILLETERA")),
    x_correlation_id: str | None = Header(default=None),
):
    """Valida celular y PIN y entrega el token del cliente (rol CLIENTE). Un PIN equivocado y
    un celular sin billetera responden lo mismo; el tercer PIN equivocado bloquea la billetera
    hasta que el banco la afilie otra vez."""
    resultado = billetera.validar_acceso(db, datos.celular, datos.pin, _correlacion(x_correlation_id))
    if resultado.resultado == "BLOQUEADA":
        raise ErrorCoreDb("BILLETERA_BLOQUEADA", "La billetera está bloqueada. Acérquese al banco.", 403)
    if resultado.resultado == "CLIENTE_NO_OPERA":
        raise ErrorCoreDb("BILLETERA_NO_DISPONIBLE", "La billetera no está disponible.", 403)
    if resultado.resultado != "EXITOSO" or not resultado.cod_cliente:
        raise ErrorAutenticacion("CREDENCIALES_INVALIDAS", "Celular o PIN incorrectos.")
    token, vigencia = tokens.crear_token_cliente(cod_cliente=resultado.cod_cliente)
    fila = billetera.afiliacion(db, resultado.cod_cliente)
    return AccesoRespuesta(access_token=token, expires_in=vigencia,
                           cliente=ClienteSesion(cod_cliente=fila["cod_cliente"], nombre_corto=fila["nombre_corto"]))


# --- Rutas del cliente --------------------------------------------------------------

@router.post("/pin/verificacion", response_model=PinRespuesta,
             responses={401: {"description": "PIN_INCORRECTO"}, 403: {"description": "BILLETERA_BLOQUEADA"}})
def verificar_pin(
    datos: PinPeticion,
    cliente: ClienteBilletera = Depends(cliente_actual),
    db: Session = Depends(db_session),
    x_correlation_id: str | None = Header(default=None),
):
    """Confirma el PIN del cliente de la sesión antes de una operación (la app lo pide si el
    celular no tiene biometría). Cuenta intentos como el acceso: el tercero bloquea."""
    resultado = billetera.verificar_pin(db, cliente.cod_cliente, datos.pin, _correlacion(x_correlation_id))
    if resultado == "EXITOSO":
        return PinRespuesta(valido=True)
    if resultado == "BLOQUEADA":
        raise ErrorCoreDb("BILLETERA_BLOQUEADA", "La billetera está bloqueada. Acérquese al banco.", 403)
    raise ErrorAutenticacion("PIN_INCORRECTO", "PIN incorrecto.")


@router.get("/yo", response_model=PerfilRespuesta)
def yo(cliente: ClienteBilletera = Depends(cliente_actual), db: Session = Depends(db_session)):
    """Saldo disponible de la cuenta de la billetera, tope y consumo del día en el canal BD."""
    return billetera.perfil(db, cliente.cod_cliente)


@router.get("/movimientos", response_model=list[MovimientoRespuesta])
def movimientos(limite: Limite = 50, cliente: ClienteBilletera = Depends(cliente_actual),
                db: Session = Depends(db_session)):
    """Los movimientos de la cuenta de la billetera, del más reciente al más antiguo."""
    return billetera.movimientos(db, cliente.num_cuenta, limite)


@router.get("/operaciones", response_model=list[OperacionRespuesta])
def operaciones(limite: Limite = 50, cliente: ClienteBilletera = Depends(cliente_actual),
                db: Session = Depends(db_session)):
    """Envíos, pagos con QR y cobros del cliente, enviados o recibidos."""
    return billetera.operaciones(db, cliente.cod_cliente, limite)


@router.post("/contactos", response_model=ContactoRespuesta,
             responses={404: {"description": "CONTACTO_NO_ENCONTRADO"}})
def buscar_contacto(datos: ContactoPeticion, cliente: ClienteBilletera = Depends(cliente_actual),
                    db: Session = Depends(db_session)):
    """El nombre corto («Ana D.») de quien tiene billetera con ese celular, para confirmar un
    envío. No devuelve su código ni sus datos; el propio celular no se encuentra."""
    nombre = billetera.buscar_contacto(db, cliente.cod_cliente, datos.celular)
    if nombre is None:
        raise ErrorCoreDb("CONTACTO_NO_ENCONTRADO", "Ese número no tiene una billetera que pueda recibir.", 404)
    return ContactoRespuesta(nombre=nombre)


@router.post("/transferencias", response_model=OperacionCreada, status_code=status.HTTP_201_CREATED,
             responses={404: {"description": "BNA-BILLETERA-DESTINO"},
                        409: {"description": "BNA-IDEMPOTENCIA"},
                        422: {"description": "BNA-SALDO, RN-TOP-001, BNA-BILLETERA-PROPIA"}})
def transferir(
    datos: TransferenciaPeticion,
    llave_idempotencia: LlaveIdempotencia,
    cliente: ClienteBilletera = Depends(cliente_actual),
    db: Session = Depends(db_session),
    x_correlation_id: str | None = Header(default=None),
):
    """Envía dinero a otra billetera por su celular (P2P), por el canal BD."""
    id_operacion, repetido = billetera.transferir(
        db, cliente.cod_cliente, datos.celular_destino, datos.monto, datos.referencia, str(llave_idempotencia),
        cliente.actor, _correlacion(x_correlation_id))
    return _creada(db, id_operacion, cliente, repetido)


@router.post("/qr", response_model=QrRespuesta, status_code=status.HTTP_201_CREATED)
def crear_qr(datos: QrPeticion, cliente: ClienteBilletera = Depends(cliente_actual),
             db: Session = Depends(db_session)):
    """Sin monto, el QR estático del cliente (siempre el mismo); con monto, uno dinámico que
    se paga una vez y vence."""
    id_qr = billetera.crear_qr(db, cliente.cod_cliente, datos.monto, datos.minutos, cliente.actor)
    return billetera.qr(db, id_qr)


@router.get("/qr/{id_qr}", response_model=QrRespuesta)
def ver_qr(id_qr: uuid.UUID, _cliente: ClienteBilletera = Depends(cliente_actual),
           db: Session = Depends(db_session)):
    """Lo que el pagador ve antes de pagar: beneficiario (nombre corto o razón social), monto
    y vigencia. Sin la cuenta ni el código del beneficiario."""
    return billetera.qr(db, id_qr)


@router.post("/qr/{id_qr}/pagos", response_model=OperacionCreada, status_code=status.HTTP_201_CREATED,
             responses={404: {"description": "BNA-QR"},
                        409: {"description": "BNA-QR-NO-VIGENTE, BNA-IDEMPOTENCIA"},
                        422: {"description": "BNA-SALDO, RN-TOP-001, BNA-QR-MONTO, BNA-QR-PROPIO"}})
def pagar_qr(
    id_qr: uuid.UUID,
    datos: PagoQrPeticion,
    llave_idempotencia: LlaveIdempotencia,
    cliente: ClienteBilletera = Depends(cliente_actual),
    db: Session = Depends(db_session),
    x_correlation_id: str | None = Header(default=None),
):
    """Paga un QR de otra billetera o de un comercio, por el canal BD."""
    id_operacion, repetido = billetera.pagar_qr(db, cliente.cod_cliente, id_qr, datos.monto,
                                                str(llave_idempotencia), cliente.actor,
                                                _correlacion(x_correlation_id))
    return _creada(db, id_operacion, cliente, repetido)


@router.get("/comercios", response_model=list[ComercioPublico])
def comercios(_cliente: ClienteBilletera = Depends(cliente_actual), db: Session = Depends(db_session)):
    """Los comercios activos con su QR estático."""
    return billetera.comercios_activos(db)


@router.post("/solicitudes", response_model=SolicitudRespuesta, status_code=status.HTTP_201_CREATED,
             responses={404: {"description": "BNA-BILLETERA-DESTINO"}})
def crear_solicitud(datos: SolicitudPeticion, cliente: ClienteBilletera = Depends(cliente_actual),
                    db: Session = Depends(db_session)):
    """Pide dinero a otra billetera por su celular; vence a las 48 horas."""
    id_solicitud = billetera.crear_solicitud(db, cliente.cod_cliente, datos.celular, datos.monto, datos.concepto,
                                             cliente.actor)
    return billetera.solicitud(db, id_solicitud)


@router.get("/solicitudes", response_model=SolicitudesRespuesta)
def listar_solicitudes(limite: Limite = 30, cliente: ClienteBilletera = Depends(cliente_actual),
                       db: Session = Depends(db_session)):
    """Las recibidas (por pagar) y las enviadas, con su estado (VENCIDA a las 48 horas)."""
    return billetera.solicitudes(db, cliente.cod_cliente, limite)


@router.post("/solicitudes/{id_solicitud}/respuesta", response_model=RespuestaSolicitud,
             responses={403: {"description": "BNA-SOLICITUD-PERMISO"},
                        404: {"description": "BNA-SOLICITUD"},
                        409: {"description": "BNA-SOLICITUD-NO-PENDIENTE, BNA-IDEMPOTENCIA"},
                        422: {"description": "ACEPTAR sin X-Idempotency-Key, BNA-SALDO, RN-TOP-001"}})
def responder_solicitud(
    id_solicitud: uuid.UUID,
    datos: RespuestaPeticion,
    cliente: ClienteBilletera = Depends(cliente_actual),
    db: Session = Depends(db_session),
    llave_idempotencia: uuid.UUID | None = Header(default=None, alias="X-Idempotency-Key"),
):
    """ACEPTAR (paga; exige X-Idempotency-Key) o RECHAZAR, solo quien debe pagar; CANCELAR,
    solo quien la pidió."""
    if datos.accion == "ACEPTAR" and llave_idempotencia is None:
        raise ErrorCoreDb("LLAVE_REQUERIDA", "Aceptar una solicitud exige X-Idempotency-Key.", 422)
    llave = str(llave_idempotencia) if datos.accion == "ACEPTAR" else None
    estado, id_operacion, repetido = billetera.responder_solicitud(
        db, cliente.cod_cliente, id_solicitud, datos.accion, llave, cliente.actor)
    operacion = _creada(db, id_operacion, cliente, repetido) if id_operacion else None
    return RespuestaSolicitud(estado=estado, operacion=operacion)


@router.get("/notificaciones", response_model=list[NotificacionRespuesta])
def notificaciones(limite: Limite = 40, cliente: ClienteBilletera = Depends(cliente_actual),
                   db: Session = Depends(db_session)):
    return billetera.notificaciones(db, cliente.cod_cliente, limite)


@router.post("/notificaciones/leidas", response_model=MarcadasRespuesta)
def marcar_leidas(cliente: ClienteBilletera = Depends(cliente_actual), db: Session = Depends(db_session)):
    return MarcadasRespuesta(marcadas=billetera.marcar_leidas(db, cliente.cod_cliente))
