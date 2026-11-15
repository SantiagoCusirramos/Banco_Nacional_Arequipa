"""Regla provisional de evaluación RN-EVA-002-P del equipo de Evaluación (demo v1).

Se conserva tal como la definió ese equipo; solo se trasladó a Decimal de punta a punta.
Capacidad = 35 % del ingreso mensual menos la deuda mensual; límite = capacidad x plazo x
factor de riesgo. Monto / límite hasta 80 % aprueba, hasta 100 % queda para el analista y
por encima rechaza. No es una política de riesgo aprobada.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from .comun import CENTIMO, CUATRO_DECIMALES

REGLA = "RN-EVA-002-P · demo v1"
SCORE = {"BUENO": 850, "REGULAR": 650, "ALTO": 400}
FACTOR = {"BUENO": Decimal("1"), "REGULAR": Decimal("0.75"), "ALTO": Decimal("0.4")}
PROPORCION_CUOTA = Decimal("0.35")
UMBRAL_REVISION = Decimal("0.8")


@dataclass(frozen=True)
class ResultadoMotor:
    resultado: str          # APROBADO, OBSERVADO (lo decide el analista) o RECHAZADO
    score: int
    limite: Decimal
    ratio: Decimal | None   # monto / límite, con cuatro decimales
    motivo: str


def evaluar(monto: Decimal, plazo_meses: int, ingreso: Decimal, deuda: Decimal, riesgo: str) -> ResultadoMotor:
    capacidad = max(Decimal(0), ingreso * PROPORCION_CUOTA - deuda)
    limite = (capacidad * plazo_meses * FACTOR[riesgo]).quantize(CENTIMO, rounding=ROUND_HALF_UP)
    if limite <= 0:
        return ResultadoMotor("RECHAZADO", SCORE[riesgo], limite, None, "Capacidad disponible insuficiente")
    ratio = monto / limite
    if ratio > 1:
        resultado = "RECHAZADO"
    elif ratio > UMBRAL_REVISION:
        resultado = "OBSERVADO"
    else:
        resultado = "APROBADO"
    return ResultadoMotor(resultado, SCORE[riesgo], limite,
                          ratio.quantize(CUATRO_DECIMALES, rounding=ROUND_HALF_UP),
                          f"Monto / límite: {ratio * 100:.2f} %")
