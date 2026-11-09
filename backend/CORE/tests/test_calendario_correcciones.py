"""Pruebas de las correcciones del calendario de créditos (sin BD).

Cubren los hallazgos #4, #5 y #6 del Informe de Errores BNA (22/oct/2026).
Los nombres de TestCalendario coinciden con los criterios de aceptación de
TAREAS_POR_INTEGRANTE.md (Leonardo Lonasco, Actividad 1).
"""

from datetime import date
from decimal import Decimal, localcontext

import pytest

from CORE.exceptions import ValidationError
from CORE.services.creditossvc import (
    generar_calendario_frances,
    tasa_mensual_desde_tea,
)


def _mensual_esperada(tea: str) -> Decimal:
    """Cálculo independiente de (1 + TEA)^(1/12) − 1 con alta precisión."""
    with localcontext() as ctx:
        ctx.prec = 34
        return (Decimal(1) + Decimal(tea)) ** (Decimal(1) / Decimal(12)) - Decimal(1)


class TestCalendario:
    # ---------------------------------------------------------------- #4
    def test_tea_no_se_redondea_a_2_decimales(self):
        # 18.5 % debe calcularse como 18.5 %, no como 19 %
        i = tasa_mensual_desde_tea(Decimal("0.185"))
        assert abs(i - _mensual_esperada("0.185")) < Decimal("1e-20")
        assert abs(i - _mensual_esperada("0.19")) > Decimal("0.0003")
        # La TEA implícita reconstruida es la contratada
        assert abs((1 + i) ** 12 - 1 - Decimal("0.185")) < Decimal("1e-20")

    @pytest.mark.parametrize("tea", ["0.1050", "0.125", "0.1249", "0.0001", "0.2200"])
    def test_tea_con_mas_de_dos_decimales_se_respeta(self, tea):
        assert abs(tasa_mensual_desde_tea(Decimal(tea)) - _mensual_esperada(tea)) < Decimal("1e-20")

    def test_cuota_hipotecario_tea_10_50(self):
        # Regresión con valor calculado de forma independiente:
        # S/ 200 000, TEA 10.50 %, 240 cuotas -> S/ 1 933.51.
        # Con el error anterior (TEA redondeada a 11 %) salía S/ 1 994.28.
        cuotas = generar_calendario_frances(
            Decimal("200000"), Decimal("0.1050"), 240, date(2026, 1, 15)
        )
        assert cuotas[0]["cuota_total"] == Decimal("1933.51")

    def test_tea_en_porcentaje_es_rechazada(self):
        # Error típico: enviar 18.5 (porcentaje) en vez de 0.185 (fracción)
        with pytest.raises(ValidationError) as exc:
            tasa_mensual_desde_tea(Decimal("18.5"))
        assert exc.value.code == "TEA_FUERA_DE_RANGO"

    @pytest.mark.parametrize("tea", [Decimal("-0.01"), "abc", None, float("nan")])
    def test_tea_invalida_es_rechazada(self, tea):
        with pytest.raises(ValidationError):
            tasa_mensual_desde_tea(tea)

    # ---------------------------------------------------------------- #5
    @pytest.mark.parametrize("tea", [Decimal("0"), Decimal("0.20")])
    def test_cuotas_cero_valida_entrada(self, tea):
        with pytest.raises(ValidationError) as exc:
            generar_calendario_frances(Decimal("1000"), tea, 0, date(2026, 1, 1))
        assert exc.value.code == "NUMERO_CUOTAS_INVALIDO"

    def test_cuotas_negativas_rechazadas(self):
        with pytest.raises(ValidationError) as exc:
            generar_calendario_frances(Decimal("1000"), Decimal("0.20"), -3, date(2026, 1, 1))
        assert exc.value.code == "NUMERO_CUOTAS_INVALIDO"

    @pytest.mark.parametrize("monto", [Decimal("-1000"), Decimal("0"), Decimal("0.004")])
    def test_monto_negativo_rechazado(self, monto):
        # 0.004 se redondea a 0.00 céntimos: tampoco es un crédito válido
        with pytest.raises(ValidationError) as exc:
            generar_calendario_frances(monto, Decimal("0.20"), 6, date(2026, 1, 1))
        assert exc.value.code == "MONTO_INVALIDO"

    def test_numero_cuotas_no_entero_rechazado(self):
        with pytest.raises(ValidationError):
            generar_calendario_frances(Decimal("1000"), Decimal("0.20"), 6.5, date(2026, 1, 1))

    # ---------------------------------------------------------------- #6
    def test_vencimientos_mensuales_calendario(self):
        cuotas = generar_calendario_frances(
            Decimal("1000"), Decimal("0.20"), 13, date(2026, 1, 31)
        )
        assert [c["fecha_vencimiento"] for c in cuotas] == [
            date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30),
            date(2026, 5, 31), date(2026, 6, 30), date(2026, 7, 31),
            date(2026, 8, 31), date(2026, 9, 30), date(2026, 10, 31),
            date(2026, 11, 30), date(2026, 12, 31), date(2027, 1, 31),
            date(2027, 2, 28),
        ]

    def test_vencimientos_anio_bisiesto(self):
        cuotas = generar_calendario_frances(
            Decimal("1000"), Decimal("0.20"), 2, date(2028, 1, 31)
        )
        assert cuotas[0]["fecha_vencimiento"] == date(2028, 2, 29)
        assert cuotas[1]["fecha_vencimiento"] == date(2028, 3, 31)

    def test_ningun_mes_se_salta(self):
        cuotas = generar_calendario_frances(
            Decimal("5000"), Decimal("0.22"), 60, date(2026, 1, 31)
        )
        meses = [(c["fecha_vencimiento"].year, c["fecha_vencimiento"].month) for c in cuotas]
        esperados = [(2026 + (k // 12), k % 12 + 1) for k in range(1, 61)]
        assert meses == esperados

    def test_dia_de_pago_se_conserva(self):
        cuotas = generar_calendario_frances(
            Decimal("1000"), Decimal("0.20"), 12, date(2026, 3, 15)
        )
        assert all(c["fecha_vencimiento"].day == 15 for c in cuotas)

    # ------------------------------------------------- integridad del cálculo
    @pytest.mark.parametrize(
        "monto,tea,n",
        [
            ("10000.00", "0.24", 12),
            ("5000.00", "0.185", 18),
            ("200000.00", "0.1050", 240),
            ("1500.00", "0.2800", 6),
            ("1200.00", "0", 12),
            ("1000.00", "0.1500", 1),
        ],
    )
    def test_calendario_cuadra(self, monto, tea, n):
        cuotas = generar_calendario_frances(Decimal(monto), Decimal(tea), n, date(2026, 1, 31))
        assert len(cuotas) == n
        # El capital se recupera completo y el saldo final es cero
        assert sum((c["amortizacion"] for c in cuotas), Decimal("0")) == Decimal(monto)
        assert cuotas[-1]["saldo_final"] == Decimal("0.00")
        for c in cuotas:
            assert c["cuota_total"] == c["amortizacion"] + c["interes"]
            assert c["amortizacion"] >= 0 and c["interes"] >= 0
            # Los importes de dinero van a céntimos exactos
            for campo in ("amortizacion", "interes", "cuota_total", "saldo_final"):
                assert c[campo] == c[campo].quantize(Decimal("0.01"))
        # Cuota fija: todas iguales salvo la última, que absorbe el residuo
        # de redondear cada cuota e interés a céntimos. Ese residuo crece con
        # el interés compuesto (valor futuro de los errores de redondeo), por
        # eso en un hipotecario a 240 meses la última cuota difiere en soles,
        # no en céntimos. Cota: 0.01 por periodo capitalizado a la tasa i.
        if n > 2:
            assert len({c["cuota_total"] for c in cuotas[:-1]}) == 1
            i = tasa_mensual_desde_tea(Decimal(tea))
            factor = ((1 + i) ** n - 1) / i if i else Decimal(n)
            cota = Decimal("0.01") * factor
            assert abs(cuotas[-1]["cuota_total"] - cuotas[0]["cuota_total"]) <= cota
