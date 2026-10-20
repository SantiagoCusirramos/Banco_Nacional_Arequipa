from decimal import Decimal

from CORE.services.creditossvc import (
    generar_calendario_frances,
    tasa_mensual_desde_tea,
)
from datetime import date


def test_tasa_mensual_desde_tea():
    # TEA 24% -> mensual ~1.7777%
    i = tasa_mensual_desde_tea(Decimal("0.24"))
    assert Decimal("0.017") < i < Decimal("0.019")


def test_calendario_frances_cuadra():
    monto = Decimal("10000.00")
    tea = Decimal("0.24")
    cuotas = generar_calendario_frances(monto, tea, 12, date(2026, 1, 15))
    assert len(cuotas) == 12
    # La suma de amortizaciones debe recuperar el capital
    total_amort = sum((c["amortizacion"] for c in cuotas), start=Decimal("0"))
    assert total_amort == monto
    # Saldo final en cero
    assert cuotas[-1]["saldo_final"] == Decimal("0.00")
    # Todas las cuotas (excepto la última ajustada) son iguales
    assert cuotas[0]["cuota_total"] == cuotas[1]["cuota_total"]


def test_calendario_tasa_cero():
    cuotas = generar_calendario_frances(
        Decimal("1200.00"), Decimal("0"), 12, date(2026, 1, 1)
    )
    assert all(c["interes"] == Decimal("0.00") for c in cuotas)
    assert cuotas[0]["cuota_total"] == Decimal("100.00")
