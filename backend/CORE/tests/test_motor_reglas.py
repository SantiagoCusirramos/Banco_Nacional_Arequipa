"""Tests del motor de reglas de evaluación (sin BD)."""

from decimal import Decimal

from CORE.models import EvaRegla
from CORE.services.creditossvc import _evaluar_regla, _riesgo_desde_puntaje


def _regla(**kw) -> EvaRegla:
    defaults = dict(
        id_regla="r1",
        nombre="test",
        variable="ratio_capacidad",
        operador="MAYOR",
        valor_min=Decimal("0.4"),
        valor_max=None,
        resultado="OBSERVAR",
        peso=Decimal("1"),
        activa=True,
    )
    defaults.update(kw)
    return EvaRegla(**defaults)


def test_mayor():
    r = _regla(operador="MAYOR", valor_min=Decimal("0.4"))
    assert not _evaluar_regla(r, {"ratio_capacidad": Decimal("0.3")})
    assert _evaluar_regla(r, {"ratio_capacidad": Decimal("0.5")})


def test_entre():
    r = _regla(operador="ENTRE", valor_min=Decimal("10"), valor_max=Decimal("20"))
    assert _evaluar_regla(r, {"ratio_capacidad": Decimal("15")})
    assert not _evaluar_regla(r, {"ratio_capacidad": Decimal("25")})


def test_excluye():
    r = _regla(variable="dias_mayor_mora", operador="EXCLUYE",
               valor_min=Decimal("1"), valor_max=None)
    assert _evaluar_regla(r, {"dias_mayor_mora": Decimal("5")})
    assert not _evaluar_regla(r, {"dias_mayor_mora": Decimal("0")})


def test_regla_inactiva_no_aplica():
    r = _regla(activa=False)
    assert not _evaluar_regla(r, {"ratio_capacidad": Decimal("99")})


def test_variable_ausente():
    r = _regla()
    assert not _evaluar_regla(r, {})


def test_riesgo_desde_puntaje():
    assert _riesgo_desde_puntaje(90) == "BAJO"
    assert _riesgo_desde_puntaje(60) == "MEDIO"
    assert _riesgo_desde_puntaje(30) == "ALTO"
    assert _riesgo_desde_puntaje(10) == "MUY_ALTO"
