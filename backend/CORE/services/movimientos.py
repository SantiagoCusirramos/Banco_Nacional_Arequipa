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
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from CORE.exceptions import (
    BlockedAccountError,
    ConflictError,
    DailyLimitExceededError,
    ExchangeRateNotFoundError,
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


def _buscar_por_idempotencia(db: Session, key: str) -> list[CtaTransaccion]:
    llaves = (key, key + SUFIJO_CONTRAPARTE)
    return (
        db.query(CtaTransaccion)
        .filter(CtaTransaccion.idempotency_key.in_(llaves))
        .order_by(CtaTransaccion.fecha_hora)
        .all()
    )


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


def _asiento_de_transaccion(db: Session, id_transaccion: str) -> str:
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
    if evento and evento.detalle:
        return str(evento.detalle.get("id_asiento", ""))
    return ""


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

    if idempotency_key:
        previas = _buscar_por_idempotencia(db, idempotency_key)
        if previas:
            tx = previas[0]
            res = _resultado_desde_transaccion(tx, replay=True)
            res.id_asiento = _asiento_de_transaccion(db, tx.id_transaccion)
            return res

    try:
        resultado = _ejecutar_movimiento(
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
        )
        db.commit()
        return resultado
    except IntegrityError as exc:
        db.rollback()
        # Carrera por idempotencia: otro proceso insertó la misma llave.
        if idempotency_key:
            previas = _buscar_por_idempotencia(db, idempotency_key)
            if previas:
                tx = previas[0]
                res = _resultado_desde_transaccion(tx, replay=True)
                res.id_asiento = _asiento_de_transaccion(db, tx.id_transaccion)
                return res
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

    if idempotency_key:
        previas = _buscar_por_idempotencia(db, idempotency_key)
        if previas:
            return _resultado_transferencia_replay(db, previas)

    try:
        resultado = _ejecutar_transferencia(
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
        )
        db.commit()
        return resultado
    except IntegrityError as exc:
        db.rollback()
        if idempotency_key:
            previas = _buscar_por_idempotencia(db, idempotency_key)
            if previas:
                return _resultado_transferencia_replay(db, previas)
        raise ConflictError(
            "CONFLICTO_UNICIDAD",
            "Conflicto de unicidad al registrar la transferencia.",
            details={"motivo": str(exc.orig) if exc.orig else str(exc)},
        ) from exc
    except Exception:
        db.rollback()
        raise


def _resultado_transferencia_replay(
    db: Session, transacciones: list[CtaTransaccion]
) -> TransferenciaResultado:
    origen_tx = transacciones[0]
    destino_tx = transacciones[1] if len(transacciones) > 1 else origen_tx
    origen = _resultado_desde_transaccion(origen_tx, replay=True)
    destino = _resultado_desde_transaccion(destino_tx, replay=True)
    origen.id_asiento = _asiento_de_transaccion(db, origen_tx.id_transaccion)
    destino.id_asiento = origen.id_asiento
    return TransferenciaResultado(
        origen=origen, destino=destino, id_asiento=origen.id_asiento, replay=True
    )


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

    # Bloqueo pesimista en orden alfabético de num_cuenta para evitar
    # deadlocks entre transferencias cruzadas concurrentes.
    primer, segundo = sorted([num_cuenta_origen, num_cuenta_destino])
    cuenta_origen = (
        db.query(CuentaAhorro)
        .filter(CuentaAhorro.num_cuenta == num_cuenta_origen)
        .with_for_update()
        .first()
    )
    cuenta_destino = (
        db.query(CuentaAhorro)
        .filter(CuentaAhorro.num_cuenta == num_cuenta_destino)
        .with_for_update()
        .first()
    )
    if cuenta_origen is None:
        raise NotFoundError("CUENTA_NO_ENCONTRADA", f"Cuenta {num_cuenta_origen} no existe.")
    if cuenta_destino is None:
        raise NotFoundError("CUENTA_NO_ENCONTRADA", f"Cuenta {num_cuenta_destino} no existe.")
    _ = primer, segundo  # orden ya aplicado por la secuencia de queries

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
