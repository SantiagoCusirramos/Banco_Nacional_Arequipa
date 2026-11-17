"""Reglas puras: puntaje de riesgo y proveedor simulado."""

from decimal import Decimal

import pytest

from CAPTACION import proveedores


def _rep(calificacion="NORMAL", deuda="0", entidades=0, mora=0):
    return {"calificacion": calificacion, "deuda_total": Decimal(deuda), "entidades": entidades,
            "dias_mora": mora}


def test_sin_deudas_es_riesgo_bajo():
    assert proveedores.puntaje([_rep()], []) [:2] == (1000, "BAJO")


def test_cpp_con_mora_es_medio():
    valor, calificacion, _ = proveedores.puntaje([_rep("CPP", "3000", 2, 15)], [])
    assert valor == 1000 - 250 - 30 - 30 and calificacion == "MEDIO"


def test_dudoso_siempre_es_muy_alto():
    assert proveedores.puntaje([_rep("DUDOSO")], [])[1] == "MUY_ALTO"


def test_pep_observado_resta_cien():
    con_pep, _, nota = proveedores.puntaje([_rep()], ["PEP"])
    assert con_pep == 900 and "PEP" in nota


def test_sin_consultas_es_error():
    with pytest.raises(ValueError):
        proveedores.puntaje([], [])


def test_simulador_de_identidad():
    assert proveedores.validar("RENIEC", "DNI", "12345678")[0] == "APROBADO"
    assert proveedores.validar("RENIEC", "CE", "A12345678")[0] == "OBSERVADO"
    assert proveedores.validar("LISTAS_NEGRAS", "DNI", "99999999")[0] == "RECHAZADO"
    assert proveedores.validar("PEP", "DNI", "88888880")[0] == "OBSERVADO"


@pytest.mark.parametrize("numero,esperado", [("40000001", "NORMAL"), ("40000007", "CPP"),
                                             ("40000008", "DEFICIENTE"), ("40000009", "DUDOSO")])
def test_simulador_de_centrales(numero, esperado):
    assert proveedores.consultar_central(numero)["calificacion"] == esperado
