"""Rutas del módulo ATM."""

import json
import threading
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from ATM.config import settings
from ATM.core_client import CoreClient
from ATM import sesiones
from ATM.dependencies import (
    autorizacion, contexto_operacion, correlation_id, get_core_client, operador, sesion_tarjeta,
)
from ATM.errores import traducir
from ATM.respuestas import error, exito
from ATM.services import atm as svc
from ATM.schemas.atm import (
    AperturaIn, AutorizacionOut, AutorizarIn, ConfirmarIn, ConfigOut, EstadoOut,
    ExtornarIn, IdentificarIn, SaldoOut, ValidarPinIn, ValidarPinOut,
)

router = APIRouter(prefix="/api", tags=["ATM"])

# Registro de operaciones en memoria (para el panel técnico)
_registro_lock = threading.Lock()
_registro_operaciones = []

class RegistroEventoIn(BaseModel):
    tipo: str
    estado: str
    correlationId: str
    tarjeta: str = Field(max_length=4)  # solo los 4 últimos caracteres, nunca el id completo
    codigo: str | None = None
    ms: int | None = None
    uuidTransaccion: str | None = None


def _estado_cajero() -> EstadoOut:
    """Estado local del cajero (bandejas simuladas)."""
    return EstadoOut(
        terminal=settings.atm_id,
        bandejas={"PEN": {"200": 20, "100": 40, "50": 60, "20": 80, "10": 80},
                  "USD": {"100": 20, "50": 40, "20": 60, "10": 60}},
        pendientes=[],
        pruebas=None,
    )


# ── Health / Ready ───────────────────────────────────────────────────────

@router.get("/health", tags=["Sistema"])
def health():
    return {"status": "healthy", "modulo": "atm"}


@router.get("/ready", tags=["Sistema"])
async def ready(core: CoreClient = Depends(get_core_client)):
    """Listo si TARJETAS y CUENTAS responden por el Bus."""
    try:
        # Verificar TARJETAS
        core._request("GET", "/bus/tarjetas/health", sin_cuerpo=True)
        # Verificar CUENTAS
        core._request("GET", "/bus/cuentas/health", sin_cuerpo=True)
    except Exception:
        return {"status": "not_ready", "coredb": "no disponible"}
    return {"status": "ready"}


# ── Config / Estado ──────────────────────────────────────────────────────

@router.get("/config")
def config(request: Request):
    return exito(request, ConfigOut(id_cajero=settings.atm_id, pruebas=False))


@router.get("/estado")
def estado(request: Request):
    return exito(request, _estado_cajero())


# ── Identificar la tarjeta (en vez del UUID) ─────────────────────────────

@router.post("/identificar-tarjeta")
def identificar_tarjeta(
    request: Request,
    datos: IdentificarIn,
    core: CoreClient = Depends(get_core_client),
    cid: str = Depends(correlation_id),
    token: str | None = Depends(autorizacion),
):
    """Documento del titular + 4 últimos dígitos → id de la tarjeta. Exige el token del operador
    que abrió el cajero (busca con sus permisos); no abre sesión: después se pide el PIN."""
    if not token:
        return error(request, 401, "ERR-ATM-TOKEN-REQUERIDO", "Se requiere la credencial del operador del cajero.")
    try:
        return exito(request, svc.identificar_tarjeta(core, datos, cid, token).model_dump())
    except Exception as e:
        status, code = traducir(getattr(e, "code", "DESCONOCIDO"), getattr(e, "status_code", 500))
        return error(request, status, code, getattr(e, "message", str(e)), getattr(e, "details", {}))


# ── Validar PIN ──────────────────────────────────────────────────────────

@router.post("/validar-pin")
async def validar_pin_endpoint(
    request: Request,
    datos: ValidarPinIn,
    core: CoreClient = Depends(get_core_client),
    cid: str = Depends(correlation_id),
    token: str | None = Depends(autorizacion),
    x_idempotency_key: str | None = None,  # opcional para validar PIN
):
    try:
        resultado = await svc.validar_pin(core, datos, cid, token)
        if resultado.resultado == "EXITOSO":
            resultado.token_sesion = sesiones.abrir(datos.id_tarjeta)
        return exito(request, resultado)
    except Exception as e:
        status, code = traducir(getattr(e, "code", "DESCONOCIDO"), getattr(e, "status_code", 500))
        return error(request, status, code, getattr(e, "message", str(e)), getattr(e, "details", {}))


# ── Autorizar Retiro ─────────────────────────────────────────────────────

@router.post("/autorizar", status_code=201)
async def autorizar_endpoint(
    request: Request,
    datos: AutorizarIn,
    core: CoreClient = Depends(get_core_client),
    ctx = Depends(contexto_operacion),
    token_sesion: str | None = Depends(sesion_tarjeta),
):
    try:
        sesion = sesiones.exigir(token_sesion, datos.id_tarjeta)
        resultado = await svc.autorizar_retiro(
            core, datos, ctx.idempotency_key, ctx.correlation_id, ctx.authorization
        )
        sesion.autorizaciones.add(resultado.uuid_autorizacion)
        return exito(request, resultado.model_dump(mode="json"), 201, "Operación autorizada")
    except Exception as e:
        status, code = traducir(getattr(e, "code", "DESCONOCIDO"), getattr(e, "status_code", 500))
        return error(request, status, code, getattr(e, "message", str(e)), getattr(e, "details", {}))


# ── Confirmar Dispensación ───────────────────────────────────────────────

@router.post("/confirmar")
async def confirmar_endpoint(
    request: Request,
    datos: ConfirmarIn,
    core: CoreClient = Depends(get_core_client),
    ctx = Depends(contexto_operacion),
    token_sesion: str | None = Depends(sesion_tarjeta),
):
    try:
        sesiones.exigir_autorizacion(token_sesion, datos.uuid_autorizacion)
        resultado = await svc.confirmar_dispensacion(
            core, datos, ctx.idempotency_key, ctx.correlation_id, ctx.authorization
        )
        return exito(request, resultado.model_dump(mode="json"), message="Dispensación confirmada")
    except Exception as e:
        status, code = traducir(getattr(e, "code", "DESCONOCIDO"), getattr(e, "status_code", 500))
        return error(request, status, code, getattr(e, "message", str(e)), getattr(e, "details", {}))


# ── Extorno ──────────────────────────────────────────────────────────────

@router.post("/extornar")
async def extornar_endpoint(
    request: Request,
    datos: ExtornarIn,
    core: CoreClient = Depends(get_core_client),
    cid: str = Depends(correlation_id),
    token: str | None = Depends(autorizacion),
    token_sesion: str | None = Depends(sesion_tarjeta),
):
    try:
        sesiones.exigir_autorizacion(token_sesion, datos.uuid_autorizacion)
        resultado = await svc.extornar_autorizacion(core, datos, cid, token)
        return exito(request, resultado.model_dump(mode="json"), message="Operación extornada")
    except Exception as e:
        status, code = traducir(getattr(e, "code", "DESCONOCIDO"), getattr(e, "status_code", 500))
        return error(request, status, code, getattr(e, "message", str(e)), getattr(e, "details", {}))


# ── Consultar Saldo ──────────────────────────────────────────────────────

@router.get("/saldo")
async def saldo_endpoint(
    request: Request,
    id_tarjeta: str,
    core: CoreClient = Depends(get_core_client),
    cid: str = Depends(correlation_id),
    token: str | None = Depends(autorizacion),
    token_sesion: str | None = Depends(sesion_tarjeta),
):
    try:
        sesion = sesiones.exigir(token_sesion, id_tarjeta)
        resultado = await svc.consultar_saldo(core, id_tarjeta, cid, token)
        sesion.cuentas.update(c.id_cuenta for c in resultado.lista_cuentas)
        return exito(request, resultado.model_dump(mode="json"))
    except Exception as e:
        status, code = traducir(getattr(e, "code", "DESCONOCIDO"), getattr(e, "status_code", 500))
        return error(request, status, code, getattr(e, "message", str(e)), getattr(e, "details", {}))


# ── Consultar Movimientos ────────────────────────────────────────────────

@router.get("/movimientos")
async def movimientos_endpoint(
    request: Request,
    num_cuenta: str,
    core: CoreClient = Depends(get_core_client),
    cid: str = Depends(correlation_id),
    token: str | None = Depends(autorizacion),
    token_sesion: str | None = Depends(sesion_tarjeta),
):
    try:
        sesion = sesiones.exigir(token_sesion)
        if num_cuenta not in sesion.cuentas:
            return error(request, 403, "ERR-ATM-CUENTA-AJENA", "La cuenta no es de la tarjeta de esta sesión.")
        resultado = await svc.consultar_movimientos(core, num_cuenta, cid, token)
        return exito(request, resultado)
    except Exception as e:
        status, code = traducir(getattr(e, "code", "DESCONOCIDO"), getattr(e, "status_code", 500))
        return error(request, status, code, getattr(e, "message", str(e)), getattr(e, "details", {}))


# ── Sesión de la tarjeta y apertura del cajero ──────────────────────────
# La pantalla se sirve en / con StaticFiles (ver ATM/api.py: montar_pantalla), que nunca lee
# fuera de static/.

@router.post("/cerrar-sesion")
def cerrar_sesion(request: Request, token_sesion: str | None = Depends(sesion_tarjeta)):
    sesiones.cerrar(token_sesion)
    return exito(request, {"cerrada": True}, message="Sesión de tarjeta cerrada")


@router.post("/apertura")
async def apertura(request: Request, datos: AperturaIn, core: CoreClient = Depends(get_core_client),
                   cid: str = Depends(correlation_id)):
    """El operador abre el cajero con su usuario de COREDB (por el Bus). La pantalla guarda el
    token en la memoria de la pestaña y lo envía en Authorization en cada operación."""
    try:
        sesion = core.login(datos.username, datos.password, cid)
        return exito(request, {"access_token": sesion["access_token"],
                               "token_type": sesion.get("token_type", "bearer")}, message="Cajero abierto")
    except Exception as e:
        status, code = traducir(getattr(e, "code", "DESCONOCIDO"), getattr(e, "status_code", 500))
        return error(request, status, code, getattr(e, "message", str(e)), getattr(e, "details", {}))


# ── Registro de eventos del canal (para panel técnico) ────────────────────

@router.post("/registrar", include_in_schema=False)
async def registrar_evento(request: Request, datos: RegistroEventoIn, _operador: dict = Depends(operador)):
    """Recibe eventos del frontend (clave, consulta, retiro) para el log del canal.
    No guarda datos sensibles (clave, token, PAN completo)."""
    evento = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        "terminal": settings.atm_id,
        "correlationId": datos.correlationId,
        "uuidTransaccion": datos.uuidTransaccion or "-",
        "tipo": datos.tipo[:20],
        "estado": datos.estado[:30],
        "tarjeta": datos.tarjeta,
        "codigo": datos.codigo,
        "ms": datos.ms,
    }
    with _registro_lock:
        _registro_operaciones.append(evento)
        if len(_registro_operaciones) > 5000:
            _registro_operaciones.pop(0)
    return {"ok": True}


@router.get("/registro", include_in_schema=False)
async def leer_registro(n: int = 30, _operador: dict = Depends(operador)):
    """Devuelve las últimas N líneas del registro de operaciones."""
    n = max(1, min(500, n))
    with _registro_lock:
        return _registro_operaciones[-n:]