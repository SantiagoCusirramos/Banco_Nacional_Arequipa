"""Rutas del módulo ATM."""

import json
import threading
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path
from pydantic import BaseModel

from ATM.config import settings
from ATM.core_client import CoreClient
from ATM.dependencies import (
    autorizacion, contexto_operacion, correlation_id, get_core_client,
)
from ATM.errores import traducir
from ATM.respuestas import error, exito
from ATM.services import atm as svc
from ATM.schemas.atm import (
    AutorizacionOut, AutorizarIn, ConfirmarIn, ConfigOut, EstadoOut,
    ExtornarIn, SaldoOut, ValidarPinIn, ValidarPinOut,
)

router = APIRouter(prefix="/api", tags=["ATM"])

# Directorio de archivos estáticos
STATIC_DIR = Path(__file__).resolve().parents[2] / "static"

# Registro de operaciones en memoria (para el panel técnico)
_registro_lock = threading.Lock()
_registro_operaciones = []

class RegistroEventoIn(BaseModel):
    tipo: str
    estado: str
    correlationId: str
    tarjeta: str
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
):
    try:
        resultado = await svc.autorizar_retiro(
            core, datos, ctx.idempotency_key, ctx.correlation_id, ctx.authorization
        )
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
):
    try:
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
):
    try:
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
):
    try:
        resultado = await svc.consultar_saldo(core, id_tarjeta, cid, token)
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
):
    try:
        resultado = await svc.consultar_movimientos(core, num_cuenta, cid, token)
        return exito(request, resultado)
    except Exception as e:
        status, code = traducir(getattr(e, "code", "DESCONOCIDO"), getattr(e, "status_code", 500))
        return error(request, status, code, getattr(e, "message", str(e)), getattr(e, "details", {}))


# ── Archivos Estáticos (HTML, CSS, JS, Fuentes, Logo) ────────────────────

@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@router.get("/tecnico.html", response_class=HTMLResponse, include_in_schema=False)
async def tecnico():
    return FileResponse(STATIC_DIR / "tecnico.html")


@router.get("/static/{path:path}", include_in_schema=False)
async def static_files(path: str):
    file_path = STATIC_DIR / path
    if not file_path.exists() or not file_path.is_file():
        return error(Request(scope={"type": "http"}), 404, "ERR-ATM-NO-ENCONTRADO", "Archivo no encontrado")
    return FileResponse(file_path)


# ── Registro de eventos del canal (para panel técnico) ────────────────────

@router.post("/registrar", include_in_schema=False)
async def registrar_evento(request: Request, datos: RegistroEventoIn):
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
async def leer_registro(n: int = 30):
    """Devuelve las últimas N líneas del registro de operaciones."""
    n = max(1, min(500, n))
    with _registro_lock:
        return _registro_operaciones[-n:]