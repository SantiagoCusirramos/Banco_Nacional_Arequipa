"""Pruebas del motor de reglas y del flujo CREAR -> EVALUAR -> APROBAR.

Acompañan a CORE/CREDITOS_MOTOR_Y_FLUJO.md (Leonardo Lonasco, Actividad 2).

- Las pruebas normales fijan el comportamiento ACTUAL que se documenta.
- Las marcadas `xfail(strict=True)` describen el comportamiento ESPERADO de
  hallazgos que requieren decisión del Comité de Créditos. Hoy fallan a
  propósito (la suite sigue en verde). Cuando alguien corrija el hallazgo,
  pytest marcará XPASS como error: es la señal para quitar el `xfail`.

Usa SQLite en memoria: no necesita MySQL.
"""

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import CORE.models as m
from CORE.database import Base
from CORE.exceptions import ValidationError
from CORE.services.creditossvc import (
    _evaluar_regla,
    aprobar_credito,
    crear_solicitud,
    evaluar_credito,
    generar_calendario_frances,
)
from CORE.utils.ids import new_uuid7

PRODUCTO = "prod-personal"
CLIENTE = "cli-0001"

# Copia de las reglas sembradas en Infraestructura - BD/.../10_seed_catalogos.sql
REGLAS_SEED = [
    ("RATIO_SALUDABLE", "ratio_capacidad", "ENTRE", "0", "0.80", "APROBAR", "1.00"),
    ("RATIO_LIMITE", "ratio_capacidad", "ENTRE", "0.80", "1.00", "OBSERVAR", "1.00"),
    ("RATIO_INSUFICIENTE", "ratio_capacidad", "MAYOR", "1.00", None, "RECHAZAR", "1.00"),
    ("MORA_RECIENTE", "dias_mayor_mora", "MAYOR", "30", None, "OBSERVAR", "0.50"),
    ("MORA_GRAVE", "dias_mayor_mora", "MAYOR", "120", None, "RECHAZAR", "1.00"),
]


def _dec(valor):
    return None if valor is None else Decimal(valor)


def _regla(operador, vmin, vmax, variable="v"):
    return m.EvaRegla(
        id_regla="r", nombre="r", variable=variable, operador=operador,
        valor_min=_dec(vmin), valor_max=_dec(vmax), resultado="OBSERVAR",
        peso=Decimal("1"), activa=True,
    )


# ======================================================================
# 1. Semántica de operadores (sin BD)
# ======================================================================
@pytest.mark.parametrize(
    "vmin,vmax",
    [("0", "0.80"), ("0.80", "1.00"), ("1", None), (None, "30"), ("30", None), (None, None)],
)
@pytest.mark.parametrize("valor", ["-1", "0", "0.5", "0.80", "1", "1.5", "30", "31", "120", "121"])
def test_excluye_se_comporta_igual_que_entre(vmin, vmax, valor):
    """Hoy EXCLUYE dispara cuando el valor está DENTRO de la banda, igual
    que ENTRE (ambos extremos incluidos, extremo NULL = abierto). Ver §2.2
    del documento: son dos nombres para la misma regla."""
    variables = {"v": Decimal(valor)}
    assert _evaluar_regla(_regla("EXCLUYE", vmin, vmax), variables) == _evaluar_regla(
        _regla("ENTRE", vmin, vmax), variables
    )


def test_fronteras_de_los_operadores():
    v = lambda x: {"v": Decimal(x)}  # noqa: E731
    # MAYOR y MENOR son estrictos: el umbral exacto NO dispara
    assert not _evaluar_regla(_regla("MAYOR", "30", None), v("30"))
    assert _evaluar_regla(_regla("MAYOR", "30", None), v("31"))
    assert not _evaluar_regla(_regla("MENOR", "30", None), v("30"))
    # ENTRE incluye ambos extremos
    assert _evaluar_regla(_regla("ENTRE", "0.80", "1.00"), v("0.80"))
    assert _evaluar_regla(_regla("ENTRE", "0.80", "1.00"), v("1.00"))
    # IGUAL es exacto
    assert _evaluar_regla(_regla("IGUAL", "5", None), v("5.00"))
    assert not _evaluar_regla(_regla("IGUAL", "5", None), v("5.01"))


# ======================================================================
# 2. Flujo y motor sobre SQLite en memoria
# ======================================================================
@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as sesion:
        sesion.add(m.ProductoCredito(
            id_producto_credito=PRODUCTO, nombre="Credito Personal",
            tasa_tea=Decimal("0.2200"), plazo_min_meses=6, plazo_max_meses=60, activo=True,
        ))
        sesion.add(m.Cliente(
            id_cliente=CLIENTE, cod_tipo_documento="DNI", numero_documento="70000001",
            nombres="Ana", apellido_paterno="Quispe", numero_celular="900000001",
            fecha_registro=datetime.now(),
        ))
        for nombre, var, op, vmin, vmax, res, peso in REGLAS_SEED:
            sesion.add(m.EvaRegla(
                id_regla=new_uuid7(), nombre=nombre, variable=var, operador=op,
                valor_min=_dec(vmin), valor_max=_dec(vmax), resultado=res,
                peso=Decimal(peso), activa=True,
            ))
        sesion.commit()
        yield sesion


def _nueva_solicitud(db, monto="10000.00", plazo=12):
    return crear_solicitud(
        db, id_cliente=CLIENTE, id_producto_credito=PRODUCTO,
        monto_solicitado=Decimal(monto), moneda="PEN", plazo_meses=plazo,
    )


def _evaluar(db, sol, ingresos, otros="0", mora=0):
    return evaluar_credito(
        db, id_solicitud=sol.id_solicitud, dias_mayor_mora=mora,
        situacion={"ingresos_mensuales": ingresos, "cuota_otros_creditos": otros},
    )


def _reglas_que_coinciden(evaluacion):
    return [r["regla"] for r in evaluacion.detalle_reglas["reglas"] if r.get("coincide")]


def _cuota_estimada(monto="10000.00", plazo=12):
    return generar_calendario_frances(Decimal(monto), Decimal("0.2200"), plazo, date.today())[0][
        "cuota_total"
    ]


def test_crear_solicitud_genera_calendario_simulado_con_meses_calendario(db):
    sol = _nueva_solicitud(db, plazo=12)
    cal = db.scalars(select(m.SolCalendarioVersion)).one()
    cuotas = db.scalars(
        select(m.SolCuotaCalendario).order_by(m.SolCuotaCalendario.numero_cuota)
    ).all()
    assert sol.estado_solicitud == "REGISTRADA"
    assert cal.estado == "SIMULADO" and len(cuotas) == 12
    meses = [(c.fecha_vencimiento.year, c.fecha_vencimiento.month) for c in cuotas]
    assert len(set(meses)) == 12  # una cuota por mes, ninguno se salta


def test_aprobar_no_genera_credito_ni_desembolso_hueco_conocido(db):
    """Fija el hueco documentado en CORE/README.md (punto 2) y en §4.4 del
    documento: tras APROBAR no existe cob_credito, ni cuotas de cobranza,
    ni asiento contable de desembolso, y el calendario sigue SIMULADO.
    Si se implementa RGN-12, esta prueba debe actualizarse."""
    sol = _nueva_solicitud(db)
    _evaluar(db, sol, ingresos="10000")
    sol, _ = aprobar_credito(db, id_solicitud=sol.id_solicitud, decision="APROBAR", id_analista="a1")
    assert sol.estado_solicitud == "APROBADA"
    assert db.scalars(select(m.CobCredito)).first() is None
    assert db.scalars(select(m.CobCuota)).first() is None
    assert db.scalars(select(m.AsientoContable)).first() is None
    assert db.scalars(select(m.SolCalendarioVersion)).one().estado == "SIMULADO"


def test_estado_tras_evaluar_es_en_evaluacion_aunque_el_resultado_sea_rechazado(db):
    sol = _nueva_solicitud(db)
    ev = _evaluar(db, sol, ingresos="10000", mora=200)
    assert ev.resultado == "RECHAZADO"
    assert db.get(m.SolSolicitud, sol.id_solicitud).estado_solicitud == "EN_EVALUACION"


# ----------------------------------------------------------------------
# Hallazgos pendientes de decisión (comportamiento esperado, hoy falla)
# ----------------------------------------------------------------------
@pytest.mark.xfail(strict=True, reason="H-A1: las reglas con resultado APROBAR restan puntaje (doc §3.1)")
def test_solicitante_sano_no_pierde_puntos_por_cumplir_la_regla_saludable(db):
    sol = _nueva_solicitud(db)
    ev = _evaluar(db, sol, ingresos="10000")  # ratio ~0.09, sin mora
    assert _reglas_que_coinciden(ev) == ["RATIO_SALUDABLE"]
    assert ev.puntaje == 100 and ev.nivel_riesgo == "BAJO"


@pytest.mark.xfail(strict=True, reason="H-A2: ratio exacto 0.80 dispara dos reglas ENTRE (doc §3.2)")
def test_ratio_exacto_en_la_frontera_activa_una_sola_regla(db):
    sol = _nueva_solicitud(db)
    otros = Decimal("800.00") - _cuota_estimada()  # (cuota + otros) / 1000 = 0.8000
    ev = _evaluar(db, sol, ingresos="1000", otros=str(otros))
    assert ev.detalle_reglas["variables"]["ratio_capacidad"] == "0.8000"
    ratio = [r for r in _reglas_que_coinciden(ev) if r.startswith("RATIO_")]
    assert len(ratio) == 1


@pytest.mark.xfail(strict=True, reason="H-A3: ingresos 0 se tratan como ratio 0, el mejor caso (doc §3.3)")
def test_solicitante_sin_ingresos_no_es_aprobado(db):
    sol = _nueva_solicitud(db)
    ev = _evaluar(db, sol, ingresos="0")
    assert ev.resultado != "APROBADO"


@pytest.mark.xfail(strict=True, reason="H-B1: se puede APROBAR una evaluación RECHAZADA (doc §4.1)")
def test_no_se_puede_aprobar_una_evaluacion_rechazada(db):
    sol = _nueva_solicitud(db)
    assert _evaluar(db, sol, ingresos="10000", mora=200).resultado == "RECHAZADO"
    with pytest.raises(ValidationError):
        aprobar_credito(db, id_solicitud=sol.id_solicitud, decision="APROBAR", id_analista="a1")


@pytest.mark.xfail(strict=True, reason="H-B3: el monto aprobado no se acota al solicitado (doc §4.3)")
def test_no_se_aprueba_mas_de_lo_solicitado(db):
    sol = _nueva_solicitud(db, monto="10000.00")
    _evaluar(db, sol, ingresos="10000")
    with pytest.raises(ValidationError):
        aprobar_credito(
            db, id_solicitud=sol.id_solicitud, decision="APROBAR",
            id_analista="a1", monto_aprobado=Decimal("50000.00"),
        )
