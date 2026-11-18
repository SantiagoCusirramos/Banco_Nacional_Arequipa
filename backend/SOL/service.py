"""Reglas del expediente y traducción entre COREDB y las respuestas de SOL.

El borrador vive en COREDB (creditos.*, bd-v1.14-mysql). SOL valida contra su política,
calcula el calendario y arma el detalle que muestra el frontend con lo que guardó COREDB y la
identidad que da Captación. Las respuestas conservan las formas de SOL v2.
"""

from datetime import date
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException

from .clock import business_today
from .finance import calendar, money
from .integrations import project_identity

# idOperacion de CR-INT-02: uno por versión de solicitud, así un reintento (con cualquier clave
# del navegador) manda exactamente el mismo sobre.
ESPACIO_SOL = uuid5(NAMESPACE_URL, "https://bna.local/sol/cr-int-02")
ACCIONES = {"EN_EVALUACION": "ENVIAR_CR_INT_02", "APROBADA": "RESULTADO_EVALUACION",
            "RECHAZADA": "RESULTADO_EVALUACION", "DESEMBOLSADA": "DESEMBOLSO"}


def operation_id(identifier, version):
    return str(uuid5(ESPACIO_SOL, f"{identifier}:{version}"))


def check_conditions(payload, policy):
    """El servidor valida contra la política. Nunca acepta cuotas calculadas por la UI."""
    if payload.moneda not in policy.monedas:
        raise HTTPException(422, "Moneda no habilitada en esta versión de la política.")
    if not policy.monto_minimo <= payload.monto_solicitado <= policy.monto_maximo:
        raise HTTPException(422, f"Monto permitido: {policy.monto_minimo}–{policy.monto_maximo} {payload.moneda}.")
    if not policy.plazo_minimo_meses <= payload.plazo_meses <= policy.plazo_maximo_meses:
        raise HTTPException(422, "Plazo fuera del rango configurado.")
    if payload.pago_doble:
        raise HTTPException(422, "Pago doble pendiente de definición; no hay una fórmula aprobada.")
    if payload.fecha_base < business_today():
        raise HTTPException(422, "La fecha base no puede ser anterior a hoy en un nuevo cálculo.")
    if len(set(payload.fiadores)) != len(payload.fiadores) or payload.id_cliente in payload.fiadores:
        raise HTTPException(422, "Las referencias de fiadores no pueden repetirse ni ser la del solicitante.")


def schedule(amount, policy_data, months, base_date):
    return calendar(Decimal(str(amount)), Decimal(str(policy_data["tea"])), months,
                    date.fromisoformat(str(base_date)), int(policy_data["dias_por_periodo"]))


def snapshot(client, conditions, guarantors, policy_data, schedule_data):
    return {"cliente": client, "condiciones": conditions, "fiadores": guarantors,
            "politica": policy_data, "calendario": schedule_data}


def prepare(integrations, payload, policy, correlation):
    """El expediente que vería Evaluación: cliente y fiadores habilitados por Captación."""
    check_conditions(payload, policy)
    client = integrations.reference(payload.id_cliente, correlation)
    guarantors = []
    for identifier in payload.fiadores:
        try:
            identity = integrations.reference(identifier, correlation)
        except HTTPException as exc:
            if exc.status_code == 422:
                raise HTTPException(422, "El fiador requiere una referencia de Captación activa y vigente.") from None
            raise
        guarantors.append({"id_cliente": identifier, "identidad": identity, "validacion": "CAPTACION"})
    policy_data = policy.model_dump(mode="json")
    conditions = payload.model_dump(mode="json", exclude={"revision", "fiadores"})
    conditions["id_producto_credito"] = policy.producto_id
    return snapshot(client, conditions, guarantors, policy_data,
                    schedule(payload.monto_solicitado, policy_data, payload.plazo_meses, payload.fecha_base))


def draft_body(payload, policy):
    """El cuerpo de POST/PUT /coredb/creditos/borradores."""
    return {
        "codCliente": payload.id_cliente, "montoSolicitado": money(payload.monto_solicitado),
        "moneda": payload.moneda, "plazoMeses": payload.plazo_meses, "condicionPagoDoble": payload.pago_doble,
        "destino": payload.destino_credito, "fechaBase": payload.fecha_base.isoformat(),
        "politica": policy.model_dump(mode="json"),
        "garantias": [{"tipo": g.tipo_garantia, "descripcion": g.descripcion, "valor": money(g.valor_tasacion)}
                      for g in payload.garantias],
        "fiadores": list(payload.fiadores),
    }


def iso(value):
    """Fechas de COREDB (UTC con zona) con el formato de SOL: segundos y sufijo Z."""
    if not value:
        return ""
    text = str(value).replace("+00:00", "").replace("Z", "")
    return text.split(".")[0] + "Z"


def _schedule_from_coredb(data):
    rows, interest, total = [], Decimal(0), Decimal(0)
    for c in data["cuotas"]:
        capital, saldo = Decimal(c["capital"]), Decimal(c["saldoCapital"])
        cuota = Decimal(c["cuotaTotal"])
        interest += Decimal(c["interes"])
        total += cuota
        rows.append({"numero_cuota": c["numeroCuota"], "fecha_vencimiento": c["fechaVencimiento"],
                     "saldo_inicial": money(saldo + capital), "amortizacion": money(capital),
                     "interes": money(Decimal(c["interes"])), "cuota_total": money(cuota),
                     "saldo_final": money(saldo)})
    return {"estado": data["tipo"], "cuotas": rows, "cuota_referencial": rows[0]["cuota_total"] if rows else "0.00",
            "intereses_totales": money(interest), "total_pagar": money(total)}


def snapshot_from_coredb(detail, identity):
    """El expediente de SOL a partir del detalle de COREDB. `identity(cod)` da la identidad."""
    expediente = detail["expediente"]
    policy_data = expediente["politica"]
    client = project_identity(identity(detail["codCliente"]))
    conditions = {
        "id_cliente": detail["codCliente"], "monto_solicitado": detail["montoSolicitado"],
        "moneda": detail["moneda"], "plazo_meses": detail["plazoMeses"],
        "destino_credito": expediente["destino"], "fecha_base": expediente["fechaBase"],
        "pago_doble": detail["condicionPagoDoble"],
        "garantias": [{"tipo_garantia": g["tipo"], "descripcion": g["descripcion"] or "",
                       "valor_tasacion": g["valor"]} for g in detail["garantias"]],
        "id_producto_credito": policy_data.get("producto_id", ""),
    }
    guarantors = [{"id_cliente": f["codCliente"], "identidad": project_identity(identity(f["codCliente"])),
                   "validacion": "CAPTACION"} for f in detail["fiadores"]]
    schedule_data = (_schedule_from_coredb(detail["calendario"]) if detail.get("calendario")
                     else schedule(detail["montoSolicitado"], policy_data, detail["plazoMeses"],
                                   expediente["fechaBase"]))
    return snapshot(client, conditions, guarantors, policy_data, schedule_data)


def full_name(client):
    return " ".join(p for p in [client.get("nombres"), client.get("apellido_paterno"),
                                client.get("apellido_materno")] if p)


def summary(row, client):
    return {"id": row["idSolicitud"], "codigo": row.get("codigo") or "", "estado": row["estado"],
            "version": row["versionSolicitud"], "revision": row.get("revision") or 0,
            "cliente_nombre": full_name(client), "documento": client.get("numero_documento", ""),
            "monto": row["montoSolicitado"], "moneda": row["moneda"], "plazo": row["plazoMeses"],
            "actualizado": iso(row.get("fechaCreacion"))}


def events(detail):
    result, previous, created = [], None, False
    for h in detail["historial"]:
        if h["estado"] == "REGISTRADA":
            action = "EDITAR_BORRADOR" if created else "CREAR_BORRADOR"
            created = True
        else:
            action = ACCIONES.get(h["estado"], "CAMBIO_DE_ESTADO")
        result.append({"accion": action, "actor": h["actor"], "version": detail["versionSolicitud"],
                       "estado_anterior": previous, "estado_nuevo": h["estado"], "fecha": iso(h["fechaHora"]),
                       "correlacion": ""})
        previous = h["estado"]
    return result


def outcomes(detail):
    result = []
    for e in detail["evaluaciones"]:
        if e["resultado"] not in ("APROBADO", "RECHAZADO"):
            continue
        observations = e.get("comentario") or f"{e['resultado'].capitalize()} por la regla {e['regla']}."
        result.append({"version": detail["versionSolicitud"], "decision": e["resultado"],
                       "observaciones": observations, "fecha": iso(e.get("fechaDecision") or e["fechaEvaluacion"])})
    return result


def deliveries(detail):
    return [{"version": r["versionSolicitud"], "id_operacion": operation_id(detail["idSolicitud"], r["versionSolicitud"]),
             "acuse": f"ACK-{r['idEvaluacion']}", "estado_transporte": "CONFIRMADO",
             "id_evaluacion": r["idEvaluacion"], "ronda": r["ronda"], "fecha": iso(r["recibidaEn"])}
            for r in detail["recepciones"]]


def application_detail(detail, identity):
    if not detail.get("expediente"):
        raise HTTPException(404, "Solicitud no encontrada.")
    data = snapshot_from_coredb(detail, identity)
    result = summary(detail, data["cliente"])
    result["actualizado"] = iso(detail["expediente"].get("actualizadoEn") or detail.get("fechaCreacion"))
    result["versiones"] = [{"numero": detail["versionSolicitud"], "congelada": detail["estado"] != "REGISTRADA",
                            "expediente": data}]
    result["eventos"] = events(detail)
    result["resultados"] = outcomes(detail)
    result["envios"] = deliveries(detail)
    return result


def evaluation_envelope(detail, snapshot_data, correlation, actor):
    version = detail["versionSolicitud"]
    return {"versionContrato": "CR-INT-02-PROPUESTA-v2", "idSolicitud": detail["idSolicitud"],
            "versionSolicitud": version, "idOperacion": operation_id(detail["idSolicitud"], version),
            "idCorrelacion": correlation, "expediente": snapshot_data, "simulado": False, "actorEnvio": actor}
