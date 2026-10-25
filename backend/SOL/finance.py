"""Calendario preliminar con Decimal, basado en la fórmula del CORE revisado."""

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP, localcontext

CENT = Decimal("0.01")


def money(value: Decimal) -> str:
    return format(value.quantize(CENT, rounding=ROUND_HALF_UP), ".2f")


def calendar(
    amount: Decimal, tea: Decimal, months: int, start: date, days: int = 30
) -> dict:
    """TEA efectiva → tasa periódica equivalente; vencimientos cada N días.

    La tasa mensual mantiene la conversión del CORE para periodos de 30 días.
    Si se cambia la duración del periodo, usa año comercial de 360 días como
    convención explícita de la demo (debe ratificarse con Créditos).
    El saldo residual se ajusta en la última cuota; nunca se usa float.
    """
    with localcontext() as context:
        context.prec = 36
        rate = (1 + tea) ** (Decimal(days) / Decimal(360)) - 1
        fixed = (
            amount / months
            if not rate
            else amount * rate / (1 - (1 + rate) ** (-months))
        )
        fixed = fixed.quantize(CENT, rounding=ROUND_HALF_UP)
        balance = amount
        rows = []
        for index in range(1, months + 1):
            interest = (balance * rate).quantize(CENT, rounding=ROUND_HALF_UP)
            capital = balance if index == months else min(balance, fixed - interest)
            end = balance - capital
            rows.append(
                {
                    "numero_cuota": index,
                    "fecha_vencimiento": (
                        start + timedelta(days=days * index)
                    ).isoformat(),
                    "saldo_inicial": money(balance),
                    "amortizacion": money(capital),
                    "interes": money(interest),
                    "cuota_total": money(capital + interest),
                    "saldo_final": money(end),
                }
            )
            balance = end
        return {
            "estado": "PRELIMINAR",
            "cuotas": rows,
            "cuota_referencial": money(fixed),
            "intereses_totales": money(
                sum((Decimal(r["interes"]) for r in rows), Decimal(0))
            ),
            "total_pagar": money(
                sum((Decimal(r["cuota_total"]) for r in rows), Decimal(0))
            ),
        }
