"""Excepciones de negocio del módulo CORE.

Todas heredan de CoreError y llevan un `code` catalogado para que el
Bus de Servicios y los canales puedan reaccionar programáticamente
(RNF-29: mensajes de error comprensibles y accionables).
"""

from typing import Any


class CoreError(Exception):
    """Error de negocio base del CORE."""

    def __init__(self, code: str, message: str, status_code: int = 400,
                 details: dict[str, Any] | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(CoreError):
    def __init__(self, code: str, message: str,
                 details: dict[str, Any] | None = None):
        super().__init__(code, message, status_code=404, details=details)


class ConflictError(CoreError):
    def __init__(self, code: str, message: str,
                 details: dict[str, Any] | None = None):
        super().__init__(code, message, status_code=409, details=details)


class IdempotencyConflictError(ConflictError):
    """RF-COR-11 / RGN-06: la `idempotency_key` ya fue usada por una
    operación con parámetros distintos (cuenta, monto, tipo, destino...).
    Se responde 409 en lugar de devolver el resultado de otra operación."""

    def __init__(self, idempotency_key: str, diferencias: dict[str, Any]):
        super().__init__(
            "IDEMPOTENCY_KEY_REUTILIZADA",
            "La idempotency_key ya fue usada por una operación con "
            "parámetros distintos. Use una llave nueva para esta operación.",
            details={
                "idempotency_key": idempotency_key,
                "diferencias": diferencias,
            },
        )


class ConcurrencyError(CoreError):
    """La operación no pudo completarse por contención de bloqueos
    (deadlock) tras agotar los reintentos automáticos. Es seguro
    reintentar con la misma `idempotency_key`."""

    def __init__(self, operacion: str, intentos: int):
        super().__init__(
            "CONCURRENCIA_REINTENTOS_AGOTADOS",
            f"No se pudo completar la {operacion} por alta concurrencia "
            "sobre las cuentas involucradas. Reintente en unos segundos.",
            status_code=503,
            details={"operacion": operacion, "intentos": intentos},
        )


class ValidationError(CoreError):
    def __init__(self, code: str, message: str,
                 details: dict[str, Any] | None = None):
        super().__init__(code, message, status_code=422, details=details)


class InsufficientFundsError(CoreError):
    def __init__(self, saldo_disponible: str, monto_solicitado: str):
        super().__init__(
            "SALDO_INSUFICIENTE",
            "El importe excede el saldo disponible de la cuenta de origen.",
            status_code=422,
            details={
                "saldo_disponible": saldo_disponible,
                "monto_solicitado": monto_solicitado,
            },
        )


class DailyLimitExceededError(CoreError):
    def __init__(self, tope: str, acumulado: str, monto_solicitado: str,
                 regla: str | None = None):
        super().__init__(
            "TOPE_DIARIO_EXCEDIDO",
            "El importe excede el tope diario vigente para la cuenta y el canal.",
            status_code=422,
            details={
                "tope_diario": tope,
                "monto_acumulado": acumulado,
                "monto_solicitado": monto_solicitado,
                "regla_negocio": regla,
            },
        )


class BlockedAccountError(CoreError):
    def __init__(self, num_cuenta: str, estado: str):
        super().__init__(
            "CUENTA_NO_OPERATIVA",
            f"La cuenta {num_cuenta} está en estado {estado} "
            "y no puede originar operaciones de débito (RGN-09).",
            status_code=422,
            details={"num_cuenta": num_cuenta, "estado_cuenta": estado},
        )


class ExchangeRateNotFoundError(CoreError):
    def __init__(self, origen: str, destino: str, fecha: str):
        super().__init__(
            "TIPO_CAMBIO_NO_ENCONTRADO",
            f"No existe tipo de cambio oficial {origen}->{destino} "
            f"vigente a la fecha {fecha}.",
            status_code=422,
            details={
                "moneda_origen": origen,
                "moneda_destino": destino,
                "fecha": fecha,
            },
        )
