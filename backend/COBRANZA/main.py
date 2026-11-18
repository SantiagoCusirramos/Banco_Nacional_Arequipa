"""API de Cobranza (módulo 14, Línea de Créditos). Puerto 8014 en el producto.

    uvicorn COBRANZA.main:app --port 8014      (desde backend/)

No tiene base propia ni cobra por CUENTAS: todo se guarda en COREDB (`creditos.*`,
CONTRATO_CREDITOS.md §5). El crédito existe desde que Desembolso confirma la orden (CR-INT-06),
así que Cobranza solo lo lee. Pagar una cuota debita la cuenta y aplica el pago en una sola
operación de COREDB (CR-INT-07); la `referencia` evita cobrar dos veces. La mora se registra y se
muestra, pero no se cobra (decisión 5 del contrato).

Rutas nuevas, con el token de COREDB de la persona:
  /api/v1/sesion                                  perfil en Cobranza
  /api/v1/creditos...                             deuda, pagos, mora y vencimientos
  /api/v1/pagos/{referencia}                      el pago con esa referencia
  /api/v1/conciliacion                            lo cobrado frente a lo aplicado

Rutas que conserva la pantalla "Pagar cuota" (misma forma que la versión con base propia):
  GET  /clientes/{idCliente}/creditos
  GET  /creditos/{codCredito}/monto-a-pagar
  GET  /pagos/{referencia}/comprobante
  POST /cr-int-08/pagos                           CR-INT-08 (Home Banking)

Lo que hace la persona va con su token, que Cobranza reenvía; la tarea diaria usa el usuario de
servicio `svc-cobranza`.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from typing import Any, Literal

import httpx
from fastapi import Depends, FastAPI, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .auth import COBRAR, CONCILIAR, MORA, VER, Sesion, VerificadorCoreDb, persona
from .comun import ErrorCob, correlacion_valida, fijar_correlacion, restaurar_correlacion
from .config import Config
from .coredb import ClienteCoreDb

VERSION = "2.0.0"
log = logging.getLogger("cobranza")
BASE = "/coredb/creditos"
CENTIMO = Decimal("0.01")

EstadoCredito = Literal["AL_DIA", "EN_MORA", "CANCELADO"]
CodCredito = Path(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9-]+$")
CodClienteQuery = Query(None, min_length=1, max_length=12, pattern=r"^[A-Za-z0-9]+$")
PATRON_REFERENCIA = r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"

# Rol de COREDB → perfil en Cobranza. Los roles de créditos sin REGISTRAR_PAGO solo consultan.
PERFILES = {"OPERADOR": "OPERADOR", "ADMINISTRADOR": "SUPERVISOR", "AUDITOR": "AUDITOR"}
# La pantalla conoce PENDIENTE, PARCIAL y PAGADA; VENCIDA es la misma cuota con saldo y vencida.
ESTADOS_CUOTA_LEGACY = {"VENCIDA": "PENDIENTE"}


def perfil_de(rol: str) -> str:
    return PERFILES.get(rol, "CONSULTA")


def _d(valor: Any) -> str | None:
    if valor is None:
        return None
    return f"{Decimal(str(valor)).quantize(CENTIMO):.2f}"


def _suma(*valores: Any) -> str:
    return f"{sum((Decimal(str(v)) for v in valores), Decimal('0')).quantize(CENTIMO):.2f}"


def _cuota(detalle: dict, numero: int) -> dict | None:
    return next((c for c in detalle.get("cuotas", []) if c["numeroCuota"] == numero), None)


# ------------------------------------------------------------------ Traducciones de la pantalla
def credito_legacy(detalle: dict) -> dict:
    """El crédito de COREDB con la forma que espera `frontend/lib/cobranza.ts`."""
    cuotas = []
    for cuota in detalle.get("cuotas", []):
        saldo = _d(cuota["saldoPendiente"])
        mora = _d(cuota["moraVigente"])
        cuotas.append({
            "idCuota": f"{detalle['codCredito']}-{cuota['numeroCuota']}",
            "numeroCuota": cuota["numeroCuota"],
            "fechaVencimiento": cuota["fechaVencimiento"],
            "montoCuota": _d(cuota["cuotaTotal"]),
            "saldoPendiente": saldo,
            "moraPendiente": mora,
            "totalAdeudado": _suma(saldo, mora),
            "estadoCuota": ESTADOS_CUOTA_LEGACY.get(cuota["estado"], cuota["estado"]),
        })
    return {
        "codCredito": detalle["codCredito"], "idCliente": detalle["codCliente"],
        "montoAprobado": _d(detalle["montoDesembolsado"]), "moneda": detalle["moneda"],
        "fechaDesembolso": detalle["fechaDesembolso"], "estadoCredito": detalle["estado"],
        "saldoTotalPendiente": _d(detalle["saldoPendiente"]), "cuotas": cuotas,
    }


def monto_a_pagar_legacy(detalle: dict) -> dict | None:
    """RF-COB-003: la cuota más antigua con saldo. La mora se muestra, pero no se cobra."""
    for cuota in detalle.get("cuotas", []):
        if Decimal(str(cuota["saldoPendiente"])) > 0:
            saldo = _d(cuota["saldoPendiente"])
            return {
                "codCredito": detalle["codCredito"],
                "idCuota": f"{detalle['codCredito']}-{cuota['numeroCuota']}",
                "numeroCuota": cuota["numeroCuota"], "fechaVencimiento": cuota["fechaVencimiento"],
                "saldoCapital": saldo, "moraVigente": _d(cuota["moraVigente"]), "totalAPagar": saldo,
            }
    return None


def pago_legacy(pago: dict, detalle: dict | None = None, *, idempotente: bool = False) -> dict:
    """El pago de COREDB con la forma de CR-INT-08; la mora no se cobra (decisión 5)."""
    aplicacion = None
    if pago.get("aplicaciones"):
        aplicada = pago["aplicaciones"][0]
        cuota = _cuota(detalle, aplicada["numeroCuota"]) if detalle else None
        aplicacion = {
            "idCuota": f"{pago['codCredito']}-{aplicada['numeroCuota']}",
            "numeroCuota": aplicada["numeroCuota"],
            "montoAplicado": _d(aplicada["montoAplicado"]),
            "montoAplicadoMora": "0.00",
            "montoAplicadoCapital": _d(aplicada["montoAplicado"]),
            "saldoPendienteCuota": _d(cuota["saldoPendiente"]) if cuota else None,
            "moraPendienteCuota": _d(cuota["moraVigente"]) if cuota else "0.00",
            "estadoCuota": cuota["estado"] if cuota else None,
        }
    return {
        "idPago": pago["idPago"], "referenciaTransaccion": pago["referencia"], "estado": pago["estado"],
        "idempotente": idempotente, "motivo": pago.get("motivo"), "codCredito": pago["codCredito"],
        "idCanal": pago["canal"], "montoPago": _d(pago["monto"]), "fechaHora": pago["fecha"],
        "aplicacion": aplicacion,
        "estadoCredito": pago.get("estadoCredito") or (detalle.get("estado") if detalle else None),
    }


def comprobante_legacy(pago: dict, detalle: dict) -> dict:
    """RN-COB-012: el comprobante de un pago CONFIRMADO, con la forma anterior."""
    if pago["estado"] != "CONFIRMADO":
        raise ErrorCob(409, "PAGO_NO_CONFIRMADO",
                       "Solo se emite comprobante de pagos confirmados.")
    aplicada = pago["aplicaciones"][0] if pago.get("aplicaciones") else None
    cuota = _cuota(detalle, aplicada["numeroCuota"]) if aplicada else None
    return {
        "numeroOperacion": pago["referencia"], "fechaHora": pago["fecha"], "canal": pago["canal"],
        "codCredito": pago["codCredito"], "montoPagado": _d(pago["monto"]),
        "montoAplicadoMora": "0.00", "montoAplicadoCapital": _d(pago["montoAplicado"]),
        "cuotaNumero": aplicada["numeroCuota"] if aplicada else None,
        "saldoRestanteCuota": _d(cuota["saldoPendiente"]) if cuota else None,
        "moraRestanteCuota": _d(cuota["moraVigente"]) if cuota else "0.00",
        "saldoRestanteCredito": _d(detalle["saldoPendiente"]), "estadoCredito": detalle["estado"],
    }


# ------------------------------------------------------------------ Cuerpos
class PagoIn(BaseModel):
    """Pago de una cuota con el token de la persona (CR-INT-07)."""

    model_config = ConfigDict(extra="forbid")
    numCuenta: str = Field(min_length=1, max_length=20)
    monto: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    referencia: str = Field(min_length=1, max_length=40, pattern=PATRON_REFERENCIA)
    canal: Literal["VEN", "HB"] = "VEN"

    def a_coredb(self) -> dict:
        return {"numCuenta": self.numCuenta, "monto": _d(self.monto), "referencia": self.referencia,
                "canal": self.canal}


class PagoLegacyIn(BaseModel):
    """CR-INT-08: el cuerpo que envía la pantalla "Pagar cuota"."""

    model_config = ConfigDict(extra="forbid")
    codCliente: str = Field(min_length=1, max_length=12)
    codCredito: str = Field(min_length=1, max_length=20)
    montoPago: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    cuentaOrigen: str = Field(min_length=1, max_length=20)
    referenciaTransaccion: str = Field(min_length=1, max_length=40, pattern=PATRON_REFERENCIA)
    idCanal: Literal["VEN", "HB"] = "HB"

    def a_coredb(self) -> dict:
        return {"numCuenta": self.cuentaOrigen, "monto": _d(self.montoPago),
                "referencia": self.referenciaTransaccion, "canal": self.idCanal}


class MoraIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    montoCalculado: Decimal = Field(ge=0, max_digits=15, decimal_places=2)

    def a_coredb(self) -> dict:
        return {"montoCalculado": _d(self.montoCalculado)}


class VencimientosIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fecha: date | None = None

    def a_coredb(self) -> dict:
        return {"fecha": self.fecha.isoformat()} if self.fecha else {}


# ------------------------------------------------------------------ Aplicación
class _FormatoJson(logging.Formatter):
    def format(self, registro: logging.LogRecord) -> str:
        datos = {"timestamp": self.formatTime(registro, "%Y-%m-%dT%H:%M:%S"), "nivel": registro.levelname,
                 "modulo": "COBRANZA", "mensaje": registro.getMessage()}
        datos.update(getattr(registro, "contexto", {}))
        return json.dumps(datos, ensure_ascii=False)


def _configurar_registros() -> None:
    raiz = logging.getLogger("cobranza")
    if not raiz.handlers:
        salida = logging.StreamHandler(sys.stdout)
        salida.setFormatter(_FormatoJson())
        raiz.addHandler(salida)
        raiz.setLevel(logging.INFO)
        raiz.propagate = False


class Contexto:
    """Lo que la API necesita en ejecución: COREDB y el verificador de sesiones."""

    def __init__(self, config: Config, *, transporte_coredb: httpx.BaseTransport | None = None):
        self.config = config
        self.coredb = ClienteCoreDb(config.coredb_url, config.servicio_usuario, config.servicio_secreto,
                                    timeout=config.timeout_seg, transporte=transporte_coredb,
                                    bus_token=config.bus_token)
        self.verificador = VerificadorCoreDb(config.coredb_url, config.timeout_seg, config.sesion_cache_seg,
                                             transporte=transporte_coredb, bus_token=config.bus_token)

    def cerrar(self) -> None:
        self.verificador.cerrar()
        self.coredb.cerrar()


def _error(estado: int, codigo: str, mensaje: str) -> JSONResponse:
    return JSONResponse(status_code=estado, content={"error": {"code": codigo, "message": mensaje}})


def _sin_vacios(params: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in params.items() if v is not None}


def crear_app(config: Config | None = None, *, contexto: Contexto | None = None) -> FastAPI:
    """Sin argumentos lee la configuración del entorno al arrancar; las pruebas pasan su contexto."""

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI):
        _configurar_registros()
        if getattr(app.state, "ctx", None) is None:
            app.state.ctx = Contexto(config or Config.desde_entorno())
        try:
            yield
        finally:
            app.state.ctx.cerrar()

    app = FastAPI(
        title="BNA · Cobranza", version=VERSION, lifespan=ciclo_de_vida,
        description=(
            "Módulo 14 de la Línea de Créditos, sin base propia. El crédito ya existe en COREDB cuando "
            "Desembolso confirma la orden (CR-INT-06): Cobranza lo lee y cobra sus cuotas. Pagar debita la "
            "cuenta del titular y aplica el pago en una sola operación (CR-INT-07); la misma `referencia` no "
            "cobra dos veces. La mora se registra y se muestra, pero no se cobra (decisión 5 del contrato). "
            "Lo que hace la persona va con su token de COREDB, que Cobranza reenvía. Montos como texto "
            "decimal (\"150.00\")."),
    )
    app.state.ctx = contexto

    def ctx(request: Request) -> Contexto:
        return request.app.state.ctx

    @app.middleware("http")
    async def correlacion_y_registro(request: Request, call_next):
        correlacion = correlacion_valida(request.headers.get("X-Correlation-ID"))
        marca = fijar_correlacion(correlacion)
        inicio = time.perf_counter()
        try:
            respuesta = await call_next(request)
        finally:
            restaurar_correlacion(marca)
        respuesta.headers["X-Correlation-ID"] = correlacion
        ruta = request.scope.get("route")
        log.info("peticion", extra={"contexto": {
            "metodo": request.method, "ruta": getattr(ruta, "path", request.url.path),
            "estado": respuesta.status_code, "duracion_ms": round((time.perf_counter() - inicio) * 1000, 1),
            "correlacion": correlacion}})
        return respuesta

    @app.exception_handler(ErrorCob)
    async def _error_cob(_request: Request, exc: ErrorCob):
        return _error(exc.estado, exc.codigo, exc.mensaje)

    @app.exception_handler(RequestValidationError)
    async def _error_validacion(_request: Request, exc: RequestValidationError):
        # Como COREDB: dice qué campo falló, sin repetir los valores recibidos (cuentas, referencias).
        return JSONResponse(status_code=422, content={"detail": [
            {"loc": list(e.get("loc", ())), "type": e.get("type"), "msg": e.get("msg")} for e in exc.errors()]})

    # ------------------------------------------------------------------ Salud
    @app.get("/salud", tags=["Estado"], summary="COREDB responde y el usuario de servicio inicia sesión")
    def salud(request: Request):
        c = ctx(request)
        if not c.coredb.salud():
            return _error(503, "COREDB_NO_DISPONIBLE", "COREDB no responde.")
        try:
            c.coredb.token_servicio()
        except ErrorCob as exc:
            return _error(503, exc.codigo, exc.mensaje)
        return {"estado": "ok", "modulo": "COBRANZA", "version": VERSION}

    # ------------------------------------------------------------------ Sesión
    @app.get("/api/v1/sesion", tags=["Operación en agencia"], summary="Perfil de la persona en Cobranza")
    def sesion(sesion: Sesion = Depends(persona(VER))):
        p = sesion.perfil
        return {"usuario": p.usuario, "rol": p.rol, "perfil": perfil_de(p.rol),
                "puedeCobrar": p.puede(COBRAR), "puedeMora": p.puede(MORA),
                "puedeConciliar": p.puede(CONCILIAR)}

    # ------------------------------------------------------------------ Créditos y pagos
    tde = "Cobranza"
    tep = "Pagos"

    @app.get("/api/v1/creditos", tags=[tde], summary="Créditos desembolsados (CR-INT-06)")
    def creditos(request: Request, estado: EstadoCredito | None = None, codCliente: str | None = CodClienteQuery,
                 limite: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                 sesion: Sesion = Depends(persona(VER))):
        """Leídos de COREDB con el token de la persona, del más reciente al más antiguo."""
        params = _sin_vacios({"estado": estado, "codCliente": codCliente, "limite": limite, "offset": offset})
        return ctx(request).coredb.como_persona(sesion.token, "GET", BASE, params=params)[1]

    @app.get("/api/v1/creditos/{codCredito}", tags=[tde], summary="El crédito con sus cuotas y su bitácora",
             responses={404: {"description": "CREDITO_NO_ENCONTRADO"}})
    def detalle(codCredito: str = CodCredito, request: Request = None,
                sesion: Sesion = Depends(persona(VER))):
        return ctx(request).coredb.como_persona(sesion.token, "GET", f"{BASE}/{codCredito}")[1]

    @app.get("/api/v1/creditos/{codCredito}/pagos", tags=[tep],
             summary="Los pagos del crédito, del más reciente al más antiguo")
    def pagos(codCredito: str = CodCredito, request: Request = None,
              limite: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
              sesion: Sesion = Depends(persona(VER))):
        params = {"limite": limite, "offset": offset}
        return ctx(request).coredb.como_persona(sesion.token, "GET", f"{BASE}/{codCredito}/pagos", params=params)[1]

    @app.post("/api/v1/creditos/{codCredito}/pagos", tags=[tep], status_code=201,
              summary="Cobrar una cuota: debita la cuenta y aplica el pago (CR-INT-07)",
              responses={200: {"description": "La misma referencia con el mismo cuerpo: el mismo pago"},
                         409: {"description": "IDEMPOTENCIA_CONFLICTO"},
                         422: {"description": "PAGO_NO_ADMITIDO, CREDITO_NO_ADMITIDO o CUENTA_NO_ELEGIBLE"}})
    def cobrar(datos: PagoIn, request: Request, codCredito: str = CodCredito,
               sesion: Sesion = Depends(persona(COBRAR))):
        estado, pago = ctx(request).coredb.como_persona(sesion.token, "POST", f"{BASE}/{codCredito}/pagos",
                                                        json=datos.a_coredb())
        return JSONResponse(status_code=estado, content=pago)

    @app.get("/api/v1/pagos/{referencia}", tags=[tep], summary="El pago con esa referencia (comprobante)",
             responses={404: {"description": "PAGO_NO_ENCONTRADO"}})
    def pago_por_referencia(referencia: str = Path(min_length=1, max_length=40), request: Request = None,
                            sesion: Sesion = Depends(persona(VER))):
        return ctx(request).coredb.como_persona(sesion.token, "GET", f"{BASE}/pagos/{referencia}")[1]

    # ------------------------------------------------------------------ Mora y vencimientos
    tmo = "Mora (valor recibido)"
    lista_mora = "Créditos y mora"

    @app.post("/api/v1/creditos/{codCredito}/cuotas/{numeroCuota}/mora", tags=[tmo], status_code=201,
              summary="Registrar la mora recibida de una cuota vencida (decisión 5: no se cobra)",
              responses={422: {"description": "CUOTA_NO_ADMITIDA"}})
    def registrar_mora(datos: MoraIn, request: Request, codCredito: str = CodCredito,
                       numeroCuota: int = Path(ge=1, le=600), sesion: Sesion = Depends(persona(MORA))):
        estado, mora = ctx(request).coredb.como_persona(
            sesion.token, "POST", f"{BASE}/{codCredito}/cuotas/{numeroCuota}/mora", json=datos.a_coredb())
        return JSONResponse(status_code=estado, content=mora)

    @app.get("/api/v1/creditos/{codCredito}/cuotas/{numeroCuota}/mora", tags=[lista_mora],
             summary="Los cálculos de mora de la cuota, del más reciente al más antiguo")
    def historial_mora(request: Request, codCredito: str = CodCredito,
                       numeroCuota: int = Path(ge=1, le=600), sesion: Sesion = Depends(persona(VER))):
        return ctx(request).coredb.como_persona(
            sesion.token, "GET", f"{BASE}/{codCredito}/cuotas/{numeroCuota}/mora")[1]

    @app.post("/api/v1/vencimientos", tags=[tmo], summary="Marcar las cuotas vencidas y recalcular los créditos",
              responses={422: {"description": "FECHA_NO_ADMITIDA"}})
    def vencimientos(request: Request, datos: VencimientosIn | None = None,
                     sesion: Sesion = Depends(persona(MORA))):
        """Es también la tarea diaria de `svc-cobranza`, que la llama con su token de servicio."""
        return ctx(request).coredb.como_persona(
            sesion.token, "POST", f"{BASE}/vencimientos", json=datos.a_coredb() if datos else {})[1]

    # ------------------------------------------------------------------ Conciliación
    @app.get("/api/v1/conciliacion", tags=["Conciliación"],
             summary="Lo cobrado frente a lo aplicado, por día, canal y moneda")
    def conciliacion(request: Request, fecha: date | None = None, sesion: Sesion = Depends(persona(CONCILIAR))):
        params = {"fecha": fecha.isoformat()} if fecha else {}
        return ctx(request).coredb.como_persona(sesion.token, "GET", f"{BASE}/conciliacion/pagos", params=params)[1]

    # ------------------------------------------------------------------ Pantalla "Pagar cuota"
    tpan = "Pantalla Pagar cuota (formato anterior)"

    @app.get("/clientes/{idCliente}/creditos", tags=[tpan],
             summary="Créditos (con su cronograma) de un cliente (RF-COB-002 / RF-COB-012)")
    def creditos_del_cliente(idCliente: str = Path(min_length=1, max_length=12, pattern=r"^[A-Za-z0-9]+$"),
                             request: Request = None, sesion: Sesion = Depends(persona(VER))):
        c = ctx(request).coredb
        _, lista = c.como_persona(sesion.token, "GET", BASE, params={"codCliente": idCliente})
        return [credito_legacy(c.como_persona(sesion.token, "GET", f"{BASE}/{r['codCredito']}")[1]) for r in lista]

    @app.get("/creditos/{codCredito}/monto-a-pagar", tags=[tpan],
             summary="Monto a pagar de la próxima cuota (RF-COB-003)")
    def monto_a_pagar(request: Request, codCredito: str = CodCredito, sesion: Sesion = Depends(persona(VER))):
        detalle_credito = ctx(request).coredb.como_persona(sesion.token, "GET", f"{BASE}/{codCredito}")[1]
        monto = monto_a_pagar_legacy(detalle_credito)
        if monto is None:
            raise ErrorCob(409, "CREDITO_SIN_DEUDA", "El crédito no tiene cuotas pendientes.")
        return monto

    @app.get("/pagos/{referencia}/comprobante", tags=[tpan],
             summary="Comprobante de un pago confirmado (RN-COB-012)")
    def comprobante(request: Request, referencia: str = Path(min_length=1, max_length=40),
                    sesion: Sesion = Depends(persona(VER))):
        c = ctx(request).coredb
        _, pago = c.como_persona(sesion.token, "GET", f"{BASE}/pagos/{referencia}")
        detalle_credito = c.como_persona(sesion.token, "GET", f"{BASE}/{pago['codCredito']}")[1]
        return comprobante_legacy(pago, detalle_credito)

    @app.post("/cr-int-08/pagos", tags=[tpan], summary="CR-INT-08: pago desde Home Banking")
    def pago_home_banking(datos: PagoLegacyIn, request: Request, sesion: Sesion = Depends(persona(COBRAR))):
        """La misma `referenciaTransaccion` no cobra dos veces. `codCliente` se conserva por
        compatibilidad: COREDB comprueba que la cuenta sea del titular del crédito."""
        c = ctx(request).coredb
        estado, pago = c.como_persona(sesion.token, "POST", f"{BASE}/{datos.codCredito}/pagos",
                                      json=datos.a_coredb())
        detalle_credito = c.como_persona(sesion.token, "GET", f"{BASE}/{datos.codCredito}")[1]
        return JSONResponse(status_code=estado,
                            content=pago_legacy(pago, detalle_credito, idempotente=estado == 200))

    return app


app = crear_app()
