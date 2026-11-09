"""Ciclo de crédito en CORE — acciones CREAR_SOLICITUD_CREDITO,
EVALUAR_CREDITO, APROBAR_CREDITO, VER_CREDITO, REGISTRAR_PAGO y
CONSULTAR_DEUDA.

RN-16: la solicitud registra plazo, monto, moneda, calendario,
garantías y fiadores. RGN-12: solo una solicitud evaluada como
APROBADA genera cuenta de crédito y asiento de desembolso.
RGN-14: cada pago —incluso fraccionado— genera su propio asiento.
"""

import calendar
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, localcontext

from sqlalchemy.orm import Session

from CORE.exceptions import ConflictError, NotFoundError, ValidationError
from CORE.models import (
    CobAplicacionPago,
    CobCanalPago,
    CobCuota,
    CobCredito,
    CobMora,
    CobPago,
    EvaDecisionAnalista,
    EvaEvaluacion,
    EvaRegla,
    EvaSituacionFinanciera,
    SolCalendarioVersion,
    SolCuotaCalendario,
    SolFiador,
    SolGarantia,
    SolHistorialEstado,
    SolSolicitud,
)
from CORE.models import ProductoCredito as ProductoCreditoModel
from CORE.services import auditoria, clientessvc, contabilidad, movimientos
from CORE.utils.ids import new_uuid7
from CORE.utils.money import D

DOS = Decimal("0.01")
CERO = Decimal("0.00")


# ----------------------------------------------------------------------
# Calendario de pagos (sistema francés, cuota fija)
# ----------------------------------------------------------------------
# La TEA se guarda como FRACCIÓN (producto_credito.tasa_tea DECIMAL(6,4)):
# 0.1850 equivale a 18.50 %. El tope de 5 (500 %) no es un límite legal,
# es una cota de cordura: su objetivo es atrapar el error típico de enviar
# 18.5 (porcentaje) en lugar de 0.185 (fracción).
TEA_MAXIMA = Decimal("5")
# Dígitos significativos para operar con tasas. Las tasas NUNCA se
# redondean a 2 decimales; solo los importes de dinero.
PRECISION_TASAS = 34


def _validar_tea(tasa_tea) -> Decimal:
    """Devuelve la TEA como Decimal exacto (sin redondear) o lanza
    ValidationError si no es numérica o está fuera de [0, TEA_MAXIMA]."""
    try:
        tea = tasa_tea if isinstance(tasa_tea, Decimal) else Decimal(str(tasa_tea))
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError("TEA_INVALIDA", f"TEA no numérica: {tasa_tea!r}.") from None
    if not tea.is_finite():
        raise ValidationError("TEA_INVALIDA", f"TEA no numérica: {tasa_tea!r}.")
    if not (Decimal("0") <= tea <= TEA_MAXIMA):
        raise ValidationError(
            "TEA_FUERA_DE_RANGO",
            "La TEA se expresa como fracción (0.185 equivale a 18.5 %) "
            f"y debe estar entre 0 y {TEA_MAXIMA}.",
            details={"tasa_tea": str(tea)},
        )
    return tea


def tasa_mensual_desde_tea(tasa_tea) -> Decimal:
    """Tasa mensual equivalente: (1 + TEA)^(1/12) − 1.

    Hallazgo #4: antes la TEA pasaba por D(), que redondea a 2 decimales,
    y 0.185 (18.5 %) se convertía en 0.19 (19 %). Ahora la TEA se usa
    exacta y el cálculo se hace con PRECISION_TASAS dígitos.
    """
    tea = _validar_tea(tasa_tea)
    with localcontext() as ctx:
        ctx.prec = PRECISION_TASAS
        mensual = (Decimal("1") + tea) ** (Decimal("1") / Decimal("12")) - Decimal("1")
    return mensual


def _sumar_meses(fecha: date, meses: int) -> date:
    """fecha + n meses calendario, conservando el día de pago.

    Hallazgo #6: antes se sumaban 30·n días y el calendario se desfasaba
    (desde el 31-ene no había cuota en febrero). Si el día no existe en el
    mes destino (31 en febrero), se usa el último día de ese mes. Se calcula
    SIEMPRE desde la fecha original, no encadenado: así un 31 que cayó en
    28 de febrero vuelve a 31 en marzo.

    Equivale a `fecha + dateutil.relativedelta(months=meses)`, pero sin
    agregar python-dateutil a requirements.txt.
    """
    indice = fecha.month - 1 + meses
    anio, mes = fecha.year + indice // 12, indice % 12 + 1
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    return date(anio, mes, min(fecha.day, ultimo_dia))


def generar_calendario_frances(
    monto: Decimal, tasa_tea: Decimal, numero_cuotas: int,
    fecha_inicio: date,
) -> list[dict]:
    """Devuelve las cuotas proyectadas del crédito.

    Hallazgo #5: el servicio valida sus propias entradas y no depende de que
    el schema o el router lo hayan hecho (antes, 0 cuotas producía
    DivisionByZero, cuotas negativas un calendario vacío y un monto negativo
    cuotas negativas). Solo se redondean a céntimos los importes de dinero.
    """
    if isinstance(numero_cuotas, bool) or not isinstance(numero_cuotas, int) or numero_cuotas < 1:
        raise ValidationError(
            "NUMERO_CUOTAS_INVALIDO",
            "El número de cuotas debe ser un entero mayor o igual a 1.",
            details={"numero_cuotas": str(numero_cuotas)},
        )
    try:
        monto = D(monto)
    except (ValueError, InvalidOperation):
        raise ValidationError("MONTO_INVALIDO", f"Monto no numérico: {monto!r}.") from None
    if not monto.is_finite() or monto <= CERO:
        raise ValidationError(
            "MONTO_INVALIDO",
            "El monto del crédito debe ser mayor a cero.",
            details={"monto": str(monto)},
        )
    i = tasa_mensual_desde_tea(tasa_tea)  # valida la TEA

    if i == CERO:
        cuota_fija = (monto / numero_cuotas).quantize(DOS, rounding=ROUND_HALF_UP)
    else:
        cuota_fija = (monto * i / (Decimal("1") - (Decimal("1") + i) ** (-numero_cuotas)))
        cuota_fija = cuota_fija.quantize(DOS, rounding=ROUND_HALF_UP)

    cuotas: list[dict] = []
    saldo = monto
    for n in range(1, numero_cuotas + 1):
        interes = (saldo * i).quantize(DOS, rounding=ROUND_HALF_UP)
        amortizacion = cuota_fija - interes
        if n == numero_cuotas:  # última cuota ajusta el saldo residual
            amortizacion = saldo
            cuota_fija_ajustada = amortizacion + interes
        else:
            cuota_fija_ajustada = cuota_fija
        saldo_final = saldo - amortizacion
        cuotas.append(
            {
                "numero_cuota": n,
                "fecha_vencimiento": _sumar_meses(fecha_inicio, n),
                "saldo_inicial": saldo,
                "amortizacion": amortizacion,
                "interes": interes,
                "cuota_total": cuota_fija_ajustada,
                "saldo_final": saldo_final,
            }
        )
        saldo = saldo_final
    return cuotas


# ----------------------------------------------------------------------
# CREAR_SOLICITUD_CREDITO (RN-16 / RF-SOL-01..05)
# ----------------------------------------------------------------------
def crear_solicitud(
    db: Session,
    *,
    id_cliente: str,
    id_producto_credito: str,
    monto_solicitado: Decimal,
    moneda: str,
    plazo_meses: int,
    destino_credito: str | None = None,
    id_asesor: str | None = None,
    id_agencia: str | None = None,
    id_caso: str | None = None,
    fiadores: list[dict] | None = None,
    garantias: list[dict] | None = None,
    actor: str = "sistema",
    correlation_id: str | None = None,
) -> SolSolicitud:
    if clientessvc.obtener_cliente(db, id_cliente) is None:
        raise NotFoundError("CLIENTE_NO_ENCONTRADO", f"Cliente {id_cliente} no existe.")
    producto = db.get(ProductoCreditoModel, id_producto_credito)
    if producto is None or not producto.activo:
        raise NotFoundError(
            "PRODUCTO_CREDITO_NO_ENCONTRADO",
            f"Producto de crédito {id_producto_credito} inexistente o inactivo.",
        )
    monto = D(monto_solicitado)
    if monto <= CERO:
        raise ValidationError("MONTO_INVALIDO", "El monto solicitado debe ser mayor a cero.")
    if not (producto.plazo_min_meses <= plazo_meses <= producto.plazo_max_meses):
        raise ValidationError(
            "PLAZO_INVALIDO",
            f"El plazo debe estar entre {producto.plazo_min_meses} y "
            f"{producto.plazo_max_meses} meses para {producto.nombre}.",
        )

    solicitud = SolSolicitud(
        id_solicitud=new_uuid7(),
        id_cliente=id_cliente,
        id_caso=id_caso,
        id_producto_credito=id_producto_credito,
        id_asesor=id_asesor,
        id_agencia=id_agencia,
        monto_solicitado=monto,
        moneda=moneda,
        plazo_meses=plazo_meses,
        destino_credito=destino_credito,
        estado_solicitud="REGISTRADA",
        fecha_registro=datetime.now(),
    )
    db.add(solicitud)
    db.flush()

    # Historial de estados
    db.add(
        SolHistorialEstado(
            id_historial=new_uuid7(),
            id_solicitud=solicitud.id_solicitud,
            estado_anterior=None,
            estado_nuevo="REGISTRADA",
            motivo="Alta de solicitud",
            id_usuario=None,
            fecha_hora=datetime.now(),
        )
    )

    for f in fiadores or []:
        db.add(
            SolFiador(
                id_fiador=new_uuid7(),
                id_solicitud=solicitud.id_solicitud,
                id_cliente=f.get("id_cliente"),
                cod_tipo_documento=f.get("cod_tipo_documento"),
                numero_documento=f.get("numero_documento"),
                nombre_completo=f["nombre_completo"],
                telefono=f.get("telefono"),
                ingreso_mensual=D(f["ingreso_mensual"]) if f.get("ingreso_mensual") else None,
                tipo_fiador=f.get("tipo_fiador", "PERSONAL"),
            )
        )
    for g in garantias or []:
        db.add(
            SolGarantia(
                id_garantia=new_uuid7(),
                id_solicitud=solicitud.id_solicitud,
                tipo_garantia=g.get("tipo_garantia", "SIN_GARANTIA"),
                descripcion=g.get("descripcion"),
                valor_tasacion=D(g["valor_tasacion"]) if g.get("valor_tasacion") else None,
                entidad_registro=g.get("entidad_registro"),
                partida_registral=g.get("partida_registral"),
                fecha_tasacion=g.get("fecha_tasacion"),
            )
        )

    # Calendario propuesto (versión SIMULADO)
    calendario = SolCalendarioVersion(
        id_calendario=new_uuid7(),
        id_solicitud=solicitud.id_solicitud,
        version=1,
        tasa_tea=producto.tasa_tea,
        numero_cuotas=plazo_meses,
        monto_financiado=monto,
        estado="SIMULADO",
        fecha_creacion=datetime.now(),
    )
    db.add(calendario)
    db.flush()

    for cuota in generar_calendario_frances(
        monto, producto.tasa_tea, plazo_meses, date.today()
    ):
        db.add(
            SolCuotaCalendario(
                id_cuota=new_uuid7(),
                id_calendario=calendario.id_calendario,
                numero_cuota=cuota["numero_cuota"],
                fecha_vencimiento=cuota["fecha_vencimiento"],
                saldo_inicial=cuota["saldo_inicial"],
                amortizacion=cuota["amortizacion"],
                interes=cuota["interes"],
                cuota_total=cuota["cuota_total"],
                saldo_final=cuota["saldo_final"],
            )
        )

    auditoria.registrar_evento(
        db,
        modulo="CORE",
        entidad="sol_solicitud",
        id_entidad=solicitud.id_solicitud,
        accion="CREAR_SOLICITUD_CREDITO",
        actor=actor,
        detalle={
            "id_cliente": id_cliente,
            "monto": str(monto),
            "moneda": moneda,
            "plazo_meses": plazo_meses,
            "fiadores": len(fiadores or []),
            "garantias": len(garantias or []),
        },
        correlation_id=correlation_id,
    )
    db.commit()
    return solicitud


# ----------------------------------------------------------------------
# EVALUAR_CREDITO (RF-EVA-01..03)
# ----------------------------------------------------------------------
def _evaluar_regla(regla: EvaRegla, variables: dict[str, Decimal]) -> bool:
    if not regla.activa:
        return False
    valor = variables.get(regla.variable)
    if valor is None:
        return False
    op = regla.operador
    if op == "MAYOR":
        return valor > (regla.valor_min or CERO)
    if op == "MENOR":
        return valor < (regla.valor_min or CERO)
    if op == "IGUAL":
        return valor == regla.valor_min
    if op == "ENTRE":
        vmin = regla.valor_min if regla.valor_min is not None else Decimal("-Infinity")
        vmax = regla.valor_max if regla.valor_max is not None else Decimal("Infinity")
        return vmin <= valor <= vmax
    if op == "EXCLUYE":
        # La regla dispara cuando el valor cae dentro de la banda
        # excluida [valor_min, valor_max] (banda abierta si un extremo
        # es NULL, p. ej. dias_mayor_mora >= 1).
        min_ok = regla.valor_min is None or valor >= regla.valor_min
        max_ok = regla.valor_max is None or valor <= regla.valor_max
        return min_ok and max_ok
    return False


def _riesgo_desde_puntaje(puntaje: int) -> str:
    if puntaje >= 80:
        return "BAJO"
    if puntaje >= 50:
        return "MEDIO"
    if puntaje >= 25:
        return "ALTO"
    return "MUY_ALTO"


def evaluar_credito(
    db: Session,
    *,
    id_solicitud: str,
    situacion: dict | None = None,
    dias_mayor_mora: int | None = None,
    actor: str = "sistema",
    correlation_id: str | None = None,
) -> EvaEvaluacion:
    """Ejecuta el motor de reglas (eva_regla) sobre la solicitud.

    Variables disponibles: `ratio_capacidad` (cuota propuesta + otros
    créditos sobre ingresos) y `dias_mayor_mora` (central de riesgos).
    Puede recibirse la situación financiera en el payload o usar la
    ya registrada en eva_situacion_financiera.
    """
    solicitud = db.get(SolSolicitud, id_solicitud)
    if solicitud is None:
        raise NotFoundError("SOLICITUD_NO_ENCONTRADA", f"Solicitud {id_solicitud} no existe.")
    if solicitud.estado_solicitud not in ("REGISTRADA", "EN_EVALUACION", "OBSERVADO"):
        raise ValidationError(
            "SOLICITUD_NO_EVALUABLE",
            f"Solicitud en estado {solicitud.estado_solicitud} no puede evaluarse de nuevo.",
        )

    producto = db.get(ProductoCreditoModel, solicitud.id_producto_credito)
    tea = producto.tasa_tea if producto else Decimal("0.22")
    cuota_estimada = (
        generar_calendario_frances(solicitud.monto_solicitado, tea, solicitud.plazo_meses, date.today())
        or [{}]
    )[0].get("cuota_total", CERO)

    # Situación financiera: payload o tabla
    if situacion:
        ingresos = D(situacion.get("ingresos_mensuales", 0))
        otros = D(situacion.get("cuota_otros_creditos", 0))
        db.add(
            EvaSituacionFinanciera(
                id_situacion=new_uuid7(),
                id_solicitud=id_solicitud,
                id_cliente=solicitud.id_cliente,
                ingresos_mensuales=ingresos,
                egresos_mensuales=D(situacion.get("egresos_mensuales", 0)),
                patrimonio=(
                    D(situacion["patrimonio"]) if situacion.get("patrimonio") is not None else None
                ),
                cuota_otros_creditos=otros,
                ratio_capacidad=None,
                fecha_declaracion=datetime.now(),
            )
        )
    else:
        sit = (
            db.query(EvaSituacionFinanciera)
            .filter(EvaSituacionFinanciera.id_solicitud == id_solicitud)
            .first()
        )
        if sit is None:
            raise ValidationError(
                "SITUACION_FINANCIERA_FALTANTE",
                "No hay situación financiera registrada para la solicitud.",
            )
        ingresos = sit.ingresos_mensuales
        otros = sit.cuota_otros_creditos

    ratio = CERO if ingresos <= CERO else (cuota_estimada + otros) / ingresos
    variables = {
        "ratio_capacidad": ratio.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
        "dias_mayor_mora": Decimal(dias_mayor_mora or 0),
        "monto_solicitado": solicitud.monto_solicitado,
    }

    reglas = db.query(EvaRegla).filter(EvaRegla.activa.is_(True)).all()
    detalle: list[dict] = []
    puntaje_base = 100
    resultado_final = "APROBADO"
    for regla in reglas:
        coincide = _evaluar_regla(regla, variables)
        if coincide:
            puntaje_base -= int(float(regla.peso) * 40)
            detalle.append(
                {
                    "regla": regla.nombre,
                    "resultado": regla.resultado,
                    "peso": str(regla.peso),
                    "coincide": True,
                }
            )
            if regla.resultado == "RECHAZAR":
                resultado_final = "RECHAZADO"
            elif regla.resultado == "OBSERVAR" and resultado_final != "RECHAZADO":
                resultado_final = "OBSERVADO"
        else:
            detalle.append({"regla": regla.nombre, "coincide": False})

    puntaje = max(puntaje_base, 0)
    if resultado_final == "APROBADO" and puntaje < 50:
        resultado_final = "OBSERVADO"

    monto_max = (
        solicitud.monto_solicitado if resultado_final != "RECHAZADO" else None
    )
    evaluacion = EvaEvaluacion(
        id_evaluacion=new_uuid7(),
        id_solicitud=id_solicitud,
        puntaje=puntaje,
        resultado=resultado_final,
        monto_maximo_sugerido=monto_max,
        nivel_riesgo=_riesgo_desde_puntaje(puntaje),
        detalle_reglas={"variables": {k: str(v) for k, v in variables.items()}, "reglas": detalle},
        fecha_evaluacion=datetime.now(),
    )
    db.add(evaluacion)

    estado_anterior = solicitud.estado_solicitud
    solicitud.estado_solicitud = "EN_EVALUACION"
    db.add(
        SolHistorialEstado(
            id_historial=new_uuid7(),
            id_solicitud=id_solicitud,
            estado_anterior=estado_anterior,
            estado_nuevo="EN_EVALUACION",
            motivo=f"Evaluación automática: {resultado_final} (puntaje {puntaje})",
            id_usuario=None,
            fecha_hora=datetime.now(),
        )
    )

    auditoria.registrar_evento(
        db,
        modulo="CORE",
        entidad="eva_evaluacion",
        id_entidad=evaluacion.id_evaluacion,
        accion="EVALUAR_CREDITO",
        actor=actor,
        detalle={
            "id_solicitud": id_solicitud,
            "resultado": resultado_final,
            "puntaje": puntaje,
        },
        correlation_id=correlation_id,
    )
    db.commit()
    return evaluacion


# ----------------------------------------------------------------------
# APROBAR_CREDITO (RF-EVA-01/05, RGN-12)
# ----------------------------------------------------------------------
def aprobar_credito(
    db: Session,
    *,
    id_solicitud: str,
    decision: str = "APROBAR",
    id_analista: str | None = None,
    monto_aprobado: Decimal | None = None,
    plazo_aprobado: int | None = None,
    observacion: str | None = None,
    actor: str = "sistema",
    correlation_id: str | None = None,
) -> tuple[SolSolicitud, EvaDecisionAnalista]:
    if decision not in ("APROBAR", "RECHAZAR", "OBSERVAR", "DERIVAR"):
        raise ValidationError(
            "DECISION_INVALIDO",
            "Decisión admitida: APROBAR, RECHAZAR, OBSERVAR o DERIVAR.",
        )
    solicitud = db.get(SolSolicitud, id_solicitud)
    if solicitud is None:
        raise NotFoundError("SOLICITUD_NO_ENCONTRADA", f"Solicitud {id_solicitud} no existe.")
    if solicitud.estado_solicitud not in ("REGISTRADA", "EN_EVALUACION", "OBSERVADO"):
        raise ValidationError(
            "SOLICITUD_NO_DECIDIBLE",
            f"Solicitud en estado {solicitud.estado_solicitud} no admite decisión.",
        )

    evaluacion = (
        db.query(EvaEvaluacion)
        .filter(EvaEvaluacion.id_solicitud == id_solicitud)
        .order_by(EvaEvaluacion.fecha_evaluacion.desc())
        .first()
    )
    if evaluacion is None:
        raise ValidationError(
            "EVALUACION_FALTANTE",
            "La solicitud aún no ha sido evaluada (EVALUAR_CREDITO primero).",
        )

    nuevo_estado = {
        "APROBAR": "APROBADA",
        "RECHAZAR": "RECHAZADA",
        "OBSERVAR": "OBSERVADO",
        "DERIVAR": "EN_EVALUACION",
    }[decision]

    estado_anterior = solicitud.estado_solicitud
    solicitud.estado_solicitud = nuevo_estado

    monto_final = D(monto_aprobado) if monto_aprobado is not None else solicitud.monto_solicitado
    decision_reg = EvaDecisionAnalista(
        id_decision=new_uuid7(),
        id_evaluacion=evaluacion.id_evaluacion,
        id_analista=id_analista,
        decision=decision,
        monto_aprobado=monto_final if decision == "APROBAR" else None,
        plazo_aprobado=plazo_aprobado or solicitud.plazo_meses,
        observacion=observacion,
        fecha_decision=datetime.now(),
    )
    db.add(decision_reg)
    db.add(
        SolHistorialEstado(
            id_historial=new_uuid7(),
            id_solicitud=id_solicitud,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            motivo=observacion or f"Decisión del analista: {decision}",
            id_usuario=None,
            fecha_hora=datetime.now(),
        )
    )

    auditoria.registrar_evento(
        db,
        modulo="CORE",
        entidad="sol_solicitud",
        id_entidad=id_solicitud,
        accion="APROBAR_CREDITO" if decision == "APROBAR" else "DECIDIR_CREDITO",
        actor=actor,
        detalle={
            "decision": decision,
            "estado_anterior": estado_anterior,
            "estado_nuevo": nuevo_estado,
            "monto_aprobado": str(monto_final),
        },
        correlation_id=correlation_id,
    )
    db.commit()
    return solicitud, decision_reg


# ----------------------------------------------------------------------
# VER_CREDITO / CONSULTAR_DEUDA
# ----------------------------------------------------------------------
def ver_credito(db: Session, id_solicitud: str) -> dict:
    solicitud = db.get(SolSolicitud, id_solicitud)
    if solicitud is None:
        raise NotFoundError("SOLICITUD_NO_ENCONTRADA", f"Solicitud {id_solicitud} no existe.")
    fiadores = db.query(SolFiador).filter(SolFiador.id_solicitud == id_solicitud).all()
    garantias = db.query(SolGarantia).filter(SolGarantia.id_solicitud == id_solicitud).all()
    historial = (
        db.query(SolHistorialEstado)
        .filter(SolHistorialEstado.id_solicitud == id_solicitud)
        .order_by(SolHistorialEstado.fecha_hora)
        .all()
    )
    calendario = (
        db.query(SolCalendarioVersion)
        .filter(SolCalendarioVersion.id_solicitud == id_solicitud)
        .first()
    )
    cuotas = []
    if calendario:
        cuotas = (
            db.query(SolCuotaCalendario)
            .filter(SolCuotaCalendario.id_calendario == calendario.id_calendario)
            .order_by(SolCuotaCalendario.numero_cuota)
            .all()
        )
    credito = (
        db.query(CobCredito).filter(CobCredito.id_solicitud == id_solicitud).first()
    )
    return {
        "id_solicitud": solicitud.id_solicitud,
        "id_cliente": solicitud.id_cliente,
        "id_producto_credito": solicitud.id_producto_credito,
        "monto_solicitado": solicitud.monto_solicitado,
        "moneda": solicitud.moneda,
        "plazo_meses": solicitud.plazo_meses,
        "destino_credito": solicitud.destino_credito,
        "estado_solicitud": solicitud.estado_solicitud,
        "fecha_registro": solicitud.fecha_registro,
        "fiadores": [
            {"nombre_completo": f.nombre_completo, "tipo_fiador": f.tipo_fiador}
            for f in fiadores
        ],
        "garantias": [
            {"tipo_garantia": g.tipo_garantia, "valor_tasacion": g.valor_tasacion}
            for g in garantias
        ],
        "historial": [
            {
                "estado_anterior": h.estado_anterior,
                "estado_nuevo": h.estado_nuevo,
                "motivo": h.motivo,
                "fecha_hora": h.fecha_hora,
            }
            for h in historial
        ],
        "calendario": (
            {
                "version": calendario.version,
                "tasa_tea": calendario.tasa_tea,
                "numero_cuotas": calendario.numero_cuotas,
                "monto_financiado": calendario.monto_financiado,
                "estado": calendario.estado,
                "cuotas": [
                    {
                        "numero_cuota": c.numero_cuota,
                        "fecha_vencimiento": c.fecha_vencimiento,
                        "cuota_total": c.cuota_total,
                        "saldo_final": c.saldo_final,
                    }
                    for c in cuotas
                ],
            }
            if calendario else None
        ),
        "credito_desembolsado": (
            {
                "id_credito": credito.id_credito,
                "saldo_capital": credito.saldo_capital,
                "estado_credito": credito.estado_credito,
                "dias_mora": credito.dias_mora,
            }
            if credito else None
        ),
    }


def consultar_deuda(db: Session, *, id_credito: str | None = None,
                    id_cliente: str | None = None) -> list[dict]:
    """RF-COB-01 / RF-COR-25: saldo de deuda y estado del crédito."""
    q = db.query(CobCredito)
    if id_credito:
        q = q.filter(CobCredito.id_credito == id_credito)
    if id_cliente:
        q = q.filter(CobCredito.id_cliente == id_cliente)
    creditos = q.all()
    if id_credito and not creditos:
        raise NotFoundError("CREDITO_NO_ENCONTRADO", f"Crédito {id_credito} no existe.")

    resultado = []
    hoy = date.today()
    for cred in creditos:
        cuotas = (
            db.query(CobCuota)
            .filter(CobCuota.id_credito == cred.id_credito)
            .order_by(CobCuota.numero_cuota)
            .all()
        )
        mora_vigente = (
            db.query(CobMora)
            .join(CobCuota, CobCuota.id_cuota_credito == CobMora.id_cuota_credito)
            .filter(CobCuota.id_credito == cred.id_credito, CobMora.vigente_flag == 1)
            .all()
        )
        saldo_mora = sum((m.interes_mora for m in mora_vigente), start=CERO)
        pendientes = [c for c in cuotas if c.estado_cuota != "PAGADA"]
        proxima = pendientes[0] if pendientes else None
        en_mora = any(c.fecha_vencimiento < hoy and c.estado_cuota != "PAGADA" for c in cuotas)
        resultado.append(
            {
                "id_credito": cred.id_credito,
                "id_solicitud": cred.id_solicitud,
                "id_cliente": cred.id_cliente,
                "monto_aprobado": cred.monto_aprobado,
                "moneda": cred.moneda,
                "tasa_tea": cred.tasa_tea,
                "plazo_meses": cred.plazo_meses,
                "saldo_capital": cred.saldo_capital,
                "saldo_mora": D(saldo_mora),
                "saldo_total": D(cred.saldo_capital + saldo_mora),
                "estado_credito": cred.estado_credito,
                "estado_riesgo": "EN_MORA" if en_mora else "AL_DIA",
                "dias_mora": cred.dias_mora,
                "proxima_cuota": (
                    {
                        "numero_cuota": proxima.numero_cuota,
                        "fecha_vencimiento": proxima.fecha_vencimiento,
                        "cuota_total": proxima.cuota_total,
                        "monto_pagado": proxima.monto_pagado,
                        "estado_cuota": proxima.estado_cuota,
                    }
                    if proxima else None
                ),
                "cuotas": [
                    {
                        "numero_cuota": c.numero_cuota,
                        "fecha_vencimiento": c.fecha_vencimiento,
                        "capital": c.capital,
                        "interes": c.interes,
                        "cuota_total": c.cuota_total,
                        "monto_pagado": c.monto_pagado,
                        "estado_cuota": c.estado_cuota,
                    }
                    for c in cuotas
                ],
            }
        )
    return resultado


# ----------------------------------------------------------------------
# REGISTRAR_PAGO (RF-COR-23, RGN-14)
# ----------------------------------------------------------------------
def registrar_pago(
    db: Session,
    *,
    id_credito: str,
    monto: Decimal,
    id_canal_pago: str,
    num_cuenta: str | None = None,
    num_operacion: str,
    id_cobrador: str | None = None,
    idempotency_key: str | None = None,
    actor: str = "sistema",
    correlation_id: str | None = None,
) -> dict:
    """Registra un pago (parcial o total) y lo aplica a las cuotas.

    Si se indica `num_cuenta`, se debita de esa cuenta de ahorro y cada
    aplicación genera su propio asiento contable (RGN-14).
    """
    monto = D(monto)
    if monto <= CERO:
        raise ValidationError("MONTO_INVALIDO", "El monto del pago debe ser mayor a cero.")

    pago_existente = db.query(CobPago).filter(CobPago.num_operacion == num_operacion).first()
    if pago_existente is not None:
        raise ConflictError(
            "PAGO_DUPLICADO",
            f"Ya existe un pago con número de operación {num_operacion}.",
            details={"id_pago": pago_existente.id_pago},
        )

    credito = db.get(CobCredito, id_credito)
    if credito is None:
        raise NotFoundError("CREDITO_NO_ENCONTRADO", f"Crédito {id_credito} no existe.")
    canal_pago = db.get(CobCanalPago, id_canal_pago)
    if canal_pago is None or not canal_pago.activo:
        raise NotFoundError(
            "CANAL_PAGO_NO_ENCONTRADO", f"Canal de pago {id_canal_pago} inexistente."
        )

    cuotas = (
        db.query(CobCuota)
        .filter(CobCuota.id_credito == id_credito, CobCuota.estado_cuota != "PAGADA")
        .order_by(CobCuota.fecha_vencimiento, CobCuota.numero_cuota)
        .all()
    )
    if not cuotas:
        raise ValidationError("CREDITO_SIN_CUOTAS_PENDIENTES", "El crédito no tiene cuotas pendientes.")

    hoy = datetime.now()
    pago = CobPago(
        id_pago=new_uuid7(),
        id_credito=id_credito,
        id_canal_pago=id_canal_pago,
        num_cuenta=num_cuenta,
        monto=monto,
        moneda=credito.moneda,
        num_operacion=num_operacion,
        id_cobrador=id_cobrador,
        estado_pago="REGISTRADO",
        fecha_pago=hoy,
    )
    db.add(pago)
    db.flush()

    restante = monto
    aplicaciones: list[dict] = []
    for cuota in cuotas:
        if restante <= CERO:
            break
        mora = (
            db.query(CobMora)
            .filter(CobMora.id_cuota_credito == cuota.id_cuota_credito,
                    CobMora.vigente_flag == 1)
            .first()
        )
        interes_mora = mora.interes_mora if mora else CERO
        pendiente = D(cuota.cuota_total - cuota.monto_pagado + interes_mora)
        aplicar = min(restante, pendiente)

        # Orden de aplicación: mora -> interes -> seguro -> capital
        aplica_mora = min(aplicar, interes_mora)
        resto = aplicar - aplica_mora
        aplica_interes = min(resto, cuota.interes)
        resto -= aplica_interes
        aplica_seguro = min(resto, cuota.seguro)
        resto -= aplica_seguro
        aplica_capital = resto

        cuota.monto_pagado = D(cuota.monto_pagado + aplicar)
        restante = D(restante - aplicar)
        if aplica_capital > CERO:
            cuota.saldo_capital = D(cuota.saldo_capital - aplica_capital)
            credito.saldo_capital = D(credito.saldo_capital - aplica_capital)
        if interes_mora > CERO and mora is not None:
            mora.interes_mora = D(mora.interes_mora - aplica_mora)
            if mora.interes_mora <= CERO:
                mora.estado_mora = "PAGADA"

        if cuota.monto_pagado >= cuota.cuota_total:
            cuota.estado_cuota = "PAGADA"
        elif cuota.monto_pagado > CERO:
            cuota.estado_cuota = "PARCIAL"

        aplicacion = CobAplicacionPago(
            id_aplicacion=new_uuid7(),
            id_pago=pago.id_pago,
            id_cuota_credito=cuota.id_cuota_credito,
            aplica_capital=aplica_capital,
            aplica_interes=aplica_interes,
            aplica_seguro=aplica_seguro,
            aplica_mora=aplica_mora,
            fecha_aplicacion=hoy,
        )
        db.add(aplicacion)

        # RGN-14: cada aplicación de pago genera su propio asiento
        lineas = []
        if num_cuenta is not None:
            tasa_base = movimientos.tasa_vigente(db, credito.moneda, "PEN", hoy.date())
            if aplica_capital > CERO:
                lineas.append(contabilidad.linea(
                    contabilidad.CTAS_POR_COBRAR, debe=aplica_capital,
                    moneda=credito.moneda, tipo_cambio=tasa_base,
                    importe_base=aplica_capital if credito.moneda == "PEN" else (aplica_capital * tasa_base).quantize(DOS),
                ))
            if aplica_interes > CERO:
                lineas.append(contabilidad.linea(
                    contabilidad.INGRESOS_INTERESES, haber=aplica_interes,
                    moneda=credito.moneda, tipo_cambio=tasa_base,
                    importe_base=aplica_interes if credito.moneda == "PEN" else (aplica_interes * tasa_base).quantize(DOS),
                ))
            if aplica_mora > CERO:
                lineas.append(contabilidad.linea(
                    contabilidad.INGRESOS_MORA, haber=aplica_mora,
                    moneda=credito.moneda, tipo_cambio=tasa_base,
                    importe_base=aplica_mora if credito.moneda == "PEN" else (aplica_mora * tasa_base).quantize(DOS),
                ))
            # Débito a la cuenta de ahorro por el total aplicado
            lineas.insert(0, contabilidad.linea(
                contabilidad.DEPOSITOS_AHORRO, debe=aplicar,
                moneda=credito.moneda, tipo_cambio=tasa_base,
                importe_base=aplicar if credito.moneda == "PEN" else (aplicar * tasa_base).quantize(DOS),
            ))
            asiento = contabilidad.crear_asiento(
                db,
                glosa=(
                    f"Pago crédito {id_credito} cuota {cuota.numero_cuota} "
                    f"op {num_operacion}"
                ),
                lineas=lineas,
                fecha=hoy,
            )
            aplicaciones.append({"id_aplicacion": aplicacion.id_aplicacion,
                                 "id_asiento": asiento.id_asiento})
        else:
            aplicaciones.append({"id_aplicacion": aplicacion.id_aplicacion,
                                 "id_asiento": None})

    if credito.saldo_capital <= CERO:
        credito.estado_credito = "CANCELADO"
        credito.saldo_capital = max(credito.saldo_capital, CERO)
    pago.estado_pago = "APLICADO"

    auditoria.registrar_evento(
        db,
        modulo="CORE",
        entidad="cob_pago",
        id_entidad=pago.id_pago,
        accion="REGISTRAR_PAGO",
        actor=actor,
        detalle={
            "id_credito": id_credito,
            "monto": str(monto),
            "num_operacion": num_operacion,
            "aplicaciones": aplicaciones,
            "monto_no_aplicado": str(restante),
        },
        correlation_id=correlation_id,
    )
    db.commit()
    return {
        "id_pago": pago.id_pago,
        "id_credito": id_credito,
        "monto": monto,
        "monto_aplicado": D(monto - restante),
        "monto_no_aplicado": restante,
        "num_operacion": num_operacion,
        "estado_pago": pago.estado_pago,
        "aplicaciones": aplicaciones,
        "saldo_capital_restante": credito.saldo_capital,
        "estado_credito": credito.estado_credito,
    }
