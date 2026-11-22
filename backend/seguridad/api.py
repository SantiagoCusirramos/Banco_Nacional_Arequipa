"""Rutas de Seguridad (módulo 9). Sin base propia: todo se guarda en la base integrada por
COREDB, a través del Bus, con el usuario de servicio svc-seguridad y por la persona que llama.

Todas las rutas /seguridad/* exigen X-Correlation-ID; las protegidas, el token de COREDB de la
persona (Authorization: Bearer).
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Path, Query, Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import auditoria
from .auth import DESBLOQUEAR, EVALUAR, INCIDENTES, VER_AUDITORIA, Sesion, _bearer, persona, token_de
from .comun import PATRON_CORRELACION, ErrorSeg

VERSION = "1.0.0"
SEGUNDOS_DESAFIO = 120  # core.fn_segundos_desafio()
# Objetivos de atención y resolución en minutos: propuestos, no medidos; reloj continuo.
SLA = {"P1": (15, 120), "P2": (30, 240), "P3": (120, 1440), "P4": (480, 4320)}


def correlacion(x_correlation_id: str = Header(default="", alias="X-Correlation-ID")) -> str:
    if not PATRON_CORRELACION.fullmatch(x_correlation_id):
        raise ErrorSeg(400, "CORRELACION_REQUERIDA", "X-Correlation-ID obligatorio: 1 a 100 caracteres seguros.")
    return x_correlation_id


router = APIRouter(prefix="/seguridad", tags=["Módulo 9 · Seguridad"], dependencies=[Depends(correlacion)])


def _ctx(request: Request):
    return request.app.state.ctx


def hmac_codigo(clave: str, id_desafio: uuid.UUID, codigo: str) -> str:
    """El HMAC que guarda la base; separado por dominio del de los sellos."""
    return hmac.new(clave.encode(), f"desafio-v1:{id_desafio}:{codigo}".encode(), hashlib.sha256).hexdigest()


# --------------------------------------------------------------------- estado y sesión
@router.get("/estado")
def estado(request: Request):
    ctx = _ctx(request)
    return {"modulo": "SEGURIDAD", "version": VERSION, "base_propia": False,
            "persistencia": "COREDB por el Bus de Servicios", "coredb_disponible": ctx.coredb.salud(),
            "sellado_cada_seg": ctx.config.sellado_seg or None,
            "pendientes": ["segundo factor por canal independiente", "RENIEC", "HSM", "SIEM", "SMS"]}


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=1, max_length=256)


@router.post("/auth/login")
def login(datos: Login, request: Request):
    """El login de COREDB, tal cual: Seguridad no tiene usuarios propios. Cinco fallos seguidos
    bloquean a la persona 15 minutos (bd-v1.12)."""
    return _ctx(request).coredb.como_persona(None, "POST", "/coredb/auth/login", json=datos.model_dump())


@router.get("/auth/me")
def me(request: Request, credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer)):
    perfil = _ctx(request).verificador.perfil(token_de(credenciales))
    return {"username": perfil.usuario, "rol": perfil.rol, "acciones": sorted(perfil.acciones)}


# --------------------------------------------------------------------- evaluación de operaciones
Canal = Literal["ATM", "HB", "BD", "VEN", "AGE"]


class Operacion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    uuid_operacion: uuid.UUID = Field(description="Lo genera quien llama; repetirlo devuelve la misma decisión.")
    num_cuenta: str = Field(min_length=1, max_length=20)
    canal: Canal
    monto: Annotated[Decimal, Field(gt=0, max_digits=15, decimal_places=2)]
    id_desafio: uuid.UUID | None = None
    codigo: str | None = Field(default=None, pattern=r"^\d{6}$")

    @model_validator(mode="after")
    def _desafio_completo(self):
        if (self.id_desafio is None) != (self.codigo is None):
            raise ValueError("id_desafio y codigo van juntos")
        return self


@router.post("/operaciones/evaluar")
def evaluar(datos: Operacion, request: Request, quien: Sesion = Depends(persona(EVALUAR))):
    """Decisión de seguridad, no movimiento contable: compara el monto con el tope real del canal y
    el consumo real del día de la cuenta (COREDB). Sobre el 80 % del tope pide un desafío de 120 s;
    tres códigos incorrectos lo agotan. El código se muestra por el mismo canal: es una simulación,
    no un segundo factor."""
    ctx = _ctx(request)
    cuerpo = {"uuid_operacion": str(datos.uuid_operacion), "num_cuenta": datos.num_cuenta,
              "canal": datos.canal, "monto": f"{datos.monto:.2f}"}
    if datos.id_desafio is not None:
        cuerpo |= {"id_desafio": str(datos.id_desafio),
                   "hmac_codigo": hmac_codigo(ctx.config.clave, datos.id_desafio, datos.codigo)}
    resultado = ctx.coredb.por_persona(quien.token, "POST", "/coredb/seguridad/evaluaciones", json=cuerpo)
    if resultado["decision"] != "DESAFIO_REQUERIDO":
        return {**resultado, "efecto_financiero": False}
    id_desafio, codigo = uuid.uuid4(), f"{secrets.randbelow(1_000_000):06d}"
    creado = ctx.coredb.por_persona(quien.token, "POST", "/coredb/seguridad/desafios", json={
        **{k: cuerpo[k] for k in ("uuid_operacion", "num_cuenta", "canal", "monto")},
        "id_desafio": str(id_desafio), "hmac_codigo": hmac_codigo(ctx.config.clave, id_desafio, codigo)})
    return {**resultado, "id_desafio": str(id_desafio), "vence_en": creado["vence_en"],
            "vence_en_seg": SEGUNDOS_DESAFIO, "codigo_demo": codigo,
            "aviso": "SIMULACIÓN: el código viaja por el mismo canal; falta un proveedor de segundo factor.",
            "efecto_financiero": False}


# --------------------------------------------------------------------- bitácora
@router.get("/auditoria")
def eventos(request: Request, quien: Sesion = Depends(persona(VER_AUDITORIA))):
    """Los últimos 100 eventos de la bitácora general de COREDB."""
    return _ctx(request).coredb.como_persona(quien.token, "GET", "/coredb/auditoria", params={"limite": 100})


@router.post("/auditoria/sellos")
def sellar(request: Request, quien: Sesion = Depends(persona(VER_AUDITORIA))):
    """Sella ahora los eventos que siguen al último sello (sin esperar a la tarea periódica). Sella
    solo los que tienen la antigüedad mínima configurada."""
    ctx = _ctx(request)
    sello = auditoria.sellar(ctx.coredb, ctx.config.clave, ctx.config.sellado_antiguedad_seg)
    return {"sellado": sello is not None, "sello": sello}


@router.get("/auditoria/verificar")
def verificar(request: Request, quien: Sesion = Depends(persona(VER_AUDITORIA))):
    ctx = _ctx(request)
    return auditoria.verificar(ctx.coredb, ctx.config.clave)


# --------------------------------------------------------------------- incidentes
class Incidente(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prioridad: Literal["P1", "P2", "P3", "P4"]
    titulo: str = Field(min_length=8, max_length=200)


class Avance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estado: Literal["EN_PROGRESO", "RESUELTO", "CERRADO"]
    resolucion: str | None = Field(default=None, min_length=8, max_length=500)


def _con_sla(incidente: dict) -> dict:
    atencion, resolucion = SLA[incidente["prioridad"]]
    return {**incidente, "sla_atencion_min": atencion, "sla_resolucion_min": resolucion,
            "sla": "objetivos propuestos; reloj continuo, sin calendario hábil"}


@router.get("/incidentes")
def incidentes(request: Request, quien: Sesion = Depends(persona(VER_AUDITORIA, INCIDENTES))):
    lista = _ctx(request).coredb.por_persona(quien.token, "GET", "/coredb/seguridad/incidentes")
    return [_con_sla(i) for i in lista]


@router.post("/incidentes", status_code=201)
def abrir_incidente(datos: Incidente, request: Request, quien: Sesion = Depends(persona(INCIDENTES))):
    return _con_sla(_ctx(request).coredb.por_persona(quien.token, "POST", "/coredb/seguridad/incidentes",
                                                     json=datos.model_dump()))


@router.patch("/incidentes/{id_incidente}")
def avanzar_incidente(datos: Avance, request: Request, id_incidente: uuid.UUID = Path(),
                      quien: Sesion = Depends(persona(INCIDENTES))):
    """ABIERTO → EN_PROGRESO → RESUELTO (con resolución) → CERRADO, sin saltos."""
    return _con_sla(_ctx(request).coredb.por_persona(
        quien.token, "POST", f"/coredb/seguridad/incidentes/{id_incidente}/estado",
        json=datos.model_dump(exclude_none=True)))


# --------------------------------------------------------------------- tarjetas
class Desbloqueo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: str = Field(min_length=3, max_length=255)


BLOQUEADAS = ("BLOQUEADA", "RETENIDA")


def _con_numero(tarjeta: dict) -> dict:
    """Solo el BIN y los últimos cuatro: el PAN nunca llega a Seguridad."""
    return {**tarjeta, "numero_enmascarado": f"{tarjeta['bin']}******{tarjeta['ultimos4']}"}


@router.get("/tarjetas")
def tarjetas_de_un_cliente(request: Request,
                           cod_cliente: str = Query(min_length=1, max_length=12, pattern=r"^[A-Za-z0-9]+$"),
                           quien: Sesion = Depends(persona(DESBLOQUEAR))):
    """Las tarjetas del cliente, para elegir la que se desbloquea. Lee con el token de la persona:
    COREDB comprueba además su VER_TARJETA."""
    lista = _ctx(request).coredb.como_persona(quien.token, "GET", "/coredb/tarjetas",
                                              params={"cod_cliente": cod_cliente})
    return [_con_numero(t) for t in lista]


@router.get("/tarjetas/{id_tarjeta}")
def ficha_de_tarjeta(request: Request, id_tarjeta: uuid.UUID = Path(),
                     quien: Sesion = Depends(persona(DESBLOQUEAR))):
    """La tarjeta, sus últimos cambios de estado y, si está bloqueada o retenida, el cambio que la
    dejó así (motivo, origen y fecha), para decidir el desbloqueo."""
    coredb = _ctx(request).coredb
    tarjeta = coredb.como_persona(quien.token, "GET", f"/coredb/tarjetas/{id_tarjeta}")
    historial = coredb.como_persona(quien.token, "GET", f"/coredb/tarjetas/{id_tarjeta}/historial",
                                    params={"limite": 5})
    bloqueada = tarjeta["estado_tarjeta"] in BLOQUEADAS
    bloqueo = historial[0] if bloqueada and historial and historial[0]["estado_nuevo"] in BLOQUEADAS else None
    return {**_con_numero(tarjeta), "desbloqueable": bloqueada, "bloqueo": bloqueo, "historial": historial}


@router.post("/tarjetas/{id_tarjeta}/desbloqueo")
def desbloquear_tarjeta(datos: Desbloqueo, request: Request, id_tarjeta: uuid.UUID = Path(),
                        quien: Sesion = Depends(persona(DESBLOQUEAR))):
    """Devuelve a ACTIVA una tarjeta BLOQUEADA o RETENIDA. Es el único camino: COREDB lo ejecuta con
    la cuenta bna_seguridad de la base y registra a la persona como actor (origen SEGURIDAD). La
    respuesta trae `cambio`, el registro del historial que dejó (id, fecha, motivo, estado anterior,
    actor). Repetirlo da 409 TARJETA_NO_BLOQUEADA: no desbloquea dos veces."""
    return _ctx(request).coredb.por_persona(quien.token, "POST", f"/coredb/tarjetas/{id_tarjeta}/desbloqueo",
                                            json=datos.model_dump())
