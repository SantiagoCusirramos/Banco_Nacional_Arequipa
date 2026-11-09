"""Depósitos, retiros y transferencias sobre los procedimientos de cuentas.

Saldos, topes, canal, estado, auditoría y bloqueo ordenado de cuentas viven en la
base. Aquí queda la huella de idempotencia y el periodo contable.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from COREDB.database import llamar
from COREDB.errores import ErrorCoreDb
from COREDB.transacciones import con_reintentos


@dataclass(frozen=True)
class Movimiento:
    uuid_transaccion: uuid.UUID
    repetido: bool


@dataclass(frozen=True)
class Transferencia:
    uuid_debito: uuid.UUID
    uuid_abono: uuid.UUID
    repetido: bool


def _huella(**parametros: object) -> str:
    return hashlib.sha256(
        json.dumps(parametros, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _uuid(valor: bytes | None) -> uuid.UUID:
    if valor is None:
        raise ErrorCoreDb(
            "BNA-IDEMPOTENCIA", "La llave no tiene una operación registrada.", 409
        )
    return uuid.UUID(bytes=valor)


def _exigir_periodo(db: Session, llave: str | None) -> None:
    """La base rechaza un periodo cerrado; que no exista ninguno se rechaza aquí. Una
    llave ya usada no opera, sino que devuelve su resultado, y no necesita periodo."""
    if llave is not None and db.execute(
        text("SELECT 1 FROM cuentas.idempotencia_movimiento WHERE llave = :llave"),
        {"llave": llave},
    ).first():
        return
    existe = db.execute(
        text(
            "SELECT 1 FROM core.periodo_contable WHERE "
            "core.fn_fecha_negocio(UTC_TIMESTAMP(6)) "
            "BETWEEN fecha_inicio AND fecha_fin LIMIT 1"
        )
    ).first()
    if existe is None:
        raise ErrorCoreDb(
            "PERIODO_CONTABLE_NO_ENCONTRADO", "No hay periodo contable para la fecha de negocio."
        )


def registrar(
    db: Session,
    *,
    num_cuenta: str,
    tipo: str,
    monto: Decimal,
    glosa: str,
    id_canal: str,
    idempotency_key: str | None,
    correlation_id: uuid.UUID,
    actor: str,
) -> Movimiento:
    huella = _huella(
        num_cuenta=num_cuenta, tipo=tipo, monto=f"{monto:.2f}", glosa=glosa, id_canal=id_canal
    )

    def operacion() -> Movimiento:
        _exigir_periodo(db, idempotency_key)
        uuid_mov, repetido = llamar(
            db, "cuentas.registrar_movimiento",
            num_cuenta, tipo, monto, glosa, id_canal, correlation_id, idempotency_key, huella,
            actor,
            salidas=2,
        )
        return Movimiento(_uuid(uuid_mov), bool(repetido))

    return con_reintentos(db, operacion, nombre="registrar_movimiento")


def transferir(
    db: Session,
    *,
    origen: str,
    destino: str,
    monto: Decimal,
    glosa: str,
    id_canal: str,
    idempotency_key: str | None,
    correlation_id: uuid.UUID,
    actor: str,
) -> Transferencia:
    huella = _huella(
        origen=origen, destino=destino, monto=f"{monto:.2f}", glosa=glosa, id_canal=id_canal
    )

    def operacion() -> Transferencia:
        _exigir_periodo(db, idempotency_key)
        debito, abono, repetido = llamar(
            db, "cuentas.registrar_transferencia",
            origen, destino, monto, glosa, id_canal, correlation_id, idempotency_key, huella,
            actor,
            salidas=3,
        )
        return Transferencia(_uuid(debito), _uuid(abono), bool(repetido))

    return con_reintentos(db, operacion, nombre="registrar_transferencia")
