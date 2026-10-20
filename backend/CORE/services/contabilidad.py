"""Núcleo contable: asientos de partida doble (RF-COR-06, RGN-01, RGN-07).

Códigos del plan de cuentas según el seed 10_seed_catalogos.sql.
RGN-07: un asiento nunca se elimina ni se modifica; las correcciones
son asientos de reversión que referencian al original.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from CORE.exceptions import ValidationError
from CORE.models import AsientoContable, AsientoDetalle, PeriodoContable
from CORE.utils.ids import new_uuid7
from CORE.utils.money import D

# Plan de cuentas (seed 10_seed_catalogos.sql)
CAJA = "1101"                    # Caja — activo
FONDOS_BANCO = "1102"            # Fondos en Banco Central
CTAS_POR_COBRAR = "1103"         # Cuentas por cobrar (créditos al cliente)
DEPOSITOS_AHORRO = "2101"        # Depósitos de ahorro — pasivo
DEPOSITOS_PLAZO = "2102"
OBLIGACIONES_PUBLICO = "2103"
INGRESOS_INTERESES = "4101"      # Ingresos por intereses (créditos)
INGRESOS_COMISIONES = "4102"
INGRESOS_MORA = "4103"
GASTOS_INTERESES = "5101"        # Gastos por intereses (depósitos)
GASTOS_OPERATIVOS = "5102"


@dataclass
class LineaAsiento:
    """Una línea del asiento. `debe` y `haber` están en la moneda del
    movimiento; `importe_moneda_base` es el convertido a PEN."""

    cod_cuenta_contable: str
    debe: Decimal
    haber: Decimal
    moneda: str
    tipo_cambio: Decimal
    importe_moneda_base: Decimal


def periodo_abierto(db: Session, fecha: date) -> PeriodoContable:
    periodo = (
        db.query(PeriodoContable)
        .filter(
            PeriodoContable.fecha_inicio <= fecha,
            PeriodoContable.fecha_fin >= fecha,
        )
        .first()
    )
    if periodo is None:
        raise ValidationError(
            "PERIODO_CONTABLE_NO_ENCONTRADO",
            f"No existe periodo contable que cubra la fecha {fecha.isoformat()}.",
            details={"fecha": fecha.isoformat()},
        )
    if periodo.estado != "ABIERTO":
        raise ValidationError(
            "PERIODO_CONTABLE_CERRADO",
            f"El periodo contable {periodo.anio}-{periodo.mes:02d} está CERRADO.",
            details={"id_periodo": periodo.id_periodo},
        )
    return periodo


def crear_asiento(
    db: Session,
    *,
    glosa: str,
    lineas: list[LineaAsiento],
    fecha: datetime | None = None,
) -> AsientoContable:
    """Crea un asiento validando el cuadre partida doble (RNF-10).

    La suma de `importe_moneda_base` del debe debe ser igual a la del
    haber; si no, se rechaza la operación completa.
    """
    if not lineas:
        raise ValidationError("ASIENTO_SIN_LINEAS", "El asiento debe tener al menos una línea.")

    suma_debe = sum((l.debe for l in lineas), start=Decimal("0"))
    suma_haber = sum((l.haber for l in lineas), start=Decimal("0"))
    if suma_debe != suma_haber:
        raise ValidationError(
            "ASIENTO_DESCUADRADO",
            "La suma del debe no coincide con la suma del haber.",
            details={"debe": str(suma_debe), "haber": str(suma_haber)},
        )

    fecha = fecha or datetime.now()
    periodo = periodo_abierto(db, fecha.date())

    asiento = AsientoContable(
        id_asiento=new_uuid7(),
        id_periodo=periodo.id_periodo,
        fecha=fecha,
        glosa=glosa[:200],
        estado="REGISTRADO",
    )
    db.add(asiento)

    for linea in lineas:
        db.add(
            AsientoDetalle(
                id_detalle=new_uuid7(),
                id_asiento=asiento.id_asiento,
                cod_cuenta_contable=linea.cod_cuenta_contable,
                debe=linea.debe,
                haber=linea.haber,
                moneda=linea.moneda,
                tipo_cambio=linea.tipo_cambio,
                importe_moneda_base=linea.importe_moneda_base,
            )
        )
    return asiento


def linea(
    cod_cuenta: str,
    *,
    debe: Decimal = Decimal("0"),
    haber: Decimal = Decimal("0"),
    moneda: str,
    tipo_cambio: Decimal,
    importe_base: Decimal,
) -> LineaAsiento:
    return LineaAsiento(
        cod_cuenta_contable=cod_cuenta,
        debe=D(debe),
        haber=D(haber),
        moneda=moneda,
        tipo_cambio=tipo_cambio,
        importe_moneda_base=D(importe_base),
    )


def cuadre_del_dia(db: Session, fecha: date) -> dict:
    """Verificación del cuadre contable diario (RF-COR-20 / RNF-10)."""
    desde = datetime.combine(fecha, datetime.min.time())
    hasta = datetime.combine(fecha, datetime.max.time())

    filas = (
        db.query(AsientoDetalle)
        .join(
            AsientoContable,
            AsientoContable.id_asiento == AsientoDetalle.id_asiento,
        )
        .filter(AsientoContable.fecha >= desde, AsientoContable.fecha <= hasta)
        .all()
    )
    total_debe = sum((f.debe for f in filas), start=Decimal("0"))
    total_haber = sum((f.haber for f in filas), start=Decimal("0"))
    return {
        "fecha": fecha.isoformat(),
        "total_debe": D(total_debe),
        "total_haber": D(total_haber),
        "diferencia": D(total_debe - total_haber),
        "cuadra": total_debe == total_haber,
        "cantidad_detalles": len(filas),
    }
