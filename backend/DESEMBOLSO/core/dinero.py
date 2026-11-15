"""Importes como Decimal con dos decimales; nunca float (RT-03)."""
from decimal import ROUND_HALF_UP, Decimal

CENTIMO = Decimal("0.01")


def a_decimal(valor: str | int | Decimal) -> Decimal:
    if isinstance(valor, float):
        raise TypeError("Los importes no se manejan como float")
    return Decimal(str(valor)).quantize(CENTIMO, rounding=ROUND_HALF_UP)


def formatear(valor: Decimal) -> str:
    return f"{a_decimal(valor):.2f}"
