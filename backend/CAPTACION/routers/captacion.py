"""Rutas del personal: el expediente de captación, paso a paso. Base /api/v1/captacion."""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from CAPTACION import respuestas
from CAPTACION.core_client import CoreDb
from CAPTACION.database import db_session
from CAPTACION.dependencies import Actor, asesor, get_core, lector
from CAPTACION.schemas import (
    CasoAbrir, CasoEstado, CasoVista, ConsentimientoVista, Consentimientos, ConsultaPedir, ConsultaVista,
    OtpEnviar, OtpVerificar, PerfilVista, SolicitanteRegistrar, SolicitanteVista, ValidacionesEjecutar,
    ValidacionManual, ValidacionVista,
)
from CAPTACION.services import captacion as svc

router = APIRouter(prefix="/api/v1/captacion", tags=["Captación"])


def _solicitante(sol) -> dict:
    return SolicitanteVista.model_validate(sol).model_dump()


def _caso(caso) -> dict:
    return CasoVista.model_validate(caso).model_dump()


def _detalle(d: dict) -> dict:
    return {
        **_caso(d["caso"]),
        "solicitante": _solicitante(d["solicitante"]),
        "consentimientos": [ConsentimientoVista.model_validate(c).model_dump() for c in d["consentimientos"]],
        "validaciones": [ValidacionVista.model_validate(v).model_dump() for v in d["validaciones"]],
        "consultas": [ConsultaVista.model_validate(c).model_dump() for c in d["consultas"]],
        "perfil": PerfilVista.model_validate(d["perfil"]).model_dump() if d["perfil"] else None,
        "faltantes": d["faltantes"],
        "listo_para_habilitar": d["listo_para_habilitar"],
    }


# ── Solicitantes ────────────────────────────────────────────────────────────
@router.post("/solicitantes", status_code=201, summary="Registrar al solicitante (prospecto)")
def registrar_solicitante(request: Request, datos: SolicitanteRegistrar, db: Session = Depends(db_session),
                          actor: Actor = Depends(asesor)):
    """Si el documento ya se registró devuelve el mismo solicitante con `duplicado: true`."""
    sol, duplicado = svc.registrar_solicitante(db, datos.model_dump(), actor.usuario, actor.correlation_id)
    return respuestas.exito(request, {"solicitante": _solicitante(sol), "duplicado": duplicado},
                            200 if duplicado else 201,
                            "Solicitante ya registrado" if duplicado else "Solicitante registrado")


@router.get("/solicitantes", summary="Buscar solicitantes por documento")
def buscar_solicitantes(request: Request, documento: str | None = Query(default=None, max_length=12),
                        limite: int = Query(default=50, ge=1, le=200), db: Session = Depends(db_session),
                        _actor: Actor = Depends(lector)):
    return respuestas.exito(request, [_solicitante(s) for s in svc.buscar_solicitantes(db, documento, limite)])


@router.get("/solicitantes/{id_solicitante}", summary="Ver un solicitante")
def ver_solicitante(request: Request, id_solicitante: str, db: Session = Depends(db_session),
                    _actor: Actor = Depends(lector)):
    return respuestas.exito(request, _solicitante(svc.obtener_solicitante(db, id_solicitante)))


# ── Casos ───────────────────────────────────────────────────────────────────
@router.post("/casos", status_code=201, summary="Abrir el caso de captación")
def abrir_caso(request: Request, datos: CasoAbrir, db: Session = Depends(db_session),
               actor: Actor = Depends(asesor)):
    caso = svc.abrir_caso(db, datos.model_dump(), actor.usuario, actor.correlation_id)
    return respuestas.exito(request, _caso(caso), 201, "Caso abierto")


@router.get("/casos", summary="Bandeja de casos")
def listar_casos(request: Request, estado: str | None = Query(default=None, max_length=15),
                 limite: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0),
                 db: Session = Depends(db_session), _actor: Actor = Depends(lector)):
    filas = svc.listar_casos(db, estado, limite, offset)
    return respuestas.exito(request, [{**_caso(c), "solicitante": _solicitante(s)} for c, s in filas])


@router.get("/casos/{id_caso}", summary="Expediente completo y lo que falta para habilitar")
def ver_caso(request: Request, id_caso: str, db: Session = Depends(db_session), _actor: Actor = Depends(lector)):
    return respuestas.exito(request, _detalle(svc.detalle(db, id_caso)))


@router.post("/casos/{id_caso}/consentimientos", status_code=201, summary="Registrar consentimientos")
def consentimientos(request: Request, id_caso: str, datos: Consentimientos, db: Session = Depends(db_session),
                    actor: Actor = Depends(asesor)):
    items = [c.model_dump() for c in datos.consentimientos]
    creados = svc.registrar_consentimientos(db, id_caso, items, actor.usuario, actor.correlation_id)
    return respuestas.exito(request, [ConsentimientoVista.model_validate(c).model_dump() for c in creados], 201)


@router.post("/casos/{id_caso}/otp", status_code=201, summary="Enviar un código OTP al celular o al correo")
def enviar_otp(request: Request, id_caso: str, datos: OtpEnviar, db: Session = Depends(db_session),
               actor: Actor = Depends(asesor)):
    return respuestas.exito(request, svc.enviar_otp(db, id_caso, datos.canal, actor.usuario,
                                                    actor.correlation_id), 201, "Código enviado")


@router.post("/casos/{id_caso}/otp/verificar", summary="Verificar el código OTP")
def verificar_otp(request: Request, id_caso: str, datos: OtpVerificar, db: Session = Depends(db_session),
                  actor: Actor = Depends(asesor)):
    resultado = svc.verificar_otp(db, id_caso, datos.canal, datos.codigo, actor.usuario, actor.correlation_id)
    return respuestas.exito(request, resultado, 200,
                            "Código verificado" if resultado["verificado"] else "Código incorrecto")


@router.post("/casos/{id_caso}/validaciones", status_code=201,
             summary="Validar identidad: RENIEC, listas restrictivas, PEP, biometría")
def validaciones(request: Request, id_caso: str, datos: ValidacionesEjecutar, db: Session = Depends(db_session),
                 actor: Actor = Depends(asesor)):
    creadas = svc.ejecutar_validaciones(db, id_caso, datos.tipos, actor.usuario, actor.correlation_id)
    return respuestas.exito(request, [ValidacionVista.model_validate(v).model_dump() for v in creadas], 201)


@router.post("/casos/{id_caso}/validaciones/manual", status_code=201,
             summary="Registrar una validación hecha por una persona")
def validacion_manual(request: Request, id_caso: str, datos: ValidacionManual,
                      db: Session = Depends(db_session), actor: Actor = Depends(asesor)):
    v = svc.validacion_manual(db, id_caso, datos.model_dump(), actor.usuario, actor.correlation_id)
    return respuestas.exito(request, ValidacionVista.model_validate(v).model_dump(), 201)


@router.post("/casos/{id_caso}/consultas-riesgo", status_code=201, summary="Consultar una central de riesgos")
def consulta_riesgo(request: Request, id_caso: str, datos: ConsultaPedir, db: Session = Depends(db_session),
                    actor: Actor = Depends(asesor)):
    reporte = datos.reporte.model_dump() if datos.reporte else None
    consulta = svc.consultar_central(db, id_caso, datos.central, reporte, actor.usuario, actor.correlation_id)
    return respuestas.exito(request, ConsultaVista.model_validate(consulta).model_dump(), 201)


@router.post("/casos/{id_caso}/perfil", status_code=201, summary="Calcular el perfil de riesgo (0 a 1000)")
def perfil(request: Request, id_caso: str, db: Session = Depends(db_session), actor: Actor = Depends(asesor)):
    p = svc.calcular_perfil(db, id_caso, actor.usuario, actor.correlation_id)
    return respuestas.exito(request, PerfilVista.model_validate(p).model_dump(), 201)


@router.post("/casos/{id_caso}/estado", summary="Observar, levantar la observación, rechazar o revocar")
def estado(request: Request, id_caso: str, datos: CasoEstado, db: Session = Depends(db_session),
           actor: Actor = Depends(asesor)):
    caso = svc.cambiar_estado(db, id_caso, datos.accion, datos.motivo, actor.usuario, actor.correlation_id)
    return respuestas.exito(request, _caso(caso))


@router.post("/casos/{id_caso}/habilitar",
             summary="Registrar o reutilizar al cliente en COREDB y habilitarlo para Solicitud de Crédito")
def habilitar(request: Request, id_caso: str, db: Session = Depends(db_session),
              core: CoreDb = Depends(get_core), actor: Actor = Depends(asesor)):
    caso = svc.habilitar(db, core, id_caso, actor.usuario, actor.correlation_id)
    return respuestas.exito(request, _caso(caso), 200, "Cliente habilitado")


@router.get("/casos/{id_caso}/referencia", summary="La referencia que verá Solicitud de Crédito")
def referencia(request: Request, id_caso: str, db: Session = Depends(db_session),
               core: CoreDb = Depends(get_core), actor: Actor = Depends(lector)):
    return respuestas.exito(request, svc.referencia_de_caso(db, core, id_caso, actor.correlation_id))
