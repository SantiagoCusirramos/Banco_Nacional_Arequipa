"""API del modulo Cobranza (Linea de Creditos, BNA). Swagger automatico en /docs."""
import time
from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import servicio as S
from .auth import requerir_rol
from .cuentas import crear_cliente_cuentas
from .db import cargar_env, conectar, crear_esquema
from .seguridad import crear_validador_seguridad

cargar_env()
cuentas = crear_cliente_cuentas()
seguridad = crear_validador_seguridad()


@asynccontextmanager
async def lifespan(app):
    db = conectar()
    crear_esquema(db)
    db.cerrar()
    yield


app = FastAPI(
    title="Cobranza BNA",
    version="0.1.0",
    description=(
        "Modulo de Cobranza de la Linea de Creditos (laboratorio del producto BNA). Interfaces: "
        "CR-INT-06 (Desembolso a Cobranza), CR-INT-07 (Cobranza a CUENTAS: con CUENTAS_MODO=BNA debita "
        "la cuenta de ahorros por el modulo CUENTAS real; si no, simulado) y CR-INT-08 (Home Banking a "
        "Cobranza). La mora la calcula el nucleo y Cobranza solo la registra y la refleja (RGN-15, "
        "RF-COB-06 de Requerimientos y Especificaciones Generales BNA). Pendientes del Comite de "
        "Creditos: el propietario del calendario y el tratamiento de pagos mayores a la cuota. "
        "Autenticacion (I-04): header X-API-Key por rol (COBRANZA_LEER, COBRANZA_EJECUTAR, "
        "INTEGRACION_BUS); usa el boton Authorize. CR-INT-08 ademas exige X-Token-Seguridad "
        "(RF-COB-004, PROPUESTA pendiente del Comite)."),
    lifespan=lifespan,
)


def get_db():
    db = conectar()
    try:
        yield db
    finally:
        db.cerrar()


@app.exception_handler(S.ErrorNegocio)
async def manejar_error_negocio(request, exc):
    return JSONResponse(status_code=exc.status, content={"detalle": exc.detalle, "regla": exc.regla})


# Indicador I-05: tiempo de respuesta p95 de POST /cr-int-08/pagos, medido en memoria (sin metas numericas).
_TIEMPOS_PAGO_MS = []
_MAX_MUESTRAS_TIEMPO = 500


@app.middleware("http")
async def medir_tiempo_pagos(request, call_next):
    inicio = time.perf_counter()
    response = await call_next(request)
    if request.url.path == "/cr-int-08/pagos" and request.method == "POST":
        _TIEMPOS_PAGO_MS.append((time.perf_counter() - inicio) * 1000)
        del _TIEMPOS_PAGO_MS[:-_MAX_MUESTRAS_TIEMPO]
    return response


def _percentil(valores, p):
    if not valores:
        return None
    ordenados = sorted(valores)
    k = (len(ordenados) - 1) * (p / 100)
    f, c = int(k), min(int(k) + 1, len(ordenados) - 1)
    if f == c:
        return round(ordenados[f], 2)
    return round(ordenados[f] + (ordenados[c] - ordenados[f]) * (k - f), 2)


class CuotaIn(BaseModel):
    numeroCuota: int
    fechaVencimiento: date
    montoCuota: Decimal


class ObligacionIn(BaseModel):
    codCredito: str = Field(max_length=20)
    idCliente: str = Field(max_length=20)
    idSolicitud: str = Field(max_length=20)
    montoAprobado: Decimal
    moneda: str = "PEN"
    fechaDesembolso: datetime
    calendarioPagos: List[CuotaIn]
    model_config = {"json_schema_extra": {"examples": [{
        "codCredito": "CR-0001", "idCliente": "CLI-0001", "idSolicitud": "SOL-0001",
        "montoAprobado": 1200.00, "moneda": "PEN", "fechaDesembolso": "2026-10-05T10:00:00",
        "calendarioPagos": [
            {"numeroCuota": 1, "fechaVencimiento": "2026-11-05", "montoCuota": 400.00},
            {"numeroCuota": 2, "fechaVencimiento": "2026-12-05", "montoCuota": 400.00},
            {"numeroCuota": 3, "fechaVencimiento": "2027-01-05", "montoCuota": 400.00}]}]}}


class PagoIn(BaseModel):
    codCliente: str = Field(max_length=20)
    codCredito: str = Field(max_length=20)
    montoPago: Decimal
    cuentaOrigen: str = Field(max_length=30)
    referenciaTransaccion: str = Field(max_length=40)
    idCanal: str = Field(default="HB", max_length=10)
    model_config = {"json_schema_extra": {"examples": [{
        "codCliente": "CLI-0001", "codCredito": "CR-0001", "montoPago": 150.00,
        "cuentaOrigen": "AH-001-123456", "referenciaTransaccion": "OP-0001", "idCanal": "HB"}]}}


class MoraIn(BaseModel):
    diasAtraso: int
    montoCalculado: Decimal
    model_config = {"json_schema_extra": {"examples": [{"diasAtraso": 5, "montoCalculado": 12.50}]}}


T06 = "CR-INT-06 Desembolso a Cobranza"
T08 = "CR-INT-08 Home Banking a Cobranza"
TCO = "Consultas"
TCL = "Clientes (RF-COB-002 / RF-COB-012)"
TMO = "Mora (valor recibido)"
TAU = "Auditoria (CR-INT-10)"
TPP = "Pagos pendientes (RF-COB-011 / INC-01)"
TCI = "Conciliacion (RF-COB-018)"
TME = "Metricas (I-05)"


@app.get("/salud", tags=["Estado"])
def salud():
    modo = {"CuentasSimulado": "simulado", "CuentasHTTP": "http", "CuentasBNA": "bna"}
    return {"estado": "ok", "cuentas": modo.get(type(cuentas).__name__, "http")}


@app.post("/cr-int-06/obligaciones", status_code=201, tags=[T06], summary="Activar obligacion de cobro")
def activar_obligacion(body: ObligacionIn, db=Depends(get_db), rol: str = Depends(requerir_rol("INTEGRACION_BUS"))):
    return S.activar_obligacion(db, body.model_dump(), usuario=rol)


@app.post("/cr-int-08/pagos", tags=[T08],
          summary="Registrar pago de una cuota (RF-COB-004: exige X-Token-Seguridad)")
def registrar_pago(
        body: PagoIn,
        xTokenSeguridad: Optional[str] = Header(None, alias="X-Token-Seguridad"),
        db=Depends(get_db), rol: str = Depends(requerir_rol("INTEGRACION_BUS"))):
    return S.registrar_pago(db, body.model_dump(), cuentas, seguridad, xTokenSeguridad, usuario=rol)


@app.get("/creditos/{codCredito}", tags=[TCO], summary="Credito con sus cuotas y saldo")
def credito(codCredito: str, db=Depends(get_db), rol: str = Depends(requerir_rol("COBRANZA_LEER"))):
    return S.obtener_credito(db, codCredito)


@app.get("/creditos/{codCredito}/cuotas", tags=[TCO], summary="Cronograma de cuotas")
def cuotas(codCredito: str, db=Depends(get_db), rol: str = Depends(requerir_rol("COBRANZA_LEER"))):
    return S.obtener_credito(db, codCredito)["cuotas"]


@app.get("/creditos/{codCredito}/monto-a-pagar", tags=[TCO],
          summary="Monto a pagar de la proxima cuota, desglosado en capital y mora (RF-COB-003)")
def monto_a_pagar(codCredito: str, db=Depends(get_db), rol: str = Depends(requerir_rol("COBRANZA_LEER"))):
    return S.monto_a_pagar(db, codCredito)


@app.post("/creditos/{codCredito}/recalcular-estado", tags=[TCO],
          summary="Recalcula AL_DIA/EN_MORA del credito (RF-COB-007)")
def recalcular_estado(
        codCredito: str,
        fechaReferencia: Optional[date] = Query(
            None, description="Opcional, por defecto hoy. Permite demostrar la transicion a EN_MORA."),
        db=Depends(get_db), rol: str = Depends(requerir_rol("COBRANZA_EJECUTAR"))):
    return S.recalcular_estado(db, codCredito, fechaReferencia, usuario=rol)


@app.get("/creditos/{codCredito}/pagos", tags=[TCO], summary="Historial de pagos")
def pagos(codCredito: str, db=Depends(get_db), rol: str = Depends(requerir_rol("COBRANZA_LEER"))):
    return S.historial_pagos(db, codCredito)


@app.get("/clientes/{idCliente}/creditos", tags=[TCL], summary="Creditos (con su cronograma) de un cliente")
def creditos_por_cliente(idCliente: str, db=Depends(get_db), rol: str = Depends(requerir_rol("COBRANZA_LEER"))):
    return S.creditos_por_cliente(db, idCliente)


@app.get("/clientes/{idCliente}/pagos", tags=[TCL], summary="Historial de pagos de un cliente")
def pagos_por_cliente(idCliente: str, db=Depends(get_db), rol: str = Depends(requerir_rol("COBRANZA_LEER"))):
    return S.pagos_por_cliente(db, idCliente)


@app.get("/pagos/{referenciaTransaccion}/comprobante", tags=[TCO], summary="Comprobante de un pago confirmado")
def comprobante(referenciaTransaccion: str, db=Depends(get_db), rol: str = Depends(requerir_rol("COBRANZA_LEER"))):
    return S.comprobante(db, referenciaTransaccion)


@app.get("/pagos/pendientes", tags=[TPP], summary="Pagos PENDIENTE con su antiguedad (RF-COB-011 / INC-01)")
def pagos_pendientes(db=Depends(get_db), rol: str = Depends(requerir_rol("COBRANZA_LEER"))):
    return S.pagos_pendientes(db)


@app.post("/pagos/{referenciaTransaccion}/resolver", tags=[TPP],
          summary="Resuelve un pago PENDIENTE consultando a Cuentas, sin repetir el cargo (RN-COB-009)")
def resolver_pago(
        referenciaTransaccion: str, db=Depends(get_db),
        rol: str = Depends(requerir_rol("COBRANZA_EJECUTAR"))):
    return S.resolver_pago(db, referenciaTransaccion, cuentas, usuario=rol)


@app.get("/conciliacion", tags=[TCI], summary="Conciliacion diaria: total cobrado vs aplicado (RF-COB-018)")
def conciliacion(
        fecha: Optional[date] = Query(None, description="AAAA-MM-DD, por defecto hoy"),
        db=Depends(get_db), rol: str = Depends(requerir_rol("COBRANZA_LEER"))):
    return S.conciliacion(db, fecha, usuario=rol)


@app.get("/metricas", tags=[TME],
         summary="Tasa de fallas, pagos pendientes y p95 de POST /cr-int-08/pagos (I-05, sin metas)")
def metricas(db=Depends(get_db), rol: str = Depends(requerir_rol("COBRANZA_LEER"))):
    return S.metricas(db, p95_pago_ms=_percentil(_TIEMPOS_PAGO_MS, 95), muestras_pago=len(_TIEMPOS_PAGO_MS))


@app.post("/creditos/{codCredito}/cuotas/{numeroCuota}/mora", tags=[TMO],
          summary="Registrar la mora recibida para una cuota (RN-COB-010)")
def registrar_mora(
        codCredito: str, numeroCuota: int, body: MoraIn,
        fechaReferencia: Optional[date] = Query(
            None, description="Opcional, por defecto hoy. Permite demostrar RN-COB-010 sin esperar al vencimiento real."),
        db=Depends(get_db), rol: str = Depends(requerir_rol("COBRANZA_EJECUTAR"))):
    return S.registrar_mora(db, codCredito, numeroCuota, body.diasAtraso, body.montoCalculado,
                             origen=rol, fecha_referencia=fechaReferencia)


@app.get("/creditos/{codCredito}/cuotas/{numeroCuota}/mora", tags=[TMO], summary="Historial de mora de una cuota")
def historial_mora(
        codCredito: str, numeroCuota: int, db=Depends(get_db),
        rol: str = Depends(requerir_rol("COBRANZA_LEER"))):
    return S.historial_mora(db, codCredito, numeroCuota)


@app.get("/auditoria", tags=[TAU], summary="Eventos de auditoria registrados")
def auditoria(
        idEntidad: Optional[str] = None, limite: int = Query(50, ge=1, le=500),
        db=Depends(get_db), rol: str = Depends(requerir_rol("COBRANZA_LEER"))):
    return S.auditoria(db, idEntidad, limite)
