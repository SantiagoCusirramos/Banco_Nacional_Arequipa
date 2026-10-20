"""Utilidades monetarias. Regla del proyecto: montos siempre Decimal(15,2),
nunca float (Documents/01-stack-tecnologico.md)."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

MONEDA_BASE = "PEN"  # moneda base contable del banco
DOS_DECIMALES = Decimal("0.01")
CERO = Decimal("0.00")


def D(valor) -> Decimal:
    """Convierte a Decimal de 2 decimales con redondeo bancario (half-up)."""
    if isinstance(valor, Decimal):
        dec = valor
    else:
        try:
            dec = Decimal(str(valor))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValueError(f"Monto inválido: {valor!r}") from exc
    return dec.quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)


def convertir(monto: Decimal, tasa: Decimal) -> Decimal:
    """Convierte un monto aplicando una tasa de cambio (sin redondeo intermedio)."""
    return (monto * tasa).quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)


def convertir_a_base(monto: Decimal, moneda: str, tasa: Decimal,
                     moneda_base: str = MONEDA_BASE) -> Decimal:
    """Importe en moneda base para el asiento contable (asiento_detalle)."""
    if moneda == moneda_base:
        return D(monto)
    return convertir(monto, tasa)


def tope_de(tope: Decimal | None, acumulado: Decimal, monto: Decimal) -> bool:
    """True si el monto cabe dentro del tope diario.

    tope=None significa sin límite configurado (limite_canal.monto_maximo_diario
    nullable en el esquema).
    """
    if tope is None:
        return True
    return (D(acumulado) + D(monto)) <= D(tope)
