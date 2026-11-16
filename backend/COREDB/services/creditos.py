"""Créditos sobre los procedimientos y las vistas de creditos.* (bd-v1.4-mysql).

El usuario de la API no lee tablas de créditos: escribe por procedimientos y lee las
vistas v_*_api. Los mensajes de la base de esta sección no llevan cifras ni valores de
entrada, por eso se devuelven sin el código de la regla.
"""

import hashlib
import json
import uuid
from collections.abc import Callable, Sequence
from datetime import timezone
from decimal import Decimal
from typing import Any, Protocol, TypeVar

from sqlalchemy import text
from sqlalchemy.orm import Session

from COREDB.database import llamar
from COREDB.errores import ErrorCoreDb
from COREDB.services import regla_evaluacion
from COREDB.transacciones import con_reintentos

T = TypeVar("T")

# Regla de la base → (código del contrato, estado HTTP, mensaje fijo o None para usar el de la base).
REGLAS: dict[str, tuple[str, int, str | None]] = {
    "BNA-SOLICITUD": ("SOLICITUD_NO_ADMITIDA", 422, None),
    "BNA-CLIENTE": ("CLIENTE_NO_HABILITADO", 422, "El cliente no existe o no puede operar."),
    "BNA-CALENDARIO": ("CALENDARIO_INVALIDO", 422, None),
    "BNA-IDEMPOTENCIA": ("IDEMPOTENCIA_CONFLICTO", 409, None),
    "BNA-EVALUACION": ("EVALUACION_NO_ADMITIDA", 422, None),
    "BNA-REGLA": ("REGLA_NO_DISPONIBLE", 422, "Ninguna regla de evaluación cubre el resultado."),
    "BNA-ANALISTA": ("ANALISTA_REQUERIDO", 422, "El usuario no es un analista de crédito registrado y activo."),
    "BNA-MOTIVO": ("MOTIVO_REQUERIDO", 422, None),
    "BNA-EMPLEADO": ("EMPLEADO_NO_HABILITADO", 422, "El empleado no existe o no está activo."),
}


def _mensaje_de_la_base(mensaje: str) -> str:
    texto = mensaje.split(":", 1)[-1].strip()
    return (texto[:1].upper() + texto[1:] + ("" if texto.endswith(".") else ".")) if texto else "Rechazado."


def traducir(exc: ErrorCoreDb) -> ErrorCoreDb:
    # En esta área, solo registrar_analista puede dar un duplicado.
    if exc.code == "REGISTRO_DUPLICADO" and getattr(exc, "restriccion", None) in {"PRIMARY", "uk_analista_1"}:
        return ErrorCoreDb("ANALISTA_DUPLICADO", "El empleado ya es analista de crédito.", 409)
    if exc.code in REGLAS:
        codigo, estado, fijo = REGLAS[exc.code]
        return ErrorCoreDb(codigo, fijo or _mensaje_de_la_base(exc.message), estado)
    return exc


def _escribir(db: Session, operacion: Callable[[], T], nombre: str) -> T:
    try:
        return con_reintentos(db, operacion, nombre=nombre)
    except ErrorCoreDb as exc:
        raise traducir(exc) from None


def solicitud_no_encontrada() -> ErrorCoreDb:
    return ErrorCoreDb("SOLICITUD_NO_ENCONTRADA", "La solicitud no existe.", 404)


def _uuid(valor: Any) -> str | None:
    return None if valor is None else str(uuid.UUID(bytes=valor) if isinstance(valor, bytes) else valor)


def _utc(valor):
    return None if valor is None else valor.replace(tzinfo=timezone.utc)


# ── Expediente (CR-INT-02) ──────────────────────────────────────────────────


class _Cuota(Protocol):
    numero_cuota: int
    fecha_vencimiento: Any
    saldo_inicial: Decimal
    amortizacion: Decimal
    interes: Decimal
    cuota_total: Decimal
    saldo_final: Decimal


_IMPORTES = ("saldo_inicial", "amortizacion", "interes", "cuota_total", "saldo_final")


def _cuotas_json(cuotas: Sequence[_Cuota]) -> str:
    """JSON con números decimales exactos (json.dumps los pasaría por float)."""
    partes = []
    for c in cuotas:
        campos = [f'"numero_cuota": {int(c.numero_cuota)}',
                  f'"fecha_vencimiento": "{c.fecha_vencimiento.isoformat()}"']
        campos += [f'"{campo}": {getattr(c, campo):.2f}' for campo in _IMPORTES]
        partes.append("{" + ", ".join(campos) + "}")
    return "[" + ", ".join(partes) + "]"


def huella_expediente(datos) -> str:
    """SHA-256 del contenido del expediente, sin depender de cómo vinieron los números."""
    canonico = {
        "id_solicitud": str(datos.id_solicitud), "version": datos.version_solicitud,
        "cod_cliente": datos.cod_cliente, "monto": f"{datos.monto_solicitado:.2f}", "moneda": datos.moneda,
        "plazo": datos.plazo_meses, "pago_doble": datos.condicion_pago_doble, "destino": datos.destino,
        "metodo": datos.calendario.metodo, "tasa": f"{datos.calendario.tasa:.4f}",
        "cuotas": json.loads(_cuotas_json(datos.calendario.cuotas), parse_float=str),
    }
    return hashlib.sha256(json.dumps(canonico, sort_keys=True).encode("utf-8")).hexdigest()


def registrar_solicitud(db: Session, datos, *, correlation_id: uuid.UUID, actor: str) -> dict[str, Any]:
    huella = huella_expediente(datos)

    def operacion():
        return llamar(
            db, "creditos.registrar_solicitud",
            datos.id_solicitud, datos.version_solicitud, datos.cod_cliente, datos.monto_solicitado,
            datos.moneda, datos.plazo_meses, datos.condicion_pago_doble, datos.calendario.metodo,
            datos.calendario.tasa, _cuotas_json(datos.calendario.cuotas), huella, actor, correlation_id,
            salidas=3,
        )

    ronda, id_evaluacion, repetido = _escribir(db, operacion, "registrar_solicitud")
    (estado,) = db.execute(
        text("SELECT estado_solicitud FROM creditos.v_solicitud_api WHERE id_solicitud = :id"),
        {"id": datos.id_solicitud.bytes},
    ).one()
    return {"id_solicitud": datos.id_solicitud, "version_solicitud": datos.version_solicitud, "ronda": ronda,
            "id_evaluacion": _uuid(id_evaluacion), "estado": estado, "repetido": bool(repetido)}


# ── Lecturas ────────────────────────────────────────────────────────────────

_SOLICITUD = (
    "SELECT BIN_TO_UUID(id_solicitud) AS id_solicitud, version_solicitud, ronda, cod_cliente, monto_solicitado, "
    "moneda, plazo_meses, condicion_pago_doble, estado_solicitud AS estado, fecha_creacion, "
    "BIN_TO_UUID(id_calendario) AS id_calendario, tipo_calendario, metodo_amortizacion, tasa_aplicada, "
    "numero_cuotas, total_cuotas, primer_vencimiento FROM creditos.v_solicitud_api"
)


def _solicitud(fila) -> dict[str, Any]:
    datos = dict(fila._mapping)
    datos["condicion_pago_doble"] = bool(datos["condicion_pago_doble"])
    datos["fecha_creacion"] = _utc(datos["fecha_creacion"])
    return datos


def listar_solicitudes(db: Session, *, estado: str | None, cod_cliente: str | None, limite: int,
                       offset: int) -> list[dict[str, Any]]:
    filtros, parametros = [], {"limite": limite, "offset": offset}
    if estado is not None:
        filtros.append("estado_solicitud = :estado")
        parametros["estado"] = estado
    if cod_cliente is not None:
        filtros.append("cod_cliente = :cliente")
        parametros["cliente"] = cod_cliente
    donde = f" WHERE {' AND '.join(filtros)}" if filtros else ""
    filas = db.execute(
        text(f"{_SOLICITUD}{donde} ORDER BY fecha_creacion DESC, id_solicitud LIMIT :limite OFFSET :offset"),
        parametros,
    ).all()
    return [_solicitud(f) for f in filas]


def _evaluaciones(db: Session, condicion: str, parametros: dict) -> list[dict[str, Any]]:
    filas = db.execute(text(
        "SELECT BIN_TO_UUID(id_evaluacion) AS id_evaluacion, BIN_TO_UUID(id_solicitud) AS id_solicitud, ronda, "
        "fecha_evaluacion, score_calculado AS score, limite_aprobado AS limite, id_regla AS regla, resultado_regla, "
        "ingreso_mensual, deuda_reportada AS deuda_mensual, resultado_verificacion, decision, comentario, "
        "fecha_decision, id_analista, resultado, "
        f"es_ultima FROM creditos.v_evaluacion_api WHERE {condicion} ORDER BY ronda"
    ), parametros).all()
    resultado = []
    for fila in filas:
        datos = dict(fila._mapping)
        datos["fecha_evaluacion"] = _utc(datos["fecha_evaluacion"])
        datos["fecha_decision"] = _utc(datos["fecha_decision"])
        datos["es_ultima"] = bool(datos["es_ultima"])
        resultado.append(datos)
    return resultado


def evaluacion(db: Session, id_evaluacion: uuid.UUID) -> dict[str, Any] | None:
    filas = _evaluaciones(db, "id_evaluacion = :id", {"id": id_evaluacion.bytes})
    return filas[0] if filas else None


def solicitud(db: Session, id_solicitud: uuid.UUID) -> dict[str, Any]:
    fila = db.execute(text(f"{_SOLICITUD} WHERE id_solicitud = :id"), {"id": id_solicitud.bytes}).first()
    if fila is None:
        raise solicitud_no_encontrada()
    datos = _solicitud(fila)
    cuotas = db.execute(text(
        "SELECT numero_cuota, fecha_vencimiento, capital, interes, otros_conceptos, cuota_total, saldo_capital, "
        "saldo_pendiente, estado_cuota FROM creditos.v_calendario_api "
        "WHERE id_calendario = UUID_TO_BIN(:cal) ORDER BY numero_cuota"
    ), {"cal": datos["id_calendario"]}).all() if datos["id_calendario"] else []
    datos["calendario"] = None if datos["id_calendario"] is None else {
        "id_calendario": datos["id_calendario"], "tipo": datos["tipo_calendario"],
        "metodo": datos["metodo_amortizacion"], "tasa": datos["tasa_aplicada"],
        "cuotas": [dict(c._mapping) for c in cuotas],
    }
    datos["evaluaciones"] = _evaluaciones(db, "id_solicitud = :id", {"id": id_solicitud.bytes})
    datos["historial"] = [
        {**dict(h._mapping), "fecha_hora": _utc(h.fecha_hora)}
        for h in db.execute(text(
            "SELECT estado_nuevo AS estado, fecha_hora, actor, motivo FROM creditos.v_historial_solicitud_api "
            "WHERE id_solicitud = :id ORDER BY fecha_hora, id_historial"
        ), {"id": id_solicitud.bytes}).all()
    ]
    return datos


def aprobaciones(db: Session, *, cod_cliente: str | None, id_solicitud: uuid.UUID | None) -> list[dict[str, Any]]:
    filtros, parametros = [], {}
    if cod_cliente is not None:
        filtros.append("cod_cliente = :cliente")
        parametros["cliente"] = cod_cliente
    if id_solicitud is not None:
        filtros.append("id_solicitud = :id")
        parametros["id"] = id_solicitud.bytes
    donde = f" WHERE {' AND '.join(filtros)}" if filtros else ""
    filas = db.execute(text(
        "SELECT BIN_TO_UUID(id_evaluacion) AS id_evaluacion, BIN_TO_UUID(id_solicitud) AS id_solicitud, "
        "cod_cliente, ronda, monto, moneda, plazo_meses, limite_aprobado, fecha_aprobacion, vigente_hasta, "
        f"BIN_TO_UUID(id_calendario) AS id_calendario FROM creditos.v_aprobacion_api{donde} "
        "ORDER BY fecha_aprobacion DESC LIMIT 200"
    ), parametros).all()
    return [{**dict(f._mapping), "fecha_aprobacion": _utc(f.fecha_aprobacion),
             "vigente_hasta": _utc(f.vigente_hasta)} for f in filas]


# ── Evaluación, decisión, revocación y analistas ────────────────────────────


def evaluar(db: Session, id_solicitud: uuid.UUID, *, version_solicitud: int, ingreso_mensual: Decimal,
            deuda_mensual: Decimal, riesgo: str, correlation_id: uuid.UUID, actor: str) -> dict[str, Any]:
    def operacion():
        fila = db.execute(text(
            "SELECT version_solicitud, monto_solicitado, plazo_meses FROM creditos.v_solicitud_api "
            "WHERE id_solicitud = :id"
        ), {"id": id_solicitud.bytes}).first()
        if fila is None:
            raise solicitud_no_encontrada()
        if fila.version_solicitud != version_solicitud:
            # La base también lo rechaza; aquí evita calcular el límite con el monto de otra versión.
            raise ErrorCoreDb("BNA-SOLICITUD", "BNA-SOLICITUD: la versión evaluada no es la vigente")
        calculo = regla_evaluacion.calcular(fila.monto_solicitado, fila.plazo_meses, ingreso_mensual,
                                            deuda_mensual, riesgo)
        id_evaluacion, resultado, regla = llamar(
            db, "creditos.evaluar_solicitud",
            id_solicitud, version_solicitud, ingreso_mensual, deuda_mensual, Decimal(calculo.score),
            calculo.limite, actor, correlation_id, salidas=3,
        )
        return calculo, id_evaluacion, resultado, regla

    calculo, id_evaluacion, resultado, regla = _escribir(db, operacion, "evaluar_solicitud")
    (estado,) = db.execute(text("SELECT estado_solicitud FROM creditos.v_solicitud_api WHERE id_solicitud = :id"),
                           {"id": id_solicitud.bytes}).one()
    return {"id_evaluacion": _uuid(id_evaluacion), "id_solicitud": id_solicitud, "resultado": resultado,
            "regla": regla, "score": calculo.score, "limite": calculo.limite, "ratio": calculo.ratio,
            "estado_solicitud": estado}


def decidir(db: Session, id_evaluacion: uuid.UUID, *, decision: str, comentario: str, id_usuario: uuid.UUID,
            correlation_id: uuid.UUID, actor: str) -> dict[str, Any]:
    actual = evaluacion(db, id_evaluacion)
    if actual is None:
        raise ErrorCoreDb("EVALUACION_NO_ENCONTRADA", "La evaluación no existe.", 404)
    (estado,) = _escribir(db, lambda: llamar(
        db, "creditos.decidir_evaluacion",
        id_evaluacion, decision, comentario, id_usuario, actor, correlation_id, salidas=1,
    ), "decidir_evaluacion")
    return {"id_evaluacion": id_evaluacion, "id_solicitud": actual["id_solicitud"], "decision": decision,
            "estado_solicitud": estado}


def revocar(db: Session, id_solicitud: uuid.UUID, *, motivo: str, correlation_id: uuid.UUID,
            actor: str) -> dict[str, Any]:
    def operacion():
        if db.execute(text("SELECT 1 FROM creditos.v_solicitud_api WHERE id_solicitud = :id"),
                      {"id": id_solicitud.bytes}).first() is None:
            raise solicitud_no_encontrada()
        llamar(db, "creditos.revocar_aprobacion", id_solicitud, motivo, actor, correlation_id)

    _escribir(db, operacion, "revocar_aprobacion")
    return {"id_solicitud": id_solicitud, "estado_solicitud": "RECHAZADA"}


def registrar_analista(db: Session, id_empleado: uuid.UUID, *, actor: str) -> str:
    (id_analista,) = _escribir(
        db, lambda: llamar(db, "creditos.registrar_analista", id_empleado, actor, salidas=1), "registrar_analista"
    )
    return id_analista


def catalogos(db: Session) -> dict[str, Any]:
    (valor,) = llamar(db, "creditos.catalogos_credito", salidas=1)
    return json.loads(valor, parse_float=Decimal)
