"""Entregas y outbox persistentes con reserva temporal y confirmación explícita.

La transacción local termina antes del HTTP. Si el proceso cae, vence la reserva
(30 s) y se consulta la operación remota antes de volver a enviar. CR-INT-10 es
entrega al menos una vez: Seguridad DEBE deduplicar por idEvento.
"""
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4
from sqlalchemy import delete, or_, select
from .integrations import IntegrationError
from .models import Application, AuditOutbox, Delivery, LoginAttempt, LoginSession, SecurityEvent, Version, now
from .observability import log


def enqueue(db, identifier, payload):
    mode = db.info.get("integration_mode", "SIMULADO")
    db.add(AuditOutbox(id=identifier, mode=mode, payload={**payload, "simulado": mode == "SIMULADO"}))


def security_event(db, actor, action, correlation, subject=None):
    identifier, instant = str(uuid4()), now()
    db.add(SecurityEvent(id=identifier, actor=actor, action=action, correlation=correlation, date=instant))
    enqueue(db, identifier, {"idEvento": identifier, "idOperacion": identifier,
                            "idCorrelacion": correlation, "tipo": action,
                            "actor": actor, "sujeto": subject,
                            "fecha": instant.isoformat() + "Z"})


def process_delivery(factory, integrations, operation):
    with factory.begin() as db:
        row = db.scalar(select(Delivery).where(Delivery.operation == operation).with_for_update())
        if not row or row.mode != integrations.settings.mode:
            return False
        if row.status == "CONFIRMADO":
            return True
        if row.status == "ERROR_CONTRATO" or row.lease_until and row.lease_until > now():
            return False
        row.lease_until = now() + timedelta(seconds=30)
        row.attempts += 1
        envelope = row.payload
    try:
        receipt = integrations.deliver(envelope)
    except IntegrationError as exc:
        with factory.begin() as db:
            row = db.get(Delivery, operation)
            row.status = "ERROR_CONTRATO" if exc.permanent else "PENDIENTE"
            row.last_error, row.lease_until = exc.code, None
            row.next_attempt = now() + timedelta(seconds=min(300, 5 * 2**min(row.attempts, 6)))
        log("ENVIO_PENDIENTE", envelope["idCorrelacion"], operation, causa=exc.code)
        return False
    with factory.begin() as db:
        row = db.scalar(select(Delivery).where(Delivery.operation == operation).with_for_update())
        if row.status == "CONFIRMADO":
            return True
        application = db.scalar(select(Application).where(Application.id == row.application_id).with_for_update())
        # Reserva congelada; otras operaciones no pueden modificarla durante HTTP.
        if application.current_version != row.version or application.state != "BORRADOR":
            row.status, row.last_error, row.lease_until = "ERROR_CONTRATO", "VERSION_INCOMPATIBLE", None
            return False
        row.receipt, row.evaluation_id, row.round = receipt["acuse"], receipt["idEvaluacion"], receipt["ronda"]
        row.status, row.last_error, row.lease_until = "CONFIRMADO", None, None
        application.state = "EN_EVALUACION"
        application.revision += 1
        from .service import event
        db.info["integration_mode"] = row.mode
        db.info["operation"] = operation
        event(db, application, SimpleNamespace(username=envelope["actorEnvio"]),
              "ENVIAR_CR_INT_02_SIMULADO" if row.mode == "SIMULADO" else "ENVIAR_CR_INT_02",
              "BORRADOR", envelope["idCorrelacion"])
    log("ENVIO_CONFIRMADO", envelope["idCorrelacion"], operation, simulado=row.mode == "SIMULADO")
    return True


def process_audit(factory, integrations, identifier):
    with factory.begin() as db:
        row = db.scalar(select(AuditOutbox).where(AuditOutbox.id == identifier).with_for_update())
        if not row or row.mode != integrations.settings.mode or row.status != "PENDIENTE":
            return False
        if row.lease_until and row.lease_until > now():
            return False
        row.lease_until = now() + timedelta(seconds=30)
        row.attempts += 1
        payload = row.payload
    try:
        receipt = integrations.audit(payload)
    except IntegrationError as exc:
        with factory.begin() as db:
            row = db.get(AuditOutbox, identifier)
            row.last_error, row.lease_until = exc.code, None
            row.next_attempt = now() + timedelta(seconds=min(300, 5 * 2**min(row.attempts, 6)))
            if exc.permanent:
                row.status = "ERROR_CONTRATO"
        log("AUDITORIA_PENDIENTE", payload["idCorrelacion"], payload["idEvento"], causa=exc.code)
        return False
    with factory.begin() as db:
        row = db.get(AuditOutbox, identifier)
        row.status = "SIMULADO" if integrations.settings.mode == "SIMULADO" else "CONFIRMADO"
        row.receipt, row.lease_until, row.last_error = receipt, None, None
    log("AUDITORIA_CONFIRMADA", payload["idCorrelacion"], payload["idEvento"], simulado=integrations.settings.mode == "SIMULADO")
    return True


def maintenance(factory, integrations):
    """Un lote acotado por ciclo; un error no elimina pendientes."""
    with factory.begin() as db:
        db.execute(delete(LoginAttempt).where(LoginAttempt.until <= now()))
        removed = db.execute(delete(LoginSession).where(LoginSession.expires <= now())).rowcount
        deliveries = list(db.scalars(select(Delivery.operation).where(
            Delivery.mode == integrations.settings.mode, Delivery.status == "PENDIENTE",
            Delivery.next_attempt <= now(), or_(Delivery.lease_until.is_(None), Delivery.lease_until <= now())
        ).order_by(Delivery.date).limit(10)))
        audits = list(db.scalars(select(AuditOutbox.id).where(
            AuditOutbox.mode == integrations.settings.mode, AuditOutbox.status == "PENDIENTE",
            AuditOutbox.next_attempt <= now(), or_(AuditOutbox.lease_until.is_(None), AuditOutbox.lease_until <= now())
        ).order_by(AuditOutbox.date).limit(20)))
    for key in deliveries:
        process_delivery(factory, integrations, key)
    for key in audits:
        process_audit(factory, integrations, key)
    return {"sesiones_eliminadas": removed, "envios_revisados": len(deliveries), "eventos_revisados": len(audits)}
