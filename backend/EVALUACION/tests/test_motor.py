"""Regla provisional RN-EVA-002-P: se conservó la del equipo de Evaluación, en Decimal."""
from decimal import Decimal

import pytest

from EVALUACION import motor

MONTO = Decimal("15000.00")


@pytest.mark.parametrize(("ingreso", "deuda", "riesgo", "esperado"), [
    ("5000.00", "0.00", "BUENO", "APROBADO"),       # límite 21000.00: 71.43 %
    ("4000.00", "0.00", "BUENO", "OBSERVADO"),      # límite 16800.00: 89.29 %
    ("3000.00", "0.00", "BUENO", "RECHAZADO"),      # límite 12600.00: 119.05 %
    ("5000.00", "1750.00", "BUENO", "RECHAZADO"),   # sin capacidad de pago
    ("6000.00", "0.00", "REGULAR", "APROBADO"),     # 2100 x 12 x 0.75 = 18900.00: 79.37 %
    ("6000.00", "0.00", "ALTO", "RECHAZADO"),       # 2100 x 12 x 0.40 = 10080.00: 148.81 %
])
def test_resultado_segun_capacidad_y_riesgo(ingreso, deuda, riesgo, esperado):
    assert motor.evaluar(MONTO, 12, Decimal(ingreso), Decimal(deuda), riesgo).resultado == esperado


def test_limite_ratio_y_motivo_exactos():
    r = motor.evaluar(MONTO, 12, Decimal("5000.00"), Decimal("0"), "BUENO")
    assert (r.limite, r.ratio, r.score) == (Decimal("21000.00"), Decimal("0.7143"), 850)
    assert r.motivo == "Monto / límite: 71.43 %"


def test_sin_capacidad_no_hay_ratio():
    r = motor.evaluar(MONTO, 12, Decimal("1000.00"), Decimal("500.00"), "BUENO")
    assert (r.resultado, r.limite, r.ratio, r.motivo) == (
        "RECHAZADO", Decimal("0.00"), None, "Capacidad disponible insuficiente")


@pytest.mark.parametrize(("monto", "esperado"), [
    ("15000.00", "APROBADO"),     # exactamente 80 % aprueba
    ("15000.01", "OBSERVADO"),    # un céntimo más ya lo revisa el analista
    ("18750.00", "OBSERVADO"),    # exactamente 100 % todavía no se rechaza
    ("18750.01", "RECHAZADO"),
])
def test_fronteras_de_la_regla(monto, esperado):
    # Ingreso 10000.00 y deuda 1937.50: capacidad 1562.50 y límite 18750.00 a 12 meses.
    assert motor.evaluar(Decimal(monto), 12, Decimal("10000.00"), Decimal("1937.50"), "BUENO").resultado == esperado
