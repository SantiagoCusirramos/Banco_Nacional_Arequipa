"""Créditos sobre los procedimientos y las vistas de creditos.* (bd-v1.4-mysql).

El usuario de la API no lee tablas de créditos: escribe por procedimientos y lee las
vistas v_*_api. Los mensajes de la base de esta sección no llevan cifras ni valores de
entrada, por eso se devuelven sin el código de la regla.
"""

import hashlib
import json
import uuid
from collections.abc import Callable, Sequence
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Protocol, TypeVar

from sqlalchemy import text
from sqlalchemy.orm import Session

from COREDB.database import llamar
from COREDB.errores import ErrorCoreDb
from COREDB.services import regla_evaluacion
from COREDB.transacciones import con_reintentos

T = TypeVar("T")

_CUENTA_NO_ELEGIBLE = ("La cuenta debe ser de ahorros, activa, individual, del titular y en la moneda del "
                       "crédito.")

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
    # Desembolso. Los mensajes del disparador validar_orden y de cuentas.* llevan la cuenta, el
    # cliente o importes: esos se reemplazan por uno fijo.
    "BNA-APROBACION": ("APROBACION_NO_VIGENTE", 422, None),
    "BNA-ORDEN": ("ORDEN_NO_ADMITIDA", 422, None),
    "BNA-ORDEN-UNICA": ("ORDEN_NO_ADMITIDA", 422, "La solicitud ya tiene un desembolso confirmado."),
    "BNA-CUENTA-DESTINO": ("CUENTA_NO_ELEGIBLE", 422, _CUENTA_NO_ELEGIBLE),
    "BNA-CUENTA": ("CUENTA_NO_ELEGIBLE", 422, _CUENTA_NO_ELEGIBLE),
    "BNA-IMPORTE": ("IMPORTE_NO_ADMITIDO", 422, "El importe supera el límite aprobado."),
    "BNA-VALIDACION": ("VALIDACION_NO_ADMITIDA", 422, None),
    "BNA-CANAL": ("CANAL_NO_ADMITIDO", 422, "El canal no admite el desembolso."),
    "BNA-NUMERACION": ("NUMERACION_AGOTADA", 422, None),
    # Cobranza. Sus mensajes no llevan valores, salvo el de la cuenta de origen.
    "BNA-CREDITO": ("CREDITO_NO_ADMITIDO", 422, None),
    "BNA-PAGO": ("PAGO_NO_ADMITIDO", 422, None),
    "BNA-CUENTA-ORIGEN": ("CUENTA_NO_ELEGIBLE", 422, "La cuenta debe ser del titular del crédito y estar en su moneda."),
    "BNA-MORA": ("MORA_NO_ADMITIDA", 422, None),
    "BNA-CUOTA": ("CUOTA_NO_ADMITIDA", 422, None),
}

# Un pago RECHAZADO guarda la regla que rechazó el débito (creditos.registrar_pago_cuota); la
# API la publica con un nombre del contrato.
MOTIVOS_RECHAZO = {
    "BNA-SALDO": "SALDO_INSUFICIENTE",
    "BNA-ESTADO-CUENTA": "CUENTA_NO_OPERATIVA",
    "RN-TOP-001": "TOPE_DIARIO_SUPERADO",
    "RN-BD-002": "CANAL_NO_ADMITIDO",
    "BNA-CANAL": "CANAL_NO_ADMITIDO",
}


def _mensaje_de_la_base(mensaje: str) -> str:
    texto = mensaje.split(":", 1)[-1].strip()
    return (texto[:1].upper() + texto[1:] + ("" if texto.endswith(".") else ".")) if texto else "Rechazado."


def traducir(exc: ErrorCoreDb) -> ErrorCoreDb:
    restriccion = getattr(exc, "restriccion", None)
    if exc.code == "REGISTRO_DUPLICADO" and restriccion in {"PRIMARY", "uk_analista_1"}:
        return ErrorCoreDb("ANALISTA_DUPLICADO", "El empleado ya es analista de crédito.", 409)
    # Dos pagos simultáneos con la misma referencia en créditos distintos.
    if exc.code == "REGISTRO_DUPLICADO" and restriccion == "uk_pago_1":
        return ErrorCoreDb("IDEMPOTENCIA_CONFLICTO", "La referencia ya se usó con otros datos.", 409)
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


# ── Desembolso (CONTRATO_CREDITOS.md §4) ────────────────────────────────────


def orden_no_encontrada() -> ErrorCoreDb:
    return ErrorCoreDb("ORDEN_NO_ENCONTRADA", "La orden de desembolso no existe.", 404)


def huella_orden(datos) -> str:
    """SHA-256 del contenido de la orden: la misma llave con otro contenido es un conflicto."""
    canonico = {"id_evaluacion": str(datos.id_evaluacion), "num_cuenta": datos.num_cuenta, "canal": datos.canal,
                "id_agencia": datos.id_agencia}
    return hashlib.sha256(json.dumps(canonico, sort_keys=True).encode("utf-8")).hexdigest()


_ORDEN = (
    "SELECT BIN_TO_UUID(id_orden) AS id_orden, codigo_orden, estado_orden AS estado, motivo_rechazo, importe, "
    "moneda, num_cuenta, id_canal AS canal, id_agencia, BIN_TO_UUID(id_evaluacion) AS id_evaluacion, "
    "BIN_TO_UUID(id_solicitud) AS id_solicitud, cod_cliente, usuario_preparacion, usuario_confirmacion, "
    "BIN_TO_UUID(uuid_transaccion_abono) AS uuid_transaccion_abono, cod_credito, creado_en AS fecha_creacion, "
    "actualizado_en AS fecha_actualizacion FROM creditos.v_orden_api"
)


def _orden(fila) -> dict[str, Any]:
    datos = dict(fila._mapping)
    datos["fecha_creacion"] = _utc(datos["fecha_creacion"])
    datos["fecha_actualizacion"] = _utc(datos["fecha_actualizacion"])
    return datos


def orden(db: Session, id_orden: uuid.UUID) -> dict[str, Any]:
    fila = db.execute(text(f"{_ORDEN} WHERE id_orden = :id"), {"id": id_orden.bytes}).first()
    if fila is None:
        raise orden_no_encontrada()
    return _orden(fila)


def _exigir_orden(db: Session, id_orden: uuid.UUID) -> None:
    if db.execute(text("SELECT 1 FROM creditos.v_orden_api WHERE id_orden = :id"),
                  {"id": id_orden.bytes}).first() is None:
        raise orden_no_encontrada()


def detalle_orden(db: Session, id_orden: uuid.UUID) -> dict[str, Any]:
    datos = orden(db, id_orden)
    datos["validaciones"] = [
        {**dict(v._mapping), "vence_en": _utc(v.vence_en), "fecha": _utc(v.fecha)}
        for v in db.execute(text(
            "SELECT BIN_TO_UUID(id_validacion) AS id_validacion, tipo_validacion AS tipo, resultado, "
            "referencia_evidencia, detalle, vence_en, creado_en AS fecha FROM creditos.v_validacion_orden_api "
            "WHERE id_orden = :id ORDER BY creado_en"
        ), {"id": id_orden.bytes}).all()
    ]
    datos["eventos"] = [
        {**dict(e._mapping), "fecha_hora": _utc(e.fecha_hora),
         "detalle": None if e.detalle is None else json.loads(e.detalle, parse_float=Decimal)}
        for e in db.execute(text(
            "SELECT accion, resultado, actor, BIN_TO_UUID(correlation_id) AS correlation_id, detalle, fecha_hora "
            "FROM creditos.v_evento_credito_api WHERE id_entidad = :id ORDER BY fecha_hora, id_evento"
        ), {"id": str(id_orden)}).all()
    ]
    return datos


def listar_ordenes(db: Session, *, estado: str | None, cod_cliente: str | None, id_solicitud: uuid.UUID | None,
                   limite: int, offset: int) -> list[dict[str, Any]]:
    filtros, parametros = [], {"limite": limite, "offset": offset}
    if estado is not None:
        filtros.append("estado_orden = :estado")
        parametros["estado"] = estado
    if cod_cliente is not None:
        filtros.append("cod_cliente = :cliente")
        parametros["cliente"] = cod_cliente
    if id_solicitud is not None:
        filtros.append("id_solicitud = :solicitud")
        parametros["solicitud"] = id_solicitud.bytes
    donde = f" WHERE {' AND '.join(filtros)}" if filtros else ""
    filas = db.execute(
        text(f"{_ORDEN}{donde} ORDER BY creado_en DESC, id_orden LIMIT :limite OFFSET :offset"), parametros
    ).all()
    return [_orden(f) for f in filas]


def preparar_orden(db: Session, datos, *, llave: uuid.UUID, correlation_id: uuid.UUID,
                   actor: str) -> tuple[dict[str, Any], bool]:
    huella = huella_orden(datos)
    id_orden, _, repetido = _escribir(db, lambda: llamar(
        db, "creditos.preparar_orden",
        datos.id_evaluacion, datos.num_cuenta, datos.canal, datos.id_agencia, llave, huella, actor, correlation_id,
        salidas=3,
    ), "preparar_orden")
    return orden(db, uuid.UUID(bytes=id_orden)), bool(repetido)


def cambiar_cuenta(db: Session, id_orden: uuid.UUID, *, num_cuenta: str, correlation_id: uuid.UUID,
                   actor: str) -> dict[str, Any]:
    def operacion():
        _exigir_orden(db, id_orden)
        llamar(db, "creditos.cambiar_cuenta_orden", id_orden, num_cuenta, actor, correlation_id, salidas=1)

    _escribir(db, operacion, "cambiar_cuenta_orden")
    return orden(db, id_orden)


def _utc_sin_zona(valor: datetime | None) -> datetime | None:
    return None if valor is None else valor.astimezone(timezone.utc).replace(tzinfo=None)


def registrar_validacion(db: Session, id_orden: uuid.UUID, datos, *, correlation_id: uuid.UUID,
                         actor: str) -> dict[str, Any]:
    def operacion():
        _exigir_orden(db, id_orden)
        llamar(db, "creditos.registrar_validacion_orden",
               id_orden, datos.tipo, datos.resultado, datos.referencia_evidencia, datos.detalle,
               _utc_sin_zona(datos.vence_en), actor, correlation_id, salidas=1)

    _escribir(db, operacion, "registrar_validacion_orden")
    return orden(db, id_orden)


def confirmar_orden(db: Session, id_orden: uuid.UUID, *, correlation_id: uuid.UUID,
                    actor: str) -> tuple[dict[str, Any], bool]:
    def operacion():
        _exigir_orden(db, id_orden)
        return llamar(db, "creditos.confirmar_orden", id_orden, actor, correlation_id, salidas=3)

    cod_credito, uuid_abono, repetido = _escribir(db, operacion, "confirmar_orden")
    (fecha,) = db.execute(text("SELECT fecha_desembolso FROM creditos.v_credito_api WHERE cod_credito = :c"),
                          {"c": cod_credito}).one()
    datos = orden(db, id_orden)
    return {"id_orden": datos["id_orden"], "codigo_orden": datos["codigo_orden"], "estado": datos["estado"],
            "cod_credito": cod_credito, "uuid_transaccion_abono": _uuid(uuid_abono),
            "fecha_efectiva": _utc(fecha)}, bool(repetido)


def rechazar_orden(db: Session, id_orden: uuid.UUID, *, motivo: str, correlation_id: uuid.UUID,
                   actor: str) -> dict[str, Any]:
    def operacion():
        _exigir_orden(db, id_orden)
        llamar(db, "creditos.rechazar_orden", id_orden, motivo, actor, correlation_id)

    _escribir(db, operacion, "rechazar_orden")
    return orden(db, id_orden)


def conciliacion_desembolsos(db: Session, fecha: date | None) -> list[dict[str, Any]]:
    donde, parametros = ("", {}) if fecha is None else (" WHERE fecha = :fecha", {"fecha": fecha})
    filas = db.execute(text(
        "SELECT fecha, moneda, ordenes_confirmadas, importe_ordenes, importe_abonado, ordenes_sin_abono "
        f"FROM creditos.v_conciliacion_diaria{donde} ORDER BY fecha DESC, moneda LIMIT 366"
    ), parametros).all()
    return [dict(f._mapping) for f in filas]


# ── Cobranza (CONTRATO_CREDITOS.md §5) ──────────────────────────────────────

_CENTIMO = Decimal("0.01")


def motivo_de_rechazo(regla: str | None) -> str | None:
    if regla is None:
        return None
    return MOTIVOS_RECHAZO.get(regla, "DEBITO_RECHAZADO")


def credito_no_encontrado() -> ErrorCoreDb:
    return ErrorCoreDb("CREDITO_NO_ENCONTRADO", "El crédito no existe.", 404)


def _exigir_credito(db: Session, cod_credito: str) -> None:
    if db.execute(text("SELECT 1 FROM creditos.v_credito_api WHERE cod_credito = :c"),
                  {"c": cod_credito}).first() is None:
        raise credito_no_encontrado()


def huella_pago(cod_credito: str, datos) -> str:
    """SHA-256 del pago: la misma referencia con otro contenido, o en otro crédito, es un conflicto."""
    canonico = {"cod_credito": cod_credito, "num_cuenta": datos.num_cuenta, "monto": f"{datos.monto:.2f}",
                "referencia": datos.referencia, "canal": datos.canal}
    return hashlib.sha256(json.dumps(canonico, sort_keys=True).encode("utf-8")).hexdigest()


_CREDITO = (
    "SELECT cod_credito, estado_credito AS estado, cod_cliente, BIN_TO_UUID(id_solicitud) AS id_solicitud, "
    "BIN_TO_UUID(id_orden) AS id_orden, codigo_orden, moneda, monto_desembolsado, fecha_desembolso, numero_cuotas, "
    "cuotas_pagadas, cuotas_vencidas, saldo_pendiente, proximo_vencimiento, mora_vigente FROM creditos.v_credito_api"
)


def _credito(fila) -> dict[str, Any]:
    datos = dict(fila._mapping)
    datos["fecha_desembolso"] = _utc(datos["fecha_desembolso"])
    for campo in ("numero_cuotas", "cuotas_pagadas", "cuotas_vencidas"):
        datos[campo] = int(datos[campo] or 0)
    return datos


def listar_creditos(db: Session, *, estado: str | None, cod_cliente: str | None, limite: int,
                    offset: int) -> list[dict[str, Any]]:
    filtros, parametros = [], {"limite": limite, "offset": offset}
    if estado is not None:
        filtros.append("estado_credito = :estado")
        parametros["estado"] = estado
    if cod_cliente is not None:
        filtros.append("cod_cliente = :cliente")
        parametros["cliente"] = cod_cliente
    donde = f" WHERE {' AND '.join(filtros)}" if filtros else ""
    filas = db.execute(
        text(f"{_CREDITO}{donde} ORDER BY cod_credito DESC LIMIT :limite OFFSET :offset"), parametros
    ).all()
    return [_credito(f) for f in filas]


def _resumen_credito(db: Session, cod_credito: str) -> dict[str, Any]:
    fila = db.execute(text(f"{_CREDITO} WHERE cod_credito = :c"), {"c": cod_credito}).first()
    if fila is None:
        raise credito_no_encontrado()
    return _credito(fila)


def detalle_credito(db: Session, cod_credito: str) -> dict[str, Any]:
    datos = _resumen_credito(db, cod_credito)
    datos["cuotas"] = [
        {**dict(c._mapping), "dias_atraso": int(c.dias_atraso)}
        for c in db.execute(text(
            "SELECT numero_cuota, fecha_vencimiento, capital, interes, otros_conceptos, cuota_total, saldo_pendiente, "
            "estado_cuota AS estado, dias_atraso, mora_vigente FROM creditos.v_cuota_api WHERE cod_credito = :c "
            "ORDER BY numero_cuota"
        ), {"c": cod_credito}).all()
    ]
    # Los del crédito y los de sus cuotas («CRE-…:n»); los de cada pago están en el pago.
    datos["eventos"] = [
        {**dict(e._mapping), "fecha_hora": _utc(e.fecha_hora),
         "detalle": None if e.detalle is None else json.loads(e.detalle, parse_float=Decimal)}
        for e in db.execute(text(
            "SELECT accion, resultado, numero_cuota, actor, BIN_TO_UUID(correlation_id) AS correlation_id, detalle, "
            "fecha_hora FROM creditos.v_evento_credito_api WHERE id_entidad = :c OR id_entidad LIKE :cuotas "
            "ORDER BY fecha_hora, id_evento"
        ), {"c": cod_credito, "cuotas": f"{cod_credito}:%"}).all()
    ]
    return datos


_PAGO = (
    "SELECT BIN_TO_UUID(id_pago) AS id_pago, referencia, cod_credito, fecha_hora AS fecha, monto_pago AS monto, "
    "estado_confirmacion AS estado, motivo_rechazo, id_canal AS canal, num_cuenta, "
    "BIN_TO_UUID(uuid_transaccion) AS uuid_transaccion, monto_aplicado, aplicaciones FROM creditos.v_pago_api"
)


def _pago(fila) -> dict[str, Any]:
    datos = dict(fila._mapping)
    datos["fecha"] = _utc(datos["fecha"])
    datos["motivo"] = motivo_de_rechazo(datos.pop("motivo_rechazo"))
    # JSON_OBJECT de MySQL escribe 80.00 como 80.0: se vuelve a llevar al céntimo.
    aplicaciones = json.loads(datos["aplicaciones"], parse_float=Decimal) if datos["aplicaciones"] else []
    datos["aplicaciones"] = sorted(
        ({"numero_cuota": int(a["numero_cuota"]),
          "monto_aplicado": Decimal(str(a["monto_aplicado"])).quantize(_CENTIMO)} for a in aplicaciones),
        key=lambda a: a["numero_cuota"])
    return datos


def pago_por_referencia(db: Session, referencia: str) -> dict[str, Any]:
    fila = db.execute(text(f"{_PAGO} WHERE referencia = :r"), {"r": referencia}).first()
    if fila is None:
        raise ErrorCoreDb("PAGO_NO_ENCONTRADO", "El pago no existe.", 404)
    return _pago(fila)


def pagos_del_credito(db: Session, cod_credito: str, *, limite: int, offset: int) -> list[dict[str, Any]]:
    _exigir_credito(db, cod_credito)
    filas = db.execute(text(
        f"{_PAGO} WHERE cod_credito = :c ORDER BY fecha_hora DESC, id_pago LIMIT :limite OFFSET :offset"
    ), {"c": cod_credito, "limite": limite, "offset": offset}).all()
    return [_pago(f) for f in filas]


def registrar_pago(db: Session, cod_credito: str, datos, *, correlation_id: uuid.UUID,
                   actor: str) -> tuple[dict[str, Any], bool]:
    huella = huella_pago(cod_credito, datos)

    def operacion():
        _exigir_credito(db, cod_credito)
        return llamar(
            db, "creditos.registrar_pago_cuota",
            cod_credito, datos.num_cuenta, datos.monto, datos.referencia, datos.canal, huella, actor, correlation_id,
            salidas=5,
        )

    *_, repetido = _escribir(db, operacion, "registrar_pago_cuota")
    pago = pago_por_referencia(db, datos.referencia)
    credito = _resumen_credito(db, cod_credito)
    return {**pago, "estado_credito": credito["estado"], "saldo_pendiente": credito["saldo_pendiente"]}, bool(repetido)


# ── Mora y vencimientos ─────────────────────────────────────────────────────

_MORA = (
    "SELECT BIN_TO_UUID(id_mora) AS id_mora, cod_credito, numero_cuota, monto_calculado, fecha_calculo, dias_atraso, "
    "vigente FROM creditos.v_mora_api"
)


def _mora(fila) -> dict[str, Any]:
    datos = dict(fila._mapping)
    datos["fecha_calculo"] = _utc(datos["fecha_calculo"])
    datos["dias_atraso"] = int(datos["dias_atraso"])
    datos["vigente"] = bool(datos["vigente"])
    return datos


def registrar_mora(db: Session, cod_credito: str, numero_cuota: int, *, monto: Decimal, correlation_id: uuid.UUID,
                   actor: str) -> dict[str, Any]:
    def operacion():
        _exigir_credito(db, cod_credito)
        return llamar(db, "creditos.registrar_mora", cod_credito, numero_cuota, monto, actor, correlation_id,
                      salidas=1)

    (id_mora,) = _escribir(db, operacion, "registrar_mora")
    return _mora(db.execute(text(f"{_MORA} WHERE id_mora = :id"), {"id": id_mora}).one())


def historial_mora(db: Session, cod_credito: str, numero_cuota: int) -> list[dict[str, Any]]:
    _exigir_credito(db, cod_credito)
    filas = db.execute(text(
        f"{_MORA} WHERE cod_credito = :c AND numero_cuota = :n ORDER BY fecha_calculo DESC, id_mora"
    ), {"c": cod_credito, "n": numero_cuota}).all()
    return [_mora(f) for f in filas]


def fecha_de_negocio(db: Session) -> date:
    """Hoy en Lima, según la base."""
    return db.execute(text("SELECT core.fn_fecha_negocio(UTC_TIMESTAMP(6))")).scalar_one()


def actualizar_vencimientos(db: Session, fecha: date | None, *, actor: str) -> dict[str, Any]:
    hoy = fecha_de_negocio(db)
    if fecha is not None and fecha > hoy:
        # Una fecha futura vencería cuotas que todavía no vencen.
        raise ErrorCoreDb("FECHA_NO_ADMITIDA", "La fecha no puede ser posterior a la fecha de negocio.")
    fecha = fecha or hoy
    cuotas, creditos_ = _escribir(
        db, lambda: llamar(db, "creditos.actualizar_vencimientos", fecha, actor, salidas=2), "actualizar_vencimientos"
    )
    return {"fecha": fecha, "cuotas_vencidas": int(cuotas or 0), "creditos_actualizados": int(creditos_ or 0)}


def conciliacion_pagos(db: Session, fecha: date | None) -> list[dict[str, Any]]:
    donde, parametros = ("", {}) if fecha is None else (" WHERE fecha = :fecha", {"fecha": fecha})
    filas = db.execute(text(
        "SELECT fecha, id_canal AS canal, moneda, pagos_confirmados, importe_cobrado, importe_aplicado, "
        f"pagos_rechazados FROM creditos.v_conciliacion_cobranza{donde} ORDER BY fecha DESC, canal, moneda LIMIT 1000"
    ), parametros).all()
    return [dict(f._mapping) for f in filas]
