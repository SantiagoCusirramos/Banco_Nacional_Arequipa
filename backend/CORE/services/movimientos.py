"""Motor de movimientos sobre cuentas — RF-COR-04 a RF-COR-11, RGN-01..09.

Reglas aplicadas en una única transacción ACID (RNF-09):
- RGN-03 / RF-COR-07: rechazo si el débito excede el saldo disponible.
- RGN-04 / RF-COR-08: validación y acumulación del tope diario
  por cuenta + canal (limite_canal + cta_control_tope_diario).
- RGN-09: cuentas bloqueadas/observadas no originan débitos.
- RGN-10 / RF-COR-14: conversión con el tipo de cambio oficial vigente
  cuando la moneda de la operación difiere de la de la cuenta.
- RF-COR-06 / RGN-01: asiento de partida doble por operación.
- RF-COR-11 / RGN-06: idempotencia por `idempotency_key`.

Concurrencia (Hallazgo #10 del Informe de Errores BNA)
------------------------------------------------------
- Las transferencias bloquean (SELECT ... FOR UPDATE) las dos cuentas
  SIEMPRE en el mismo orden: primero la de menor `num_cuenta` y luego la
  otra, sin importar cuál es origen o destino. Así A->B y B->A
  simultáneas compiten por el mismo primer candado: una espera a la otra
  en lugar de quedar en espera circular (deadlock).
- Aun con orden consistente, InnoDB puede abortar una transacción por
  deadlock (p. ej. gap locks al crear el primer registro del día en
  `cta_control_tope_diario`). MySQL devuelve el error 1213 y revierte la
  transacción completa; por eso la operación se reintenta entera, con
  backoff exponencial + jitter, hasta MAX_INTENTOS_DEADLOCK veces. Si se
  agotan, se responde 503 (`CONCURRENCIA_REINTENTOS_AGOTADOS`).

Idempotencia (Hallazgo #11 del Informe de Errores BNA)
------------------------------------------------------
- Cada operación calcula una huella SHA-256 de sus parámetros críticos
  (tipo_operacion, cuenta, contraparte/destino, monto, moneda, canal) y
  la guarda en el detalle del evento de auditoría REGISTRAR_MOVIMIENTO.
- Si llega una `idempotency_key` ya usada, solo se devuelve el resultado
  original (replay) cuando la huella coincide; si no coincide (otra
  cuenta, otro monto, otro tipo de operación, otro destino...) se
  responde 409 (`IDEMPOTENCY_KEY_REUTILIZADA`). Esto también impide que
  una llave usada en un depósito se aplique a una transferencia o
  viceversa.
- En el replay de transferencias la pata origen se identifica por
  `tipo_movimiento='D'` y llave sin sufijo `#C`, y la destino por
  `tipo_movimiento='C'` y llave con sufijo `#C`; nunca por el orden de
  `fecha_hora` (ambas patas tienen el mismo instante).
"""

import hashlib
import json
import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from functools import partial
from typing import Any, TypeVar

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from CORE.exceptions import (
    BlockedAccountError,
    ConcurrencyError,
    ConflictError,
    DailyLimitExceededError,
    ExchangeRateNotFoundError,
    IdempotencyConflictError,
    InsufficientFundsError,
    NotFoundError,
    ValidationError,
)
from CORE.models import (
    Canal,
    CtaControlTopeDiario,
    CtaTransaccion,
    CuentaAhorro,
    LimiteCanal,
    TipoCambio,
)
from CORE.services import auditoria, contabilidad
from CORE.services.contabilidad import (
    CAJA,
    DEPOSITOS_AHORRO,
)
from CORE.utils.ids import new_uuid7
from CORE.utils.money import MONEDA_BASE, D, convertir, tope_de

SALDO_BASE = Decimal("0.00")

# Convención de idempotencia para transferencias: la pierna origen lleva
# la llave tal cual y la contraparte la lleva con sufijo "#C" (la columna
# idempotency_key es UNIQUE en el esquema).
SUFIJO_CONTRAPARTE = "#C"
# Longitud de la columna cta_transaccion.idempotency_key (VARCHAR(64)).
LONGITUD_MAX_IDEMPOTENCY_KEY = 64

# Reintentos ante deadlock de InnoDB (Hallazgo #10).
MAX_INTENTOS_DEADLOCK = 3
BACKOFF_BASE_SEGUNDOS = 0.05
BACKOFF_MAX_SEGUNDOS = 1.0
# Códigos de error MySQL/MariaDB que indican deadlock (transacción revertida).
CODIGOS_DEADLOCK_MYSQL = frozenset({1213})

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class MovimientoResultado:
    id_transaccion: str
    uuid_transaccion: str
    num_cuenta: str
    tipo_operacion: str
    tipo_movimiento: str  # D | C
    monto: Decimal
    moneda: str
    monto_moneda_base: Decimal
    saldo_posterior: Decimal
    id_asiento: str
    num_cuenta_contraparte: str | None = None
    idempotency_key: str | None = None
    fecha_hora: datetime | None = None
    replay: bool = False


@dataclass
class TransferenciaResultado:
    origen: MovimientoResultado
    destino: MovimientoResultado
    id_asiento: str
    replay: bool = False


def tasa_vigente(
    db: Session, origen: str, destino: str, fecha: date | None = None
) -> Decimal:
    """Tipo de cambio oficial más reciente no posterior a `fecha` (RF-COR-13)."""
    if origen == destino:
        return Decimal("1")
    fecha = fecha or date.today()
    tc = (
        db.query(TipoCambio)
        .filter(
            TipoCambio.cod_moneda_origen == origen,
            TipoCambio.cod_moneda_destino == destino,
            TipoCambio.fecha <= fecha,
        )
        .order_by(TipoCambio.fecha.desc())
        .first()
    )
    if tc is None:
        raise ExchangeRateNotFoundError(origen, destino, fecha.isoformat())
    return tc.tasa


def _cuenta_bloqueada_para_debito(cuenta: CuentaAhorro) -> bool:
    return cuenta.estado_cuenta not in ("ACTIVA",)


def _cuenta_cerrada(cuenta: CuentaAhorro) -> bool:
    return cuenta.estado_cuenta == "CERRADA"


def _validar_tope_diario(
    db: Session, cuenta: CuentaAhorro, id_canal: str,
    monto_en_moneda_cuenta: Decimal, fecha: date,
) -> CtaControlTopeDiario:
    """RF-COR-08 / RGN-04. Devuelve el control de tope (a acumular)."""
    limite = (
        db.query(LimiteCanal)
        .filter(LimiteCanal.id_canal == id_canal, LimiteCanal.moneda == cuenta.moneda)
        .first()
    )
    control = (
        db.query(CtaControlTopeDiario)
        .filter(
            CtaControlTopeDiario.num_cuenta == cuenta.num_cuenta,
            CtaControlTopeDiario.id_canal == id_canal,
            CtaControlTopeDiario.fecha_corte == fecha,
        )
        .with_for_update()
        .first()
    )
    acumulado = control.monto_acumulado if control else SALDO_BASE

    if limite is not None and limite.habilitado and limite.monto_maximo_diario is not None:
        if not tope_de(limite.monto_maximo_diario, acumulado, monto_en_moneda_cuenta):
            raise DailyLimitExceededError(
                tope=str(limite.monto_maximo_diario),
                acumulado=str(acumulado),
                monto_solicitado=str(monto_en_moneda_cuenta),
                regla=limite.regla_negocio,
            )
    return control


def _acumular_tope(
    db: Session, control: CtaControlTopeDiario | None, *, num_cuenta: str,
    id_canal: str, monto: Decimal, fecha: date,
) -> None:
    if control is not None:
        control.monto_acumulado = D(control.monto_acumulado + monto)
    else:
        db.add(
            CtaControlTopeDiario(
                id_tope=new_uuid7(),
                num_cuenta=num_cuenta,
                id_canal=id_canal,
                fecha_corte=fecha,
                monto_acumulado=D(monto),
            )
        )


# ── Reintentos ante deadlock (Hallazgo #10) ────────────────────────────


def _es_deadlock(exc: OperationalError) -> bool:
    """True si el error de BD es un deadlock de InnoDB (MySQL 1213 /
    SQLSTATE 40001). Con pymysql, `exc.orig.args[0]` es el código MySQL."""
    orig = getattr(exc, "orig", None)
    args = getattr(orig, "args", ()) or ()
    if args and isinstance(args[0], int) and args[0] in CODIGOS_DEADLOCK_MYSQL:
        return True
    texto = str(orig if orig is not None else exc).lower()
    return "deadlock" in texto


def _espera_backoff(intento: int) -> float:
    """Backoff exponencial con jitter: ~50 ms, ~100 ms, ~200 ms... (tope 1 s).
    El jitter evita que las dos transacciones en conflicto reintenten en
    el mismo instante y vuelvan a chocar."""
    base = min(BACKOFF_MAX_SEGUNDOS, BACKOFF_BASE_SEGUNDOS * (2 ** (intento - 1)))
    return base / 2 + random.uniform(0, base / 2)


def _con_reintentos_deadlock(
    db: Session, operacion: Callable[[], T], *, nombre: str
) -> T:
    """Ejecuta `operacion()` + commit; si InnoDB la elige como víctima de un
    deadlock, hace rollback y la reintenta completa con backoff.

    MySQL revierte TODA la transacción ante un deadlock, por lo que es
    seguro repetirla desde el inicio (se vuelven a leer saldos y topes).
    Cualquier otro error se propaga sin reintentar.
    """
    for intento in range(1, MAX_INTENTOS_DEADLOCK + 1):
        try:
            resultado = operacion()
            db.commit()
            return resultado
        except OperationalError as exc:
            db.rollback()
            if not _es_deadlock(exc):
                raise
            if intento >= MAX_INTENTOS_DEADLOCK:
                logger.error(
                    "Deadlock en %s: reintentos agotados (%d intentos).",
                    nombre, intento,
                )
                raise ConcurrencyError(nombre, intento) from exc
            espera = _espera_backoff(intento)
            logger.warning(
                "Deadlock en %s (intento %d/%d); reintentando en %.3fs.",
                nombre, intento, MAX_INTENTOS_DEADLOCK, espera,
            )
            time.sleep(espera)
    raise AssertionError("inalcanzable")  # pragma: no cover


# ── Idempotencia (Hallazgo #11) ────────────────────────────────────────


def _validar_formato_llave(idempotency_key: str | None, *, es_transferencia: bool) -> None:
    """El sufijo `#C` está reservado para la pata contraparte de las
    transferencias, y la llave + sufijo debe caber en VARCHAR(64)."""
    if not idempotency_key:
        return
    if idempotency_key.endswith(SUFIJO_CONTRAPARTE):
        raise ValidationError(
            "IDEMPOTENCY_KEY_INVALIDA",
            f"La idempotency_key no puede terminar en '{SUFIJO_CONTRAPARTE}' "
            "(sufijo reservado para la contraparte de transferencias).",
        )
    maximo = LONGITUD_MAX_IDEMPOTENCY_KEY - (
        len(SUFIJO_CONTRAPARTE) if es_transferencia else 0
    )
    if len(idempotency_key) > maximo:
        raise ValidationError(
            "IDEMPOTENCY_KEY_INVALIDA",
            f"La idempotency_key admite como máximo {maximo} caracteres "
            "para esta operación.",
        )


def _parametros_criticos(
    *,
    tipo_operacion: str,
    num_cuenta: str,
    num_cuenta_contraparte: str | None,
    monto: Decimal,
    moneda: str | None,
    id_canal: str,
) -> dict[str, Any]:
    """Parámetros que identifican una operación para efectos de
    idempotencia, normalizados (monto a 2 decimales, textos tal cual)."""
    return {
        "tipo_operacion": tipo_operacion,
        "num_cuenta": num_cuenta,
        "num_cuenta_contraparte": num_cuenta_contraparte or None,
        "monto": str(D(monto)),
        "moneda": moneda,
        "id_canal": id_canal,
    }


def _huella(parametros: dict[str, Any]) -> str:
    """Hash SHA-256 de los parámetros críticos (JSON canónico)."""
    canonico = json.dumps(parametros, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def _parametros_de_transaccion(tx: CtaTransaccion) -> dict[str, Any]:
    """Reconstruye los parámetros críticos desde una fila guardada (para
    transacciones sin huella en auditoría, p. ej. anteriores a este cambio)."""
    return _parametros_criticos(
        tipo_operacion=tx.tipo_operacion,
        num_cuenta=tx.num_cuenta,
        num_cuenta_contraparte=tx.num_cuenta_contraparte,
        monto=tx.monto,
        moneda=tx.moneda,
        id_canal=tx.id_canal,
    )


def _moneda_efectiva(db: Session, moneda: str | None, num_cuenta: str) -> str | None:
    """La operación usa la moneda de la cuenta cuando no se envía `moneda`;
    se resuelve igual que al ejecutar para que la huella sea comparable."""
    if moneda:
        return moneda
    cuenta = db.get(CuentaAhorro, num_cuenta)
    return cuenta.moneda if cuenta is not None else None


def _buscar_por_idempotencia(db: Session, key: str) -> list[CtaTransaccion]:
    """Filas con la llave exacta o con la llave + sufijo contraparte.

    El orden es solo para que el resultado sea determinista; NO se usa
    para decidir cuál es la pata origen (ver `_patas_transferencia`)."""
    llaves = (key, key + SUFIJO_CONTRAPARTE)
    return (
        db.query(CtaTransaccion)
        .filter(CtaTransaccion.idempotency_key.in_(llaves))
        .order_by(CtaTransaccion.idempotency_key, CtaTransaccion.id_transaccion)
        .all()
    )


def _transaccion_principal(
    transacciones: list[CtaTransaccion], key: str
) -> CtaTransaccion | None:
    """La fila que guarda la llave tal cual (sin sufijo `#C`)."""
    for tx in transacciones:
        if tx.idempotency_key == key:
            return tx
    return None


def _evento_registro(db: Session, id_transaccion: str) -> dict[str, Any]:
    evento = (
        db.query(auditoria.AuditoriaEvento)
        .filter(
            auditoria.AuditoriaEvento.entidad == "cta_transaccion",
            auditoria.AuditoriaEvento.id_entidad == id_transaccion,
            auditoria.AuditoriaEvento.accion == "REGISTRAR_MOVIMIENTO",
        )
        .order_by(auditoria.AuditoriaEvento.fecha_hora.desc())
        .first()
    )
    if evento and isinstance(evento.detalle, dict):
        return evento.detalle
    return {}


def _asiento_de_transaccion(db: Session, id_transaccion: str) -> str:
    return str(_evento_registro(db, id_transaccion).get("id_asiento", ""))


def _verificar_misma_peticion(
    db: Session,
    tx_principal: CtaTransaccion,
    *,
    idempotency_key: str,
    parametros_peticion: dict[str, Any],
) -> None:
    """Lanza 409 si la petición actual no coincide con la que originó la
    `idempotency_key`. Compara la huella guardada en auditoría (o, si no
    existe, la reconstruida desde la fila de cta_transaccion)."""
    parametros_guardados = _parametros_de_transaccion(tx_principal)
    huella_guardada = (
        _evento_registro(db, tx_principal.id_transaccion).get("hash_peticion")
        or _huella(parametros_guardados)
    )
    if huella_guardada == _huella(parametros_peticion):
        return
    diferencias = {
        campo: {"original": parametros_guardados.get(campo), "solicitado": valor}
        for campo, valor in parametros_peticion.items()
        if parametros_guardados.get(campo) != valor
    }
    raise IdempotencyConflictError(idempotency_key, diferencias)


def _replay_movimiento(
    db: Session,
    transacciones: list[CtaTransaccion],
    *,
    idempotency_key: str,
    parametros_peticion: dict[str, Any],
) -> MovimientoResultado:
    tx = _transaccion_principal(transacciones, idempotency_key)
    if tx is None:
        raise ConflictError(
            "IDEMPOTENCIA_INCONSISTENTE",
            "Existe una transacción con esa llave pero sin la pata principal.",
            details={"idempotency_key": idempotency_key},
        )
    _verificar_misma_peticion(
        db, tx, idempotency_key=idempotency_key,
        parametros_peticion=parametros_peticion,
    )
    res = _resultado_desde_transaccion(tx, replay=True)
    res.id_asiento = _asiento_de_transaccion(db, tx.id_transaccion)
    return res


def _resultado_desde_transaccion(tx: CtaTransaccion, replay: bool) -> MovimientoResultado:
    return MovimientoResultado(
        id_transaccion=tx.id_transaccion,
        uuid_transaccion=tx.uuid_transaccion,
        num_cuenta=tx.num_cuenta,
        tipo_operacion=tx.tipo_operacion,
        tipo_movimiento=tx.tipo_movimiento,
        monto=tx.monto,
        moneda=tx.moneda,
        monto_moneda_base=tx.monto,  # ajustado por el llamador si hace falta
        saldo_posterior=tx.saldo_posterior,
        id_asiento="",  # recuperado por el llamador vía auditoría
        num_cuenta_contraparte=tx.num_cuenta_contraparte,
        idempotency_key=tx.idempotency_key,
        fecha_hora=tx.fecha_hora,
        replay=replay,
    )


def registrar_movimiento(
    db: Session,
    *,
    tipo_operacion: str,
    num_cuenta: str,
    monto: Decimal,
    moneda: str | None = None,
    id_canal: str,
    id_terminal: str | None = None,
    num_cuenta_contraparte: str | None = None,
    idempotency_key: str | None = None,
    actor: str = "sistema",
    correlation_id: str | None = None,
    comision: Decimal = SALDO_BASE,
    itf: Decimal = SALDO_BASE,
    retencion: Decimal = SALDO_BASE,
) -> MovimientoResultado:
    """Registra un depósito o retiro (RF-COR-06) con su asiento contable."""
    if tipo_operacion not in ("DEPOSITO", "RETIRO"):
        raise ValidationError(
            "TIPO_OPERACION_INVALIDO",
            "Para esta operación use transferir_cuentas(). "
            "Tipos admitidos: DEPOSITO, RETIRO.",
        )
    monto = D(monto)
    if monto <= SALDO_BASE:
        raise ValidationError("MONTO_INVALIDO", "El monto debe ser mayor a cero.")

    _validar_formato_llave(idempotency_key, es_transferencia=False)

    if idempotency_key:
        parametros = _parametros_criticos(
            tipo_operacion=tipo_operacion,
            num_cuenta=num_cuenta,
            num_cuenta_contraparte=num_cuenta_contraparte,
            monto=monto,
            moneda=_moneda_efectiva(db, moneda, num_cuenta),
            id_canal=id_canal,
        )
        previas = _buscar_por_idempotencia(db, idempotency_key)
        if previas:
            # Replay solo si es la MISMA petición; si no, 409 (Hallazgo #11).
            return _replay_movimiento(
                db, previas, idempotency_key=idempotency_key,
                parametros_peticion=parametros,
            )

    try:
        return _con_reintentos_deadlock(
            db,
            partial(
                _ejecutar_movimiento,
                db,
                tipo_operacion=tipo_operacion,
                num_cuenta=num_cuenta,
                monto=monto,
                moneda=moneda,
                id_canal=id_canal,
                id_terminal=id_terminal,
                num_cuenta_contraparte=num_cuenta_contraparte,
                idempotency_key=idempotency_key,
                actor=actor,
                correlation_id=correlation_id,
                comision=comision,
                itf=itf,
                retencion=retencion,
            ),
            nombre="operación de " + tipo_operacion.lower(),
        )
    except IntegrityError as exc:
        db.rollback()
        # Carrera por idempotencia: otro proceso insertó la misma llave.
        if idempotency_key:
            previas = _buscar_por_idempotencia(db, idempotency_key)
            if previas:
                return _replay_movimiento(
                    db, previas, idempotency_key=idempotency_key,
                    parametros_peticion=parametros,
                )
        raise ConflictError(
            "CONFLICTO_UNICIDAD",
            "Conflicto de unicidad al registrar el movimiento.",
            details={"motivo": str(exc.orig) if exc.orig else str(exc)},
        ) from exc
    except Exception:
        db.rollback()
        raise


def _ejecutar_movimiento(
    db: Session,
    *,
    tipo_operacion: str,
    num_cuenta: str,
    monto: Decimal,
    moneda: str | None,
    id_canal: str,
    id_terminal: str | None,
    num_cuenta_contraparte: str | None,
    idempotency_key: str | None,
    actor: str,
    correlation_id: str | None,
    comision: Decimal,
    itf: Decimal,
    retencion: Decimal,
) -> MovimientoResultado:
    canal = db.get(Canal, id_canal)
    if canal is None or not canal.activo:
        raise NotFoundError("CANAL_NO_ENCONTRADO", f"Canal {id_canal} inexistente o inactivo.")

    cuenta = (
        db.query(CuentaAhorro)
        .filter(CuentaAhorro.num_cuenta == num_cuenta)
        .with_for_update()
        .first()
    )
    if cuenta is None:
        raise NotFoundError("CUENTA_NO_ENCONTRADA", f"Cuenta {num_cuenta} no existe.")

    moneda_op = moneda or cuenta.moneda
    ahora = datetime.now()

    # Conversión con tipo de cambio oficial si difiere la moneda (RGN-10)
    tasa = tasa_vigente(db, moneda_op, cuenta.moneda, ahora.date())
    monto_cuenta = convertir(monto, tasa) if moneda_op != cuenta.moneda else monto

    es_debito = tipo_operacion == "RETIRO"
    if es_debito:
        if _cuenta_cerrada(cuenta):
            raise BlockedAccountError(num_cuenta, cuenta.estado_cuenta)
        if _cuenta_bloqueada_para_debito(cuenta):
            raise BlockedAccountError(num_cuenta, cuenta.estado_cuenta)
        # RGN-03 / RF-COR-07: saldo suficiente
        if monto_cuenta > cuenta.saldo_disponible:
            raise InsufficientFundsError(
                saldo_disponible=str(cuenta.saldo_disponible),
                monto_solicitado=str(monto_cuenta),
            )
        # RGN-04 / RF-COR-08: tope diario por canal
        control = _validar_tope_diario(db, cuenta, id_canal, monto_cuenta, ahora.date())
    else:
        if _cuenta_cerrada(cuenta):
            raise BlockedAccountError(num_cuenta, cuenta.estado_cuenta)
        control = _validar_tope_diario(db, cuenta, id_canal, monto_cuenta, ahora.date())

    # Actualización de saldos (single source of truth, RGN-02)
    if es_debito:
        cuenta.saldo_disponible = D(cuenta.saldo_disponible - monto_cuenta)
        cuenta.saldo_contable = D(cuenta.saldo_contable - monto_cuenta)
        tipo_movimiento = "D"
    else:
        cuenta.saldo_disponible = D(cuenta.saldo_disponible + monto_cuenta)
        cuenta.saldo_contable = D(cuenta.saldo_contable + monto_cuenta)
        tipo_movimiento = "C"

    # Tasa a moneda base para el asiento
    tasa_base = tasa_vigente(db, moneda_op, MONEDA_BASE, ahora.date())

    tx = CtaTransaccion(
        id_transaccion=new_uuid7(),
        uuid_transaccion=new_uuid7(),
        num_cuenta=num_cuenta,
        num_cuenta_contraparte=num_cuenta_contraparte,
        tipo_operacion=tipo_operacion,
        tipo_movimiento=tipo_movimiento,
        monto=monto,
        moneda=moneda_op,
        id_canal=id_canal,
        id_terminal=id_terminal,
        saldo_posterior=cuenta.saldo_disponible,
        comision=D(comision),
        itf=D(itf),
        retencion=D(retencion),
        estado_transaccion="APLICADA",
        idempotency_key=idempotency_key,
        fecha_valor=ahora.date(),
        fecha_hora=ahora,
    )
    db.add(tx)

    if es_debito:
        lineas = [
            contabilidad.linea(
                DEPOSITOS_AHORRO, debe=monto, moneda=moneda_op,
                tipo_cambio=tasa_base,
                importe_base=convertir(monto, tasa_base) if moneda_op != MONEDA_BASE else monto,
            ),
            contabilidad.linea(
                CAJA, haber=monto, moneda=moneda_op,
                tipo_cambio=tasa_base,
                importe_base=convertir(monto, tasa_base) if moneda_op != MONEDA_BASE else monto,
            ),
        ]
        glosa = f"Retiro {num_cuenta} por canal {id_canal}"
    else:
        lineas = [
            contabilidad.linea(
                CAJA, debe=monto, moneda=moneda_op,
                tipo_cambio=tasa_base,
                importe_base=convertir(monto, tasa_base) if moneda_op != MONEDA_BASE else monto,
            ),
            contabilidad.linea(
                DEPOSITOS_AHORRO, haber=monto, moneda=moneda_op,
                tipo_cambio=tasa_base,
                importe_base=convertir(monto, tasa_base) if moneda_op != MONEDA_BASE else monto,
            ),
        ]
        glosa = f"Depósito {num_cuenta} por canal {id_canal}"

    asiento = contabilidad.crear_asiento(db, glosa=glosa, lineas=lineas, fecha=ahora)

    if es_debito:
        _acumular_tope(
            db, control, num_cuenta=num_cuenta, id_canal=id_canal,
            monto=monto_cuenta, fecha=ahora.date(),
        )

    db.flush()

    auditoria.registrar_evento(
        db,
        modulo="CORE",
        entidad="cta_transaccion",
        id_entidad=tx.id_transaccion,
        accion="REGISTRAR_MOVIMIENTO",
        actor=actor,
        detalle={
            "id_asiento": asiento.id_asiento,
            "tipo_operacion": tipo_operacion,
            "num_cuenta": num_cuenta,
            "monto": str(monto),
            "moneda": moneda_op,
            "resultado": "APLICADA",
            "hash_peticion": _huella(
                _parametros_criticos(
                    tipo_operacion=tipo_operacion,
                    num_cuenta=num_cuenta,
                    num_cuenta_contraparte=num_cuenta_contraparte,
                    monto=monto,
                    moneda=moneda_op,
                    id_canal=id_canal,
                )
            ),
        },
        correlation_id=correlation_id,
        fecha_hora=ahora,
    )

    monto_base = (
        convertir(monto, tasa_base) if moneda_op != MONEDA_BASE else monto
    )
    return MovimientoResultado(
        id_transaccion=tx.id_transaccion,
        uuid_transaccion=tx.uuid_transaccion,
        num_cuenta=num_cuenta,
        tipo_operacion=tipo_operacion,
        tipo_movimiento=tipo_movimiento,
        monto=monto,
        moneda=moneda_op,
        monto_moneda_base=monto_base,
        saldo_posterior=cuenta.saldo_disponible,
        id_asiento=asiento.id_asiento,
        num_cuenta_contraparte=num_cuenta_contraparte,
        idempotency_key=idempotency_key,
        fecha_hora=ahora,
    )


def transferir_cuentas(
    db: Session,
    *,
    num_cuenta_origen: str,
    num_cuenta_destino: str,
    monto: Decimal,
    moneda: str | None = None,
    id_canal: str,
    id_terminal: str | None = None,
    idempotency_key: str | None = None,
    actor: str = "sistema",
    correlation_id: str | None = None,
) -> TransferenciaResultado:
    """Transferencia entre cuentas: débito origen + crédito destino en un
    solo asiento atómico de partida doble (RF-COR-06, escenario crítico
    'Transferencia entre cuentas')."""
    if num_cuenta_origen == num_cuenta_destino:
        raise ValidationError(
            "TRANSFERENCIA_MISMA_CUENTA",
            "La cuenta de origen y la de destino deben ser distintas.",
        )
    monto = D(monto)
    if monto <= SALDO_BASE:
        raise ValidationError("MONTO_INVALIDO", "El monto debe ser mayor a cero.")

    _validar_formato_llave(idempotency_key, es_transferencia=True)

    if idempotency_key:
        parametros = _parametros_criticos(
            tipo_operacion="TRANSFERENCIA",
            num_cuenta=num_cuenta_origen,
            num_cuenta_contraparte=num_cuenta_destino,
            monto=monto,
            moneda=_moneda_efectiva(db, moneda, num_cuenta_origen),
            id_canal=id_canal,
        )
        previas = _buscar_por_idempotencia(db, idempotency_key)
        if previas:
            # Replay solo si es la MISMA transferencia; si no, 409.
            return _resultado_transferencia_replay(
                db, previas, idempotency_key=idempotency_key,
                parametros_peticion=parametros,
            )

    try:
        return _con_reintentos_deadlock(
            db,
            partial(
                _ejecutar_transferencia,
                db,
                num_cuenta_origen=num_cuenta_origen,
                num_cuenta_destino=num_cuenta_destino,
                monto=monto,
                moneda=moneda,
                id_canal=id_canal,
                id_terminal=id_terminal,
                idempotency_key=idempotency_key,
                actor=actor,
                correlation_id=correlation_id,
            ),
            nombre="transferencia",
        )
    except IntegrityError as exc:
        db.rollback()
        if idempotency_key:
            previas = _buscar_por_idempotencia(db, idempotency_key)
            if previas:
                return _resultado_transferencia_replay(
                    db, previas, idempotency_key=idempotency_key,
                    parametros_peticion=parametros,
                )
        raise ConflictError(
            "CONFLICTO_UNICIDAD",
            "Conflicto de unicidad al registrar la transferencia.",
            details={"motivo": str(exc.orig) if exc.orig else str(exc)},
        ) from exc
    except Exception:
        db.rollback()
        raise


def _patas_transferencia(
    transacciones: list[CtaTransaccion], idempotency_key: str
) -> tuple[CtaTransaccion, CtaTransaccion]:
    """Identifica origen y destino de una transferencia guardada.

    Origen: llave sin sufijo y tipo_movimiento 'D'.
    Destino: llave con sufijo '#C' y tipo_movimiento 'C'.
    No se usa fecha_hora: ambas patas comparten el mismo instante.
    """
    llave_destino = idempotency_key + SUFIJO_CONTRAPARTE
    origen = next(
        (t for t in transacciones
         if t.idempotency_key == idempotency_key and t.tipo_movimiento == "D"),
        None,
    )
    destino = next(
        (t for t in transacciones
         if t.idempotency_key == llave_destino and t.tipo_movimiento == "C"),
        None,
    )
    if origen is None or destino is None:
        raise ConflictError(
            "IDEMPOTENCIA_INCONSISTENTE",
            "La transferencia asociada a la idempotency_key no tiene sus dos "
            "patas (origen 'D' y destino 'C#C') registradas correctamente.",
            details={"idempotency_key": idempotency_key},
        )
    return origen, destino


def _resultado_transferencia_replay(
    db: Session,
    transacciones: list[CtaTransaccion],
    *,
    idempotency_key: str,
    parametros_peticion: dict[str, Any],
) -> TransferenciaResultado:
    principal = _transaccion_principal(transacciones, idempotency_key)
    if principal is None:
        raise ConflictError(
            "IDEMPOTENCIA_INCONSISTENTE",
            "Existe una transacción con esa llave pero sin la pata principal.",
            details={"idempotency_key": idempotency_key},
        )
    # 1) Misma petición (tipo TRANSFERENCIA, origen, destino, monto, moneda,
    #    canal). Una llave usada por un depósito/retiro da 409 aquí.
    _verificar_misma_peticion(
        db, principal, idempotency_key=idempotency_key,
        parametros_peticion=parametros_peticion,
    )
    # 2) Patas identificadas por tipo_movimiento + sufijo, no por fecha.
    origen_tx, destino_tx = _patas_transferencia(transacciones, idempotency_key)
    origen = _resultado_desde_transaccion(origen_tx, replay=True)
    destino = _resultado_desde_transaccion(destino_tx, replay=True)
    origen.id_asiento = _asiento_de_transaccion(db, origen_tx.id_transaccion)
    destino.id_asiento = origen.id_asiento
    return TransferenciaResultado(
        origen=origen, destino=destino, id_asiento=origen.id_asiento, replay=True
    )


def _bloquear_cuentas_en_orden(db: Session, *num_cuentas: str) -> dict[str, CuentaAhorro]:
    """SELECT ... FOR UPDATE de cada cuenta, una a una, en orden ascendente
    de `num_cuenta` (orden global y determinista para todo el CORE).

    Devuelve {num_cuenta: CuentaAhorro}; las inexistentes no aparecen.
    """
    bloqueadas: dict[str, CuentaAhorro] = {}
    for num in sorted(set(num_cuentas)):
        cuenta = (
            db.query(CuentaAhorro)
            .filter(CuentaAhorro.num_cuenta == num)
            .with_for_update()
            .first()
        )
        if cuenta is not None:
            bloqueadas[num] = cuenta
    return bloqueadas


def _ejecutar_transferencia(
    db: Session,
    *,
    num_cuenta_origen: str,
    num_cuenta_destino: str,
    monto: Decimal,
    moneda: str | None,
    id_canal: str,
    id_terminal: str | None,
    idempotency_key: str | None,
    actor: str,
    correlation_id: str | None,
) -> TransferenciaResultado:
    canal = db.get(Canal, id_canal)
    if canal is None or not canal.activo:
        raise NotFoundError("CANAL_NO_ENCONTRADO", f"Canal {id_canal} inexistente o inactivo.")

    # Bloqueo pesimista en orden de num_cuenta (Hallazgo #10): se bloquea
    # SIEMPRE primero la cuenta menor y luego la mayor, sea origen o
    # destino. Dos transferencias cruzadas A->B y B->A piden el mismo primer
    # candado, así que una espera a la otra en vez de formar un ciclo.
    cuentas = _bloquear_cuentas_en_orden(db, num_cuenta_origen, num_cuenta_destino)
    cuenta_origen = cuentas.get(num_cuenta_origen)
    cuenta_destino = cuentas.get(num_cuenta_destino)
    if cuenta_origen is None:
        raise NotFoundError("CUENTA_NO_ENCONTRADA", f"Cuenta {num_cuenta_origen} no existe.")
    if cuenta_destino is None:
        raise NotFoundError("CUENTA_NO_ENCONTRADA", f"Cuenta {num_cuenta_destino} no existe.")

    if _cuenta_cerrada(cuenta_origen) or _cuenta_bloqueada_para_debito(cuenta_origen):
        raise BlockedAccountError(num_cuenta_origen, cuenta_origen.estado_cuenta)
    if _cuenta_cerrada(cuenta_destino):
        raise BlockedAccountError(num_cuenta_destino, cuenta_destino.estado_cuenta)

    moneda_op = moneda or cuenta_origen.moneda
    ahora = datetime.now()

    # Conversión de la moneda de la operación a la moneda de cada cuenta
    tasa_origen = tasa_vigente(db, moneda_op, cuenta_origen.moneda, ahora.date())
    monto_origen = (
        convertir(monto, tasa_origen) if moneda_op != cuenta_origen.moneda else monto
    )
    tasa_destino = tasa_vigente(db, moneda_op, cuenta_destino.moneda, ahora.date())
    monto_destino = (
        convertir(monto, tasa_destino) if moneda_op != cuenta_destino.moneda else monto
    )

    if monto_origen > cuenta_origen.saldo_disponible:
        raise InsufficientFundsError(
            saldo_disponible=str(cuenta_origen.saldo_disponible),
            monto_solicitado=str(monto_origen),
        )
    control = _validar_tope_diario(
        db, cuenta_origen, id_canal, monto_origen, ahora.date()
    )

    cuenta_origen.saldo_disponible = D(cuenta_origen.saldo_disponible - monto_origen)
    cuenta_origen.saldo_contable = D(cuenta_origen.saldo_contable - monto_origen)
    cuenta_destino.saldo_disponible = D(cuenta_destino.saldo_disponible + monto_destino)
    cuenta_destino.saldo_contable = D(cuenta_destino.saldo_contable + monto_destino)

    tx_origen = CtaTransaccion(
        id_transaccion=new_uuid7(),
        uuid_transaccion=new_uuid7(),
        num_cuenta=num_cuenta_origen,
        num_cuenta_contraparte=num_cuenta_destino,
        tipo_operacion="TRANSFERENCIA",
        tipo_movimiento="D",
        monto=monto,
        moneda=moneda_op,
        id_canal=id_canal,
        id_terminal=id_terminal,
        saldo_posterior=cuenta_origen.saldo_disponible,
        comision=SALDO_BASE,
        itf=SALDO_BASE,
        retencion=SALDO_BASE,
        estado_transaccion="APLICADA",
        idempotency_key=idempotency_key,
        fecha_valor=ahora.date(),
        fecha_hora=ahora,
    )
    tx_destino = CtaTransaccion(
        id_transaccion=new_uuid7(),
        uuid_transaccion=new_uuid7(),
        num_cuenta=num_cuenta_destino,
        num_cuenta_contraparte=num_cuenta_origen,
        tipo_operacion="TRANSFERENCIA",
        tipo_movimiento="C",
        monto=monto,
        moneda=moneda_op,
        id_canal=id_canal,
        id_terminal=id_terminal,
        saldo_posterior=cuenta_destino.saldo_disponible,
        comision=SALDO_BASE,
        itf=SALDO_BASE,
        retencion=SALDO_BASE,
        estado_transaccion="APLICADA",
        idempotency_key=(
            idempotency_key + SUFIJO_CONTRAPARTE if idempotency_key else None
        ),
        fecha_valor=ahora.date(),
        fecha_hora=ahora,
    )
    db.add(tx_origen)
    db.add(tx_destino)

    tasa_base_o = tasa_vigente(db, cuenta_origen.moneda, MONEDA_BASE, ahora.date())
    tasa_base_d = tasa_vigente(db, cuenta_destino.moneda, MONEDA_BASE, ahora.date())
    base_o = (
        convertir(monto_origen, tasa_base_o)
        if cuenta_origen.moneda != MONEDA_BASE else monto_origen
    )
    base_d = (
        convertir(monto_destino, tasa_base_d)
        if cuenta_destino.moneda != MONEDA_BASE else monto_destino
    )

    lineas = [
        contabilidad.linea(
            DEPOSITOS_AHORRO, debe=monto_origen, moneda=cuenta_origen.moneda,
            tipo_cambio=tasa_base_o, importe_base=base_o,
        ),
        contabilidad.linea(
            DEPOSITOS_AHORRO, haber=monto_destino, moneda=cuenta_destino.moneda,
            tipo_cambio=tasa_base_d, importe_base=base_d,
        ),
    ]
    asiento = contabilidad.crear_asiento(
        db,
        glosa=(
            f"Transferencia {num_cuenta_origen} -> {num_cuenta_destino} "
            f"por canal {id_canal}"
        ),
        lineas=lineas,
        fecha=ahora,
    )

    _acumular_tope(
        db, control, num_cuenta=num_cuenta_origen, id_canal=id_canal,
        monto=monto_origen, fecha=ahora.date(),
    )
    db.flush()

    # Huella de la petición para validar replays (Hallazgo #11).
    hash_peticion = _huella(
        _parametros_criticos(
            tipo_operacion="TRANSFERENCIA",
            num_cuenta=num_cuenta_origen,
            num_cuenta_contraparte=num_cuenta_destino,
            monto=monto,
            moneda=moneda_op,
            id_canal=id_canal,
        )
    )
    for tx, cuenta, monto_tx, tasa_b, base in (
        (tx_origen, cuenta_origen, monto_origen, tasa_base_o, base_o),
        (tx_destino, cuenta_destino, monto_destino, tasa_base_d, base_d),
    ):
        auditoria.registrar_evento(
            db,
            modulo="CORE",
            entidad="cta_transaccion",
            id_entidad=tx.id_transaccion,
            accion="REGISTRAR_MOVIMIENTO",
            actor=actor,
            detalle={
                "id_asiento": asiento.id_asiento,
                "tipo_operacion": "TRANSFERENCIA",
                "num_cuenta": cuenta.num_cuenta,
                "monto": str(monto_tx),
                "moneda": cuenta.moneda,
                "resultado": "APLICADA",
                "hash_peticion": hash_peticion,
            },
            correlation_id=correlation_id,
            fecha_hora=ahora,
        )

    origen_res = MovimientoResultado(
        id_transaccion=tx_origen.id_transaccion,
        uuid_transaccion=tx_origen.uuid_transaccion,
        num_cuenta=num_cuenta_origen,
        tipo_operacion="TRANSFERENCIA",
        tipo_movimiento="D",
        monto=monto,
        moneda=moneda_op,
        monto_moneda_base=base_o,
        saldo_posterior=cuenta_origen.saldo_disponible,
        id_asiento=asiento.id_asiento,
        num_cuenta_contraparte=num_cuenta_destino,
        idempotency_key=idempotency_key,
        fecha_hora=ahora,
    )
    destino_res = MovimientoResultado(
        id_transaccion=tx_destino.id_transaccion,
        uuid_transaccion=tx_destino.uuid_transaccion,
        num_cuenta=num_cuenta_destino,
        tipo_operacion="TRANSFERENCIA",
        tipo_movimiento="C",
        monto=monto,
        moneda=moneda_op,
        monto_moneda_base=base_d,
        saldo_posterior=cuenta_destino.saldo_disponible,
        id_asiento=asiento.id_asiento,
        num_cuenta_contraparte=num_cuenta_origen,
        idempotency_key=(idempotency_key + SUFIJO_CONTRAPARTE if idempotency_key else None),
        fecha_hora=ahora,
    )
    return TransferenciaResultado(
        origen=origen_res, destino=destino_res, id_asiento=asiento.id_asiento
    )
