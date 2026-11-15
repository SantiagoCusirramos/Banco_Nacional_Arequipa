"""Logica de negocio del modulo Cobranza. No depende de FastAPI."""
import uuid
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP

CERO = Decimal("0.00")

# RF-COB-007: catalogo PROVISIONAL de estados del credito, pendiente de definicion del Comite de Creditos.
ESTADOS_CREDITO = ("AL_DIA", "EN_MORA", "CANCELADO")

# SUPUESTO provisional (orden de imputacion del pago), pendiente de definicion del Comite de Creditos:
# True = primero se cubre la mora vigente de la cuota y el resto va a capital; False = al reves.
ORDEN_IMPUTACION_MORA_PRIMERO = True


class ErrorNegocio(Exception):
    def __init__(self, status, detalle, regla=None):
        super().__init__(detalle)
        self.status = status
        self.detalle = detalle
        self.regla = regla


def D(x):
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _fecha(v, solo_fecha=False):
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d" if solo_fecha else "%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        base = v.strftime("%Y-%m-%d")
        return base if solo_fecha else base + " 00:00:00"
    s = str(v).replace("T", " ")
    if solo_fecha:
        return s[:10]
    return s[:19] if len(s) >= 19 else s[:10] + " 00:00:00"


def nuevo_id(prefijo):
    return f"{prefijo}-{uuid.uuid4().hex[:8].upper()}"


def registrar_evento(db, id_entidad, tipo, usuario="sistema", modulo="COBRANZA", resultado="EXITOSO"):
    """RN-CR-GEN-004 / CR-INT-10: trazabilidad de cada cambio de estado (registro local).
    usuarioOperador se toma del rol (X-API-Key) que hizo la llamada HTTP cuando aplica; resultado es el
    campo de CR-INT-10 que faltaba en el diccionario de Fase II."""
    db.ejecutar(
        "INSERT INTO EVENTO_AUDITORIA (idEvento, idEntidad, tipoEvento, `timestamp`, moduloEmisor, "
        "usuarioOperador, resultado) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (nuevo_id("EVT"), id_entidad, tipo, ahora(), modulo, usuario, resultado),
    )


def recalcular_estado_credito(db, cod, fecha_referencia=None, usuario="sistema"):
    """RF-COB-007: catalogo PROVISIONAL (ESTADOS_CREDITO), pendiente de definicion del Comite.
    EN_MORA si alguna cuota con saldo (capital o mora) vencio antes de fecha_referencia (por defecto hoy).
    CANCELADO es terminal: no se recalcula. No hace commit; el llamador decide la transaccion."""
    cred = db.uno("SELECT estadoCredito FROM CREDITO WHERE codCredito = %s", (cod,))
    if not cred or cred["estadoCredito"] == "CANCELADO":
        return cred["estadoCredito"] if cred else None
    ref = _fecha(fecha_referencia, True) if fecha_referencia else date.today().strftime("%Y-%m-%d")
    vencida = db.uno(
        "SELECT COUNT(*) AS n FROM CUOTA WHERE codCredito = %s AND (saldoPendiente > 0 OR moraPendiente > 0) "
        "AND fechaVencimiento < %s", (cod, ref))
    nuevo_estado = "EN_MORA" if vencida["n"] > 0 else "AL_DIA"
    if nuevo_estado != cred["estadoCredito"]:
        db.ejecutar("UPDATE CREDITO SET estadoCredito = %s WHERE codCredito = %s", (nuevo_estado, cod))
        registrar_evento(db, cod, f"CREDITO_{nuevo_estado}", usuario=usuario)
    return nuevo_estado


def recalcular_estado(db, cod, fecha_referencia=None, usuario="sistema"):
    """Punto de entrada publico (endpoint manual) para recalcular el estado con una fecha de referencia
    a eleccion, util para demostrar la transicion a EN_MORA sin esperar al vencimiento real."""
    obtener_credito(db, cod)  # valida existencia (404 si no)
    try:
        recalcular_estado_credito(db, cod, fecha_referencia, usuario=usuario)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return obtener_credito(db, cod)


# ------------------------------------------------------------------ CR-INT-06
def activar_obligacion(db, d, usuario="DESEMBOLSO (CR-INT-06)"):
    """CR-INT-06 (Desembolso a Cobranza). RN-COB-001: solo se cobran creditos desembolsados y activados."""
    cod = d["codCredito"]
    monto = D(d["montoAprobado"])
    moneda = d.get("moneda") or "PEN"
    cal = d.get("calendarioPagos") or []
    if monto <= 0:
        raise ErrorNegocio(422, "montoAprobado debe ser mayor a cero", "CR-INT-06")
    if moneda not in ("PEN", "USD"):
        raise ErrorNegocio(422, "moneda debe ser PEN o USD", "CR-INT-06")
    if not cal:
        raise ErrorNegocio(422, "calendarioPagos no puede estar vacio", "CR-INT-06")
    numeros = [int(c["numeroCuota"]) for c in cal]
    if min(numeros) < 1 or len(set(numeros)) != len(numeros):
        raise ErrorNegocio(422, "numeroCuota debe ser mayor a cero y no repetirse", "CR-INT-06")
    if any(D(c["montoCuota"]) <= 0 for c in cal):
        raise ErrorNegocio(422, "montoCuota debe ser mayor a cero", "CR-INT-06")
    if db.uno("SELECT codCredito FROM CREDITO WHERE codCredito = %s", (cod,)):
        raise ErrorNegocio(409, "El credito ya fue activado en Cobranza", "RN-COB-001")
    try:
        db.ejecutar(
            "INSERT INTO CREDITO (codCredito, idCliente, idSolicitud, montoAprobado, moneda, fechaDesembolso, estadoCredito) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (cod, d["idCliente"], d["idSolicitud"], monto, moneda, _fecha(d["fechaDesembolso"]), "AL_DIA"),
        )
        for c in sorted(cal, key=lambda x: int(x["numeroCuota"])):
            mc = D(c["montoCuota"])
            db.ejecutar(
                "INSERT INTO CUOTA (idCuota, codCredito, numeroCuota, fechaVencimiento, montoCuota, saldoPendiente, "
                "moraPendiente, estadoCuota) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (nuevo_id("CU"), cod, int(c["numeroCuota"]), _fecha(c["fechaVencimiento"], True), mc, mc, CERO,
                 "PENDIENTE"),
            )
        registrar_evento(db, cod, "OBLIGACION_ACTIVADA", usuario=usuario)
        recalcular_estado_credito(db, cod, usuario=usuario)  # por si ya trae una cuota vencida al activar
        db.commit()
    except Exception:
        db.rollback()
        raise
    return obtener_credito(db, cod)


# ------------------------------------------------------------------ consultas
def obtener_credito(db, cod):
    cred = db.uno("SELECT * FROM CREDITO WHERE codCredito = %s", (cod,))
    if not cred:
        raise ErrorNegocio(404, "Credito no encontrado en Cobranza", "RN-COB-001")
    filas = db.todos("SELECT * FROM CUOTA WHERE codCredito = %s ORDER BY numeroCuota", (cod,))
    cuotas = []
    for f in filas:
        capital = D(f["saldoPendiente"])
        mora = D(f["moraPendiente"])
        cuotas.append({
            "idCuota": f["idCuota"], "numeroCuota": f["numeroCuota"],
            "fechaVencimiento": str(f["fechaVencimiento"])[:10],
            "montoCuota": D(f["montoCuota"]), "saldoPendiente": capital, "moraPendiente": mora,
            "totalAdeudado": capital + mora, "estadoCuota": f["estadoCuota"],
        })
    return {
        "codCredito": cred["codCredito"], "idCliente": cred["idCliente"],
        "montoAprobado": D(cred["montoAprobado"]), "moneda": cred["moneda"],
        "fechaDesembolso": str(cred["fechaDesembolso"])[:19], "estadoCredito": cred["estadoCredito"],
        "saldoTotalPendiente": sum((c["totalAdeudado"] for c in cuotas), CERO),
        "cuotas": cuotas,
    }


def monto_a_pagar(db, cod):
    """RF-COB-003: desglose de la proxima cuota pendiente (saldo de capital + mora vigente + total)."""
    obtener_credito(db, cod)  # valida existencia (404 si no)
    cuota = db.uno(
        "SELECT * FROM CUOTA WHERE codCredito = %s AND (saldoPendiente > 0 OR moraPendiente > 0) "
        "ORDER BY numeroCuota LIMIT 1", (cod,))
    if not cuota:
        raise ErrorNegocio(409, "El credito no tiene cuotas pendientes", "RF-COB-003")
    capital = D(cuota["saldoPendiente"])
    mora = D(cuota["moraPendiente"])
    return {
        "codCredito": cod, "idCuota": cuota["idCuota"], "numeroCuota": cuota["numeroCuota"],
        "fechaVencimiento": str(cuota["fechaVencimiento"])[:10],
        "saldoCapital": capital, "moraVigente": mora, "totalAPagar": capital + mora,
    }


def creditos_por_cliente(db, id_cliente):
    """RF-COB-002 / RF-COB-012: creditos (con su cronograma) de un cliente, consultados por idCliente."""
    filas = db.todos(
        "SELECT codCredito FROM CREDITO WHERE idCliente = %s ORDER BY fechaDesembolso, codCredito", (id_cliente,))
    return [obtener_credito(db, f["codCredito"]) for f in filas]


def pagos_por_cliente(db, id_cliente):
    """RF-COB-002 / RF-COB-012: historial de pagos de un cliente, consultado por idCliente."""
    filas = db.todos(
        "SELECT p.*, c.nombreCanal FROM PAGO p JOIN CANAL_PAGO c ON c.idCanal = p.idCanal "
        "JOIN CREDITO cr ON cr.codCredito = p.codCredito WHERE cr.idCliente = %s "
        "ORDER BY p.fechaHora DESC, p.idPago", (id_cliente,))
    return [{"idPago": f["idPago"], "codCredito": f["codCredito"], "referenciaTransaccion": f["referenciaTransaccion"],
             "fechaHora": str(f["fechaHora"])[:19], "canal": f["nombreCanal"],
             "montoPago": D(f["montoPago"]), "estado": f["estadoConfirmacion"]} for f in filas]


def _resultado(db, id_pago, idempotente):
    p = db.uno("SELECT * FROM PAGO WHERE idPago = %s", (id_pago,))
    ap = db.uno(
        "SELECT a.idCuota, a.montoAplicado, c.numeroCuota, c.saldoPendiente, c.moraPendiente, c.estadoCuota "
        "FROM APLICACION_PAGO a JOIN CUOTA c ON c.idCuota = a.idCuota WHERE a.idPago = %s", (id_pago,))
    cred = db.uno("SELECT estadoCredito FROM CREDITO WHERE codCredito = %s", (p["codCredito"],))
    aplicacion = None
    if ap:
        aplicacion = {"idCuota": ap["idCuota"], "numeroCuota": ap["numeroCuota"],
                      "montoAplicado": D(ap["montoAplicado"]),
                      # RF-COB-008/013: desglose del pago entre mora y capital (orden de imputacion, ver README)
                      "montoAplicadoMora": D(p["montoMora"]), "montoAplicadoCapital": D(p["montoCapital"]),
                      "saldoPendienteCuota": D(ap["saldoPendiente"]), "moraPendienteCuota": D(ap["moraPendiente"]),
                      "estadoCuota": ap["estadoCuota"]}
    return {
        "idPago": p["idPago"], "referenciaTransaccion": p["referenciaTransaccion"],
        "estado": p["estadoConfirmacion"], "idempotente": idempotente, "motivo": None,
        "codCredito": p["codCredito"], "idCanal": p["idCanal"], "montoPago": D(p["montoPago"]),
        "fechaHora": str(p["fechaHora"])[:19], "aplicacion": aplicacion,
        "estadoCredito": cred["estadoCredito"],
    }


def _aplicar_a_cuota(db, id_pago, cod, cuota, monto, monto_mora, monto_capital, usuario="sistema"):
    """Aplica un pago ya CONFIRMADO a una cuota: registra APLICACION_PAGO, descuenta capital/mora,
    deja los eventos de auditoria y recalcula CANCELADO / AL_DIA / EN_MORA (RF-COB-007). No hace commit;
    el llamador decide la transaccion. Usado por registrar_pago y por resolver_pago (RF-COB-011)."""
    db.ejecutar(
        "INSERT INTO APLICACION_PAGO (idAplicacion, idPago, idCuota, montoAplicado) VALUES (%s, %s, %s, %s)",
        (nuevo_id("APL"), id_pago, cuota["idCuota"], monto))
    saldo_capital = D(cuota["saldoPendiente"])
    mora_pendiente = D(cuota["moraPendiente"])
    nuevo_capital = saldo_capital - monto_capital
    nueva_mora = mora_pendiente - monto_mora
    nuevo_estado = "PAGADA" if (nuevo_capital == 0 and nueva_mora == 0) else "PARCIAL"
    db.ejecutar("UPDATE CUOTA SET saldoPendiente = %s, moraPendiente = %s, estadoCuota = %s WHERE idCuota = %s",
                (nuevo_capital, nueva_mora, nuevo_estado, cuota["idCuota"]))
    registrar_evento(db, id_pago, "PAGO_APLICADO", usuario=usuario)
    registrar_evento(db, cuota["idCuota"], "CUOTA_" + nuevo_estado, usuario=usuario)
    pend = db.uno(
        "SELECT COUNT(*) AS n FROM CUOTA WHERE codCredito = %s AND (saldoPendiente > 0 OR moraPendiente > 0)",
        (cod,))
    if pend["n"] == 0:
        db.ejecutar("UPDATE CREDITO SET estadoCredito = %s WHERE codCredito = %s", ("CANCELADO", cod))
        registrar_evento(db, cod, "CREDITO_CANCELADO", usuario=usuario)
    else:
        recalcular_estado_credito(db, cod, usuario=usuario)


def _split_imputacion(monto, saldo_capital, mora_pendiente):
    """SUPUESTO provisional de orden de imputacion (ORDEN_IMPUTACION_MORA_PRIMERO), pendiente del Comite."""
    if ORDEN_IMPUTACION_MORA_PRIMERO:
        monto_mora = min(monto, mora_pendiente)
        monto_capital = monto - monto_mora
    else:
        monto_capital = min(monto, saldo_capital)
        monto_mora = monto - monto_capital
    return monto_mora, monto_capital


# ------------------------------------------------------------------ CR-INT-08 y CR-INT-07
def registrar_pago(db, d, cuentas, seguridad, token_seguridad, usuario="HOME BANKING (CR-INT-08)"):
    """CR-INT-08 (Home Banking a Cobranza). Aplica RN-COB-001/002/003/004/006/009/011/012 y RN-INT-CR-006.
    RF-COB-004 (PROPUESTA, pendiente del Comite): valida X-Token-Seguridad con el validador de Seguridad
    simulado antes que cualquier otra cosa; tras 3 rechazos seguidos para el mismo cliente, sus pagos
    quedan bloqueados temporalmente (ver COBRANZA/seguridad.py)."""
    ok_seg, motivo_seg = seguridad.validar(d["codCliente"], token_seguridad)
    if not ok_seg:
        registrar_evento(db, d["codCliente"], "TOKEN_SEGURIDAD_RECHAZADO", usuario=usuario, resultado="RECHAZADO")
        db.commit()
        raise ErrorNegocio(401, motivo_seg, "RF-COB-004")

    ref = d["referenciaTransaccion"]
    previo = db.uno("SELECT idPago FROM PAGO WHERE referenciaTransaccion = %s", (ref,))
    if previo:  # idempotencia: el mismo identificador no genera un segundo pago
        return _resultado(db, previo["idPago"], True)

    monto = D(d["montoPago"])
    if monto <= 0:
        raise ErrorNegocio(422, "montoPago debe ser mayor a cero", "RN-COB-004")
    id_canal = d.get("idCanal") or "HB"
    if not db.uno("SELECT idCanal FROM CANAL_PAGO WHERE idCanal = %s", (id_canal,)):
        raise ErrorNegocio(422, f"Canal '{id_canal}' no habilitado. Solo Home Banking (HB) esta confirmado", "RN-COB-002")
    cred = db.uno("SELECT * FROM CREDITO WHERE codCredito = %s", (d["codCredito"],))
    if not cred:
        raise ErrorNegocio(404, "Credito no encontrado en Cobranza", "RN-COB-001")
    if cred["idCliente"] != d["codCliente"]:
        raise ErrorNegocio(403, "El credito no pertenece al cliente indicado", "CR-INT-08")
    if cred["estadoCredito"] == "CANCELADO":
        raise ErrorNegocio(409, "El credito esta CANCELADO; no admite mas pagos", "RN-COB-001")
    cuota = db.uno(
        "SELECT * FROM CUOTA WHERE codCredito = %s AND (saldoPendiente > 0 OR moraPendiente > 0) "
        "ORDER BY numeroCuota LIMIT 1", (d["codCredito"],))
    if not cuota:
        raise ErrorNegocio(409, "El credito no tiene cuotas pendientes", "RN-COB-001")
    saldo_capital = D(cuota["saldoPendiente"])
    mora_pendiente = D(cuota["moraPendiente"])
    total_adeudado = saldo_capital + mora_pendiente
    if monto > total_adeudado:
        raise ErrorNegocio(
            422, f"El monto {monto} excede el saldo adeudado de la cuota {total_adeudado} "
                 f"(capital {saldo_capital} + mora {mora_pendiente}). "
                 "El tratamiento del excedente esta pendiente de definicion del Comite", "RN-COB-011")

    monto_mora, monto_capital = _split_imputacion(monto, saldo_capital, mora_pendiente)

    id_pago = nuevo_id("PAG")
    try:
        db.ejecutar(
            "INSERT INTO PAGO (idPago, codCredito, idCanal, fechaHora, montoPago, montoMora, montoCapital, "
            "referenciaTransaccion, estadoConfirmacion, cuentaOrigen) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (id_pago, d["codCredito"], id_canal, ahora(), monto, monto_mora, monto_capital, ref, "PENDIENTE",
             d["cuentaOrigen"]))
        registrar_evento(db, id_pago, "PAGO_REGISTRADO", usuario=usuario)
        db.commit()
    except Exception:
        db.rollback()
        raise

    # CR-INT-07: solicitar el cargo a Cuentas. Cobranza nunca mueve el dinero por si misma.
    estado, motivo = cuentas.cargar(d["codCredito"], d["cuentaOrigen"], monto, cred["moneda"], ref)

    try:
        if estado == "CONFIRMADO":
            db.ejecutar("UPDATE PAGO SET estadoConfirmacion = %s WHERE idPago = %s", ("CONFIRMADO", id_pago))
            _aplicar_a_cuota(db, id_pago, d["codCredito"], cuota, monto, monto_mora, monto_capital, usuario=usuario)
        elif estado == "RECHAZADO":  # RN-COB-009: la cuota no se cierra sin confirmacion
            db.ejecutar("UPDATE PAGO SET estadoConfirmacion = %s WHERE idPago = %s", ("RECHAZADO", id_pago))
            registrar_evento(db, id_pago, "PAGO_RECHAZADO", usuario=usuario, resultado="RECHAZADO")
        else:  # sin respuesta: queda PENDIENTE, no se cierra la cuota ni se reintenta el cargo
            registrar_evento(db, id_pago, "PAGO_SIN_CONFIRMAR", usuario=usuario, resultado="PENDIENTE")
        db.commit()
    except Exception:
        db.rollback()
        raise
    r = _resultado(db, id_pago, False)
    r["motivo"] = motivo
    return r


def _parse_dt(v):
    if isinstance(v, datetime):
        return v
    return datetime.strptime(str(v)[:19], "%Y-%m-%d %H:%M:%S")


def pagos_pendientes(db):
    """RF-COB-011 / INC-01 (I-04): pagos en estado PENDIENTE con su antiguedad en horas."""
    filas = db.todos("SELECT * FROM PAGO WHERE estadoConfirmacion = 'PENDIENTE' ORDER BY fechaHora")
    ahora_dt = datetime.now()
    out = []
    for f in filas:
        horas = round((ahora_dt - _parse_dt(f["fechaHora"])).total_seconds() / 3600, 2)
        out.append({
            "idPago": f["idPago"], "codCredito": f["codCredito"],
            "referenciaTransaccion": f["referenciaTransaccion"], "fechaHora": str(f["fechaHora"])[:19],
            "montoPago": D(f["montoPago"]), "antiguedadHoras": horas,
        })
    return out


def resolver_pago(db, ref, cuentas, usuario="sistema"):
    """RF-COB-011 / INC-01: resuelve un pago que quedo PENDIENTE consultando a Cuentas por su
    idOperacion (RN-COB-009: un cargo incierto nunca se reintenta, solo se consulta).
    Si Cuentas confirma, se aplica con el estado ACTUAL de la cuota (pudo cambiar mientras el pago
    estaba pendiente): si el monto ya excede lo adeudado, el dinero ya se cobro pero no se puede aplicar
    sin mas, asi que queda REQUIERE_REVISION (la politica de reversion financiera esta pendiente del
    Comite). Si Cuentas rechaza, el pago queda RECHAZADO. Si Cuentas sigue sin responder, no cambia nada."""
    p = db.uno("SELECT * FROM PAGO WHERE referenciaTransaccion = %s", (ref,))
    if not p:
        raise ErrorNegocio(404, "Pago no encontrado", "RN-COB-012")
    if p["estadoConfirmacion"] != "PENDIENTE":
        raise ErrorNegocio(
            409, f"El pago esta {p['estadoConfirmacion']}; solo se resuelven pagos PENDIENTE", "RN-COB-009")

    estado, motivo = cuentas.consultar(ref, pago=p)  # RN-COB-009: se consulta, nunca se reintenta el cargo

    if estado == "SIN_RESPUESTA":
        registrar_evento(db, p["idPago"], "PAGO_SIN_CONFIRMAR", usuario=usuario, resultado="PENDIENTE")
        db.commit()
        r = _resultado(db, p["idPago"], False)
        r["motivo"] = motivo
        return r

    if estado == "RECHAZADO":
        try:
            db.ejecutar("UPDATE PAGO SET estadoConfirmacion = %s WHERE idPago = %s", ("RECHAZADO", p["idPago"]))
            registrar_evento(db, p["idPago"], "PAGO_RECHAZADO", usuario=usuario, resultado="RECHAZADO")
            db.commit()
        except Exception:
            db.rollback()
            raise
        r = _resultado(db, p["idPago"], False)
        r["motivo"] = motivo
        return r

    # estado == "CONFIRMADO": el dinero ya se cobro. Se aplica con el estado actual de la cuota.
    monto = D(p["montoPago"])
    try:
        cuota = db.uno(
            "SELECT * FROM CUOTA WHERE codCredito = %s AND (saldoPendiente > 0 OR moraPendiente > 0) "
            "ORDER BY numeroCuota LIMIT 1", (p["codCredito"],))
        total_adeudado = D(cuota["saldoPendiente"]) + D(cuota["moraPendiente"]) if cuota else CERO
        if not cuota or monto > total_adeudado:
            db.ejecutar("UPDATE PAGO SET estadoConfirmacion = %s WHERE idPago = %s",
                        ("REQUIERE_REVISION", p["idPago"]))
            registrar_evento(db, p["idPago"], "PAGO_REQUIERE_REVISION", usuario=usuario, resultado="REVISION")
            db.commit()
            r = _resultado(db, p["idPago"], False)
            if not cuota:
                r["motivo"] = ("Cuentas confirmo el cargo, pero el credito ya no tiene cuotas pendientes. "
                                "Requiere revision manual; la politica de reversion esta pendiente del Comite")
            else:
                r["motivo"] = (f"Cuentas confirmo el cargo de {monto}, pero ya excede el saldo adeudado "
                                f"actual de la cuota ({total_adeudado}). Requiere revision manual; la "
                                "politica de reversion financiera esta pendiente del Comite")
            return r

        saldo_capital = D(cuota["saldoPendiente"])
        mora_pendiente = D(cuota["moraPendiente"])
        monto_mora, monto_capital = _split_imputacion(monto, saldo_capital, mora_pendiente)
        db.ejecutar(
            "UPDATE PAGO SET estadoConfirmacion = %s, montoMora = %s, montoCapital = %s WHERE idPago = %s",
            ("CONFIRMADO", monto_mora, monto_capital, p["idPago"]))
        _aplicar_a_cuota(db, p["idPago"], p["codCredito"], cuota, monto, monto_mora, monto_capital, usuario=usuario)
        db.commit()
    except Exception:
        db.rollback()
        raise
    r = _resultado(db, p["idPago"], False)
    r["motivo"] = motivo
    return r


def comprobante(db, ref):
    """RN-COB-012: trazabilidad del origen del pago."""
    p = db.uno(
        "SELECT p.*, c.nombreCanal FROM PAGO p JOIN CANAL_PAGO c ON c.idCanal = p.idCanal "
        "WHERE p.referenciaTransaccion = %s", (ref,))
    if not p:
        raise ErrorNegocio(404, "Pago no encontrado", "RN-COB-012")
    if p["estadoConfirmacion"] != "CONFIRMADO":
        raise ErrorNegocio(409, f"El pago esta {p['estadoConfirmacion']}; solo se emite comprobante de pagos confirmados", "RN-COB-009")
    r = _resultado(db, p["idPago"], False)
    cred = obtener_credito(db, p["codCredito"])
    return {
        "numeroOperacion": ref, "fechaHora": r["fechaHora"], "canal": p["nombreCanal"],
        "codCredito": p["codCredito"], "montoPagado": r["montoPago"],
        # RF-COB-008/013: cuanto del pago cubrio mora y cuanto capital (orden de imputacion, ver README)
        "montoAplicadoMora": r["aplicacion"]["montoAplicadoMora"],
        "montoAplicadoCapital": r["aplicacion"]["montoAplicadoCapital"],
        "cuotaNumero": r["aplicacion"]["numeroCuota"],
        "saldoRestanteCuota": r["aplicacion"]["saldoPendienteCuota"],
        "moraRestanteCuota": r["aplicacion"]["moraPendienteCuota"],
        "saldoRestanteCredito": cred["saldoTotalPendiente"], "estadoCredito": cred["estadoCredito"],
    }


def historial_pagos(db, cod):
    obtener_credito(db, cod)
    filas = db.todos("SELECT p.*, c.nombreCanal FROM PAGO p JOIN CANAL_PAGO c ON c.idCanal = p.idCanal "
                     "WHERE p.codCredito = %s ORDER BY p.fechaHora DESC, p.idPago", (cod,))
    return [{"idPago": f["idPago"], "referenciaTransaccion": f["referenciaTransaccion"],
             "fechaHora": str(f["fechaHora"])[:19], "canal": f["nombreCanal"],
             "montoPago": D(f["montoPago"]), "estado": f["estadoConfirmacion"]} for f in filas]


# ------------------------------------------------------------------ mora (valor recibido)
def _cuota_por_numero(db, cod, numero):
    cuota = db.uno("SELECT * FROM CUOTA WHERE codCredito = %s AND numeroCuota = %s", (cod, numero))
    if not cuota:
        raise ErrorNegocio(404, "Cuota no encontrada", "RN-COB-010")
    return cuota


def registrar_mora(db, cod, numero, dias_atraso, monto_calculado, origen="CORE (simulado)", fecha_referencia=None):
    """Registra una mora RECIBIDA, separada del saldo de capital de la cuota (CUOTA.moraPendiente).
    La formula y quien la calcula estan pendientes del Comite (RN-COB-005): Cobranza no calcula ni asume
    tasa; solo guarda el valor que le llega. Un recalculo REEMPLAZA la mora pendiente vigente
    (no se suma) y conserva el historial completo en la tabla MORA (campo vigente).
    RN-COB-010: la cuota debe estar vencida respecto de fecha_referencia (por defecto hoy; parametro
    opcional para poder demostrarlo), y diasAtraso en 0 no admite un montoCalculado mayor a cero."""
    cuota = _cuota_por_numero(db, cod, numero)
    if cuota["estadoCuota"] == "PAGADA":
        raise ErrorNegocio(409, "La cuota ya esta pagada; no admite mora", "RN-COB-010")
    monto = D(monto_calculado)
    dias = int(dias_atraso)
    if monto < 0 or dias < 0:
        raise ErrorNegocio(422, "diasAtraso y montoCalculado no pueden ser negativos", "RN-COB-005")
    if dias == 0 and monto > 0:
        raise ErrorNegocio(422, "diasAtraso en 0 no admite un montoCalculado mayor a cero", "RN-COB-010")
    ref = _fecha(fecha_referencia, True) if fecha_referencia else date.today().strftime("%Y-%m-%d")
    if str(cuota["fechaVencimiento"])[:10] >= ref:
        raise ErrorNegocio(422, "La cuota todavia no vencio; no admite mora", "RN-COB-010")
    prev = db.uno("SELECT idMora FROM MORA WHERE idCuota = %s AND vigente = %s", (cuota["idCuota"], 1))
    id_mora = nuevo_id("MOR")
    try:
        if prev:  # un recalculo reemplaza al vigente y conserva el historial
            db.ejecutar("UPDATE MORA SET vigente = %s WHERE idMora = %s", (0, prev["idMora"]))
        db.ejecutar(
            "INSERT INTO MORA (idMora, idCuota, diasAtraso, montoCalculado, fechaCalculo, vigente) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (id_mora, cuota["idCuota"], int(dias_atraso), monto, ahora(), 1))
        db.ejecutar("UPDATE CUOTA SET moraPendiente = %s WHERE idCuota = %s", (monto, cuota["idCuota"]))
        registrar_evento(db, cuota["idCuota"], "MORA_REGISTRADA", usuario=origen)
        recalcular_estado_credito(db, cod, usuario=origen)  # RF-COB-007
        db.commit()
    except Exception:
        db.rollback()
        raise
    actual = db.uno("SELECT saldoPendiente FROM CUOTA WHERE idCuota = %s", (cuota["idCuota"],))
    return {"idMora": id_mora, "codCredito": cod, "numeroCuota": numero, "diasAtraso": int(dias_atraso),
            "montoCalculado": monto, "vigente": True,
            "saldoCapitalCuota": D(actual["saldoPendiente"]), "moraPendienteCuota": monto}


def historial_mora(db, cod, numero):
    cuota = _cuota_por_numero(db, cod, numero)
    filas = db.todos("SELECT * FROM MORA WHERE idCuota = %s ORDER BY fechaCalculo, idMora", (cuota["idCuota"],))
    return [{"idMora": f["idMora"], "diasAtraso": f["diasAtraso"], "montoCalculado": D(f["montoCalculado"]),
             "fechaCalculo": str(f["fechaCalculo"])[:19], "vigente": bool(f["vigente"])} for f in filas]


def auditoria(db, id_entidad=None, limite=50):
    if id_entidad:
        filas = db.todos("SELECT * FROM EVENTO_AUDITORIA WHERE idEntidad = %s ORDER BY `timestamp` DESC, idEvento LIMIT %s",
                         (id_entidad, int(limite)))
    else:
        filas = db.todos("SELECT * FROM EVENTO_AUDITORIA ORDER BY `timestamp` DESC, idEvento LIMIT %s", (int(limite),))
    return [{"idEvento": f["idEvento"], "idEntidad": f["idEntidad"], "tipoEvento": f["tipoEvento"],
             "timestamp": str(f["timestamp"])[:19], "moduloEmisor": f["moduloEmisor"],
             "usuarioOperador": f["usuarioOperador"], "resultado": f["resultado"]} for f in filas]


# ------------------------------------------------------------------ RF-COB-018 / indicadores I-05
def _pagos_por_estado_y_fecha(db, estado, fecha):
    filas = db.todos(
        "SELECT * FROM PAGO WHERE estadoConfirmacion = %s AND DATE(fechaHora) = %s ORDER BY fechaHora",
        (estado, fecha))
    return [{"idPago": f["idPago"], "codCredito": f["codCredito"], "referenciaTransaccion": f["referenciaTransaccion"],
             "fechaHora": str(f["fechaHora"])[:19], "montoPago": D(f["montoPago"])} for f in filas]


def conciliacion(db, fecha=None, usuario="sistema"):
    """RF-COB-018 (I-04/I-05): total cobrado (CONFIRMADO + REQUIERE_REVISION, dinero que Cuentas si
    cargo) vs total aplicado (APLICACION_PAGO, solo pagos CONFIRMADO que se abonaron a una cuota) del
    dia. La diferencia entre ambos delata pagos REQUIERE_REVISION (cobrados pero no aplicados).
    Tambien el detalle de pagos pendientes (con antiguedad, sin filtrar por dia: es un backlog abierto),
    rechazados y REQUIERE_REVISION del dia. Deja un evento CONCILIACION_EJECUTADA."""
    f = _fecha(fecha, True) if fecha else date.today().strftime("%Y-%m-%d")
    cobrado = db.uno(
        "SELECT COUNT(*) AS n, COALESCE(SUM(montoPago), 0) AS total FROM PAGO "
        "WHERE estadoConfirmacion IN ('CONFIRMADO','REQUIERE_REVISION') AND DATE(fechaHora) = %s", (f,))
    aplicado = db.uno(
        "SELECT COALESCE(SUM(a.montoAplicado), 0) AS total FROM APLICACION_PAGO a "
        "JOIN PAGO p ON p.idPago = a.idPago WHERE p.estadoConfirmacion = 'CONFIRMADO' AND DATE(p.fechaHora) = %s",
        (f,))
    total_cobrado = D(cobrado["total"])
    total_aplicado = D(aplicado["total"])

    try:
        registrar_evento(db, f"CONCIL-{f}", "CONCILIACION_EJECUTADA", usuario=usuario)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "fecha": f, "totalCobrado": total_cobrado, "totalAplicado": total_aplicado,
        "diferencia": total_cobrado - total_aplicado, "cantidadPagosCobrados": cobrado["n"],
        "pagosPendientes": pagos_pendientes(db),
        "pagosRechazados": _pagos_por_estado_y_fecha(db, "RECHAZADO", f),
        "pagosRequierenRevision": _pagos_por_estado_y_fecha(db, "REQUIERE_REVISION", f),
    }


def metricas(db, p95_pago_ms=None, muestras_pago=0):
    """Indicadores I-05, SIN metas numericas (solo el valor medido). Tasa de fallas de operacion =
    pagos no confirmados o fallidos / intentos validos. Cada fila de PAGO ya es un "intento valido":
    los rechazos por datos invalidos (RN-COB-002/004/011, etc.) no llegan a insertar un PAGO, y los
    duplicados (idempotencia, RN-INT-CR-006) tampoco crean una fila nueva."""
    total = db.uno("SELECT COUNT(*) AS n FROM PAGO")["n"]
    fallidos = db.uno(
        "SELECT COUNT(*) AS n FROM PAGO WHERE estadoConfirmacion IN ('RECHAZADO','PENDIENTE','REQUIERE_REVISION')"
    )["n"]
    pendientes = db.uno("SELECT COUNT(*) AS n FROM PAGO WHERE estadoConfirmacion = 'PENDIENTE'")["n"]
    tasa_fallas = round(fallidos / total, 4) if total else None
    return {
        "intentosValidos": total, "pagosFallidos": fallidos, "tasaFallasOperacion": tasa_fallas,
        "pagosPendientes": pendientes,
        "tiempoRespuestaPagosP95Ms": p95_pago_ms, "muestrasTiempoRespuesta": muestras_pago,
    }
