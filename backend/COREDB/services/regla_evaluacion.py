"""Fórmula de la regla provisional RN-EVA-002-P del equipo de Evaluación.

Portada sin cambios de backend/EVALUACION/motor.py (#70, Rodrigoss06): capacidad = 35 % del
ingreso mensual menos la deuda mensual; límite = capacidad × plazo × factor de riesgo,
redondeado al céntimo. COREDB calcula el score y el límite; el resultado lo decide la base
con los umbrales de creditos.regla_evaluacion (80 % y 100 %), para que haya una sola copia
de ellos. No es una política de riesgo aprobada.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENTIMO = Decimal("0.01")
CUATRO_DECIMALES = Decimal("0.0001")
SCORE = {"BUENO": 850, "REGULAR": 650, "ALTO": 400}
FACTOR = {"BUENO": Decimal("1"), "REGULAR": Decimal("0.75"), "ALTO": Decimal("0.4")}
PROPORCION_CUOTA = Decimal("0.35")


@dataclass(frozen=True)
class Calculo:
    score: int
    limite: Decimal
    ratio: Decimal | None  # monto / límite con cuatro decimales; None si no hay capacidad


def calcular(monto: Decimal, plazo_meses: int, ingreso: Decimal, deuda: Decimal, riesgo: str) -> Calculo:
    capacidad = max(Decimal(0), ingreso * PROPORCION_CUOTA - deuda)
    limite = (capacidad * plazo_meses * FACTOR[riesgo]).quantize(CENTIMO, rounding=ROUND_HALF_UP)
    if limite <= 0:
        return Calculo(SCORE[riesgo], Decimal("0.00"), None)
    ratio = (monto / limite).quantize(CUATRO_DECIMALES, rounding=ROUND_HALF_UP)
    return Calculo(SCORE[riesgo], limite, ratio)
