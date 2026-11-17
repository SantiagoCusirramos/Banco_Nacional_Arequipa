"""Contratos de entrada y traducción del expediente de SOL al de COREDB.

CR-INT-02 sigue el sobre que arma SOL (`SOL.integrations.evaluation_envelope`, versión
CR-INT-02-PROPUESTA-v2): se validan los campos que Evaluación usa; lo demás se ignora. Lo que
llega a COREDB es su `POST /coredb/creditos/solicitudes` (CONTRATO_CREDITOS.md §3.1). Las
peticiones del personal rechazan campos desconocidos, como COREDB.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .comun import ErrorEva

PATRON_UUID = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
PATRON_OPERACION = r"^[A-Za-z0-9._:-]{8,80}$"
PATRON_CORRELACION = r"^[A-Za-z0-9._:-]{1,100}$"
# El cod_cliente de COREDB: SOL usa el mismo identificador (pendiente de ratificar en el Comité).
COD_CLIENTE = re.compile(r"^[A-Za-z0-9]{1,12}$")


class _DeSol(BaseModel):
    # Lo que SOL agregue en el futuro no rompe la recepción.
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class ClienteSol(_DeSol):
    id_cliente: str = Field(min_length=1, max_length=36)


class CondicionesSol(_DeSol):
    id_cliente: str = Field(min_length=1, max_length=36)
    monto_solicitado: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    moneda: Literal["PEN", "USD"]
    plazo_meses: int = Field(ge=1, le=600)
    destino_credito: str | None = Field(default=None, max_length=255)
    pago_doble: bool = False


class PoliticaSol(_DeSol):
    tea: Decimal = Field(ge=0, le=5)
    amortizacion: str = Field(default="FRANCES", min_length=1, max_length=20)


class CuotaSol(_DeSol):
    numero_cuota: int = Field(ge=1)
    fecha_vencimiento: date
    saldo_inicial: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    amortizacion: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    interes: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    cuota_total: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    saldo_final: Decimal = Field(ge=0, max_digits=15, decimal_places=2)


class CalendarioSol(_DeSol):
    cuotas: list[CuotaSol] = Field(min_length=1, max_length=600)
    total_pagar: Decimal = Field(gt=0, max_digits=15, decimal_places=2)


class ExpedienteSol(_DeSol):
    cliente: ClienteSol
    condiciones: CondicionesSol
    politica: PoliticaSol
    calendario: CalendarioSol


class SobreExpediente(_DeSol):
    """CR-INT-02: lo que SOL envía al pulsar «Guardar y enviar»."""

    versionContrato: str = Field(min_length=1, max_length=40)
    idSolicitud: str = Field(pattern=PATRON_UUID)
    versionSolicitud: int = Field(ge=1, le=32767, strict=True)
    idOperacion: str = Field(pattern=PATRON_OPERACION)
    idCorrelacion: str = Field(pattern=PATRON_CORRELACION)
    expediente: ExpedienteSol
    simulado: bool = False
    actorEnvio: str | None = Field(default=None, max_length=60)


def _dinero(valor: Decimal) -> str:
    return format(valor.quantize(Decimal("0.01")), "f")


def validar_expediente(sobre: SobreExpediente) -> None:
    """Lo que COREDB no puede comprobar porque solo conoce su propio cuerpo. El calendario
    (cuotas, fechas, saldos) lo vuelve a comprobar la base: CALENDARIO_INVALIDO."""
    e = sobre.expediente
    cuotas = e.calendario.cuotas
    problemas = []
    if e.cliente.id_cliente != e.condiciones.id_cliente:
        problemas.append("El cliente del expediente no coincide con el de las condiciones.")
    if sum((c.amortizacion for c in cuotas), Decimal(0)) != e.condiciones.monto_solicitado:
        problemas.append("La amortización del calendario no suma el monto solicitado.")
    if sum((c.cuota_total for c in cuotas), Decimal(0)) != e.calendario.total_pagar:
        problemas.append("Las cuotas del calendario no suman el total a pagar.")
    if problemas:
        raise ErrorEva(422, "EXPEDIENTE_INCONSISTENTE", " ".join(problemas))
    if not COD_CLIENTE.fullmatch(e.cliente.id_cliente):
        raise ErrorEva(422, "CLIENTE_NO_HABILITADO", "El cliente del expediente no es un cliente del CORE.")


def expediente_coredb(sobre: SobreExpediente) -> dict:
    """El cuerpo de `POST /coredb/creditos/solicitudes`. El calendario de SOL pasa sin cambios
    (RN-SOL-006); `destino` cuenta para la huella del expediente, pero COREDB no lo guarda."""
    e = sobre.expediente
    cuerpo = {
        "idSolicitud": sobre.idSolicitud, "versionSolicitud": sobre.versionSolicitud,
        "codCliente": e.cliente.id_cliente, "montoSolicitado": _dinero(e.condiciones.monto_solicitado),
        "moneda": e.condiciones.moneda, "plazoMeses": e.condiciones.plazo_meses,
        "condicionPagoDoble": e.condiciones.pago_doble,
        "calendario": {
            "metodo": e.politica.amortizacion.upper(),
            "tasa": format(e.politica.tea.quantize(Decimal("0.0001")), "f"),
            "cuotas": [{
                "numeroCuota": c.numero_cuota, "fechaVencimiento": c.fecha_vencimiento.isoformat(),
                "saldoInicial": _dinero(c.saldo_inicial), "amortizacion": _dinero(c.amortizacion),
                "interes": _dinero(c.interes), "cuotaTotal": _dinero(c.cuota_total),
                "saldoFinal": _dinero(c.saldo_final),
            } for c in e.calendario.cuotas],
        },
    }
    if e.condiciones.destino_credito:
        cuerpo["destino"] = e.condiciones.destino_credito
    return cuerpo


class _Estricta(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SituacionIn(_Estricta):
    """Situación financiera del cliente que registra el analista; con ella COREDB corre la regla."""

    versionSolicitud: int = Field(ge=1, le=32767)
    ingresoMensual: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    deudaMensual: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    riesgo: Literal["BUENO", "REGULAR", "ALTO"]
    verificada: bool

    def a_coredb(self) -> dict:
        return {"versionSolicitud": self.versionSolicitud, "ingresoMensual": _dinero(self.ingresoMensual),
                "deudaMensual": _dinero(self.deudaMensual), "riesgo": self.riesgo, "verificada": self.verificada}


class DecisionIn(_Estricta):
    """Decisión del analista sobre un resultado OBSERVADO de la regla. Solo APROBADO o RECHAZADO:
    por omisión del equipo (T1), el analista no devuelve la solicitud a SOL."""

    decision: Literal["APROBADO", "RECHAZADO"]
    comentario: str = Field(min_length=10, max_length=500)


class RevocacionIn(_Estricta):
    motivo: str = Field(min_length=10, max_length=255)
