"""Reglas de expediente, versionado y eventos compartidas por los endpoints."""

import hashlib
import json
from datetime import date
from copy import deepcopy
from .clock import business_today
from .operations import enqueue
from decimal import Decimal
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select
from .finance import calendar
from .integrations import captacion_reference
from .models import Application, Event, Version, Outcome, Delivery, ClientReference, now


def fingerprint(data) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def prepare(db, payload, policy):
    """El servidor recalcula y valida. Nunca acepta cuotas calculadas por la UI."""
    client = captacion_reference(db, payload.id_cliente)
    if payload.moneda not in policy.monedas:
        raise HTTPException(422, "Moneda no habilitada en esta versión de la política.")
    if not policy.monto_minimo <= payload.monto_solicitado <= policy.monto_maximo:
        raise HTTPException(
            422,
            f"Monto permitido: {policy.monto_minimo}–{policy.monto_maximo} {payload.moneda}.",
        )
    if (
        not policy.plazo_minimo_meses
        <= payload.plazo_meses
        <= policy.plazo_maximo_meses
    ):
        raise HTTPException(422, "Plazo fuera del rango configurado.")
    if payload.pago_doble:
        raise HTTPException(
            422, "Pago doble pendiente de definición; no hay una fórmula aprobada."
        )
    if payload.fecha_base < business_today():
        raise HTTPException(
            422, "La fecha base no puede ser anterior a hoy en un nuevo cálculo."
        )
    if (
        len(set(payload.fiadores)) != len(payload.fiadores)
        or payload.id_cliente in payload.fiadores
    ):
        raise HTTPException(
            422,
            "Las referencias de fiadores no pueden repetirse ni ser la del solicitante.",
        )
    if payload.fiadores and db.info.get("integration_mode") == "REAL":
        raise HTTPException(422, "La referencia institucional de fiadores requiere homologar su contrato; no se usan datos simulados en REAL.")
    fiadores = []
    for identifier in payload.fiadores:
        ref = db.get(ClientReference, identifier)
        if not ref or ref.snapshot["estado_cliente"] != "ACTIVO":
            raise HTTPException(
                422, "El fiador requiere una referencia de identidad activa."
            )
        fiadores.append(
            {
                "id_cliente": identifier,
                "identidad": {k: v for k, v in ref.snapshot.items() if k not in {"correo_electronico", "numero_celular", "fecha_nacimiento"}},
                "validacion": "SIMULADA",
            }
        )
    conditions = payload.model_dump(mode="json", exclude={"revision", "fiadores"})
    conditions["id_producto_credito"] = policy.producto_id
    return {
        "cliente": client,
        "condiciones": conditions,
        "fiadores": fiadores,
        # Conservar la política completa hace reproducible una versión antigua.
        "politica": policy.model_dump(mode="json"),
        "calendario": calendar(
            payload.monto_solicitado,
            policy.tea,
            payload.plazo_meses,
            payload.fecha_base,
            policy.dias_por_periodo,
        ),
    }


def locked_application(db, identifier: str):
    row = db.scalar(
        select(Application).where(Application.id == identifier).with_for_update()
    )
    if not row:
        raise HTTPException(404, "Solicitud no encontrada.")
    return row


def current_version(db, application):
    return db.scalar(
        select(Version).where(
            Version.application_id == application.id,
            Version.number == application.current_version,
        )
    )


def check_revision(application, revision):
    if revision != application.revision:
        raise HTTPException(
            409, "La solicitud cambió en otra sesión. Recarga antes de continuar."
        )


def event(db, application, user, action: str, before, correlation: str):
    """Historial append-only desde la API; no existe endpoint de edición/borrado."""
    application.updated = now()
    identifier, instant = str(uuid4()), now()
    db.add(
        Event(
            id=identifier,
            date=instant,
            application_id=application.id,
            version=application.current_version,
            revision=application.revision,
            actor=user.username,
            action=action,
            before=before,
            after=application.state,
            correlation=correlation,
        )
    )

    enqueue(db, identifier, {"idEvento": identifier, "idOperacion": db.info.get("operation") or identifier,
                            "idCorrelacion": correlation, "tipo": action,
                            "actor": user.username, "idSolicitud": application.id,
                            "versionSolicitud": application.current_version,
                            "estadoAnterior": before, "estadoNuevo": application.state,
                            "fecha": instant.isoformat() + "Z"})


def iso(value):
    return value.isoformat(timespec="seconds") + "Z"


def summary(db, application, version=None):
    version = version or current_version(db, application)
    data = version.snapshot
    client = data["cliente"]
    return {
        "id": application.id,
        "codigo": application.code,
        "estado": application.state,
        "version": application.current_version,
        "revision": application.revision,
        "cliente_nombre": " ".join(
            [client["nombres"], client["apellido_paterno"], client["apellido_materno"]]
        ),
        "documento": client["numero_documento"],
        "monto": data["condiciones"]["monto_solicitado"],
        "moneda": data["condiciones"]["moneda"],
        "plazo": data["condiciones"]["plazo_meses"],
        "actualizado": iso(application.updated),
    }


def detail(db, application):
    # flush hace visibles los eventos y snapshots de la misma transacción.
    db.flush()
    data = summary(db, application)
    data["versiones"] = [
        {"numero": v.number, "congelada": v.frozen, "expediente": v.snapshot}
        for v in db.scalars(
            select(Version)
            .where(Version.application_id == application.id)
            .order_by(Version.number)
        )
    ]
    data["eventos"] = [
        {
            "accion": e.action,
            "actor": e.actor,
            "version": e.version,
            "estado_anterior": e.before,
            "estado_nuevo": e.after,
            "fecha": iso(e.date),
            "correlacion": e.correlation,
        }
        for e in db.scalars(
            select(Event)
            .where(Event.application_id == application.id)
            # MySQL DATETIME de v1 conserva segundos; el UUID no ordena hechos.
            .order_by(Event.version, Event.revision, Event.date, Event.id)
        )
    ]
    data["resultados"] = [
        {
            "version": o.version,
            "decision": o.decision,
            "observaciones": o.observations,
            "fecha": iso(o.date),
        }
        for o in db.scalars(
            select(Outcome)
            .where(Outcome.application_id == application.id)
            .order_by(Outcome.date)
        )
    ]
    data["envios"] = [
        {
            "version": d.version,
            "id_operacion": d.operation,
            "acuse": d.receipt,
            "estado_transporte": d.status,
            "id_evaluacion": d.evaluation_id,
            "ronda": d.round,
            "fecha": iso(d.date),
        }
        for d in db.scalars(
            select(Delivery)
            .where(Delivery.application_id == application.id)
            .order_by(Delivery.date)
        )
    ]
    return data


def projected_detail(db, application, user):
    """Minimiza también versiones históricas, fiadores y exportaciones."""
    result = detail(db, application)
    for version in result["versiones"]:
        snapshot = deepcopy(version["expediente"])
        for identity in [snapshot["cliente"], *[f.get("identidad", {}) for f in snapshot.get("fiadores", [])]]:
            for key in ["correo_electronico", "numero_celular", "fecha_nacimiento"]:
                identity.pop(key, None)
        version["expediente"] = snapshot
    return result


def read_application(db, identifier):
    row = db.get(Application, identifier)
    if row is None:
        raise HTTPException(404, "Solicitud no encontrada.")
    return row
