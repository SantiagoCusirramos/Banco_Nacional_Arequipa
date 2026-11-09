"""Persistencia del laboratorio: referencias sintéticas, expedientes y trazabilidad.

Estas tablas mvp_sol_* viven en bna_sol_mvp. No sustituyen los maestros ni
las tablas productivas del CORE. Tecnología debe ratificar la persistencia
final antes de conectar el módulo al sistema compartido.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now():
    """La BD guarda UTC sin zona; la API lo serializa con sufijo Z."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "mvp_sol_usuario"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))
    password_hash: Mapped[str] = mapped_column(String(250))
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")


class LoginSession(Base):
    __tablename__ = "mvp_sol_sesion"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey(User.id))
    expires: Mapped[datetime] = mapped_column(DateTime)


class LoginAttempt(Base):
    __tablename__ = "mvp_sol_intento_login"
    username: Mapped[str] = mapped_column(String(60), primary_key=True)
    failures: Mapped[int] = mapped_column(Integer, default=0)
    until: Mapped[datetime] = mapped_column(DateTime, default=now)


class ClientReference(Base):
    __tablename__ = "mvp_sol_cliente_ref"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document: Mapped[str] = mapped_column(String(20), unique=True)
    # Es un snapshot de un simulador, no un segundo maestro de identidad.
    snapshot: Mapped[dict] = mapped_column(JSON)


class Application(Base):
    __tablename__ = "mvp_sol_expediente"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    client_id: Mapped[str] = mapped_column(ForeignKey(ClientReference.id))
    state: Mapped[str] = mapped_column(String(24), default="BORRADOR")
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    # Concurrencia optimista: una pestaña antigua no puede sobrescribir otra.
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated: Mapped[datetime] = mapped_column(DateTime, default=now)


class Version(Base):
    __tablename__ = "mvp_sol_version"
    __table_args__ = (
        UniqueConstraint("application_id", "number", name="uq_sol_version"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    application_id: Mapped[str] = mapped_column(ForeignKey(Application.id))
    number: Mapped[int] = mapped_column(Integer)
    frozen: Mapped[bool] = mapped_column(Boolean, default=False)
    snapshot: Mapped[dict] = mapped_column(JSON)


class Event(Base):
    __tablename__ = "mvp_sol_evento"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    application_id: Mapped[str] = mapped_column(ForeignKey(Application.id))
    version: Mapped[int] = mapped_column(Integer)
    revision: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    actor: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(50))
    before: Mapped[str | None] = mapped_column(String(24), nullable=True)
    after: Mapped[str] = mapped_column(String(24))
    correlation: Mapped[str] = mapped_column(String(100))
    date: Mapped[datetime] = mapped_column(DateTime, default=now)


class Delivery(Base):
    __tablename__ = "mvp_sol_envio"
    __table_args__ = (
        UniqueConstraint("application_id", "version", name="uq_sol_envio_version"),
    )
    operation: Mapped[str] = mapped_column(String(80), primary_key=True)
    application_id: Mapped[str] = mapped_column(ForeignKey(Application.id))
    version: Mapped[int] = mapped_column(Integer)
    fingerprint: Mapped[str] = mapped_column(String(64))
    receipt: Mapped[str] = mapped_column(String(60))
    payload: Mapped[dict] = mapped_column(JSON)
    date: Mapped[datetime] = mapped_column(DateTime, default=now)
    # Estados técnicos del transporte; no son nuevos estados de crédito.
    status: Mapped[str] = mapped_column(String(24), default="PENDIENTE", server_default="CONFIRMADO")
    mode: Mapped[str] = mapped_column(String(12), default="SIMULADO", server_default="SIMULADO")
    evaluation_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    round: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_attempt: Mapped[datetime] = mapped_column(DateTime, default=now, server_default="2000-01-01 00:00:00")
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(String(80), nullable=True)


class Outcome(Base):
    __tablename__ = "mvp_sol_resultado"
    operation: Mapped[str] = mapped_column(String(80), primary_key=True)
    application_id: Mapped[str] = mapped_column(ForeignKey(Application.id))
    version: Mapped[int] = mapped_column(Integer)
    decision: Mapped[str] = mapped_column(String(20))
    observations: Mapped[str] = mapped_column(Text)
    fingerprint: Mapped[str] = mapped_column(String(64))
    date: Mapped[datetime] = mapped_column(DateTime, default=now)
    evaluation_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    round: Mapped[int | None] = mapped_column(Integer, nullable=True)


class SecurityEvent(Base):
    """Eventos de acceso separados del historial de expedientes."""
    __tablename__ = "mvp_sol_seguridad_evento"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(50))
    correlation: Mapped[str] = mapped_column(String(100))
    date: Mapped[datetime] = mapped_column(DateTime, default=now)


class AuditOutbox(Base):
    """Se confirma junto al hecho de negocio; un reinicio no pierde pendientes."""
    __tablename__ = "mvp_sol_auditoria_pendiente"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mode: Mapped[str] = mapped_column(String(12))
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(24), default="PENDIENTE")
    receipt: Mapped[str | None] = mapped_column(String(80), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_attempt: Mapped[datetime] = mapped_column(DateTime, default=now)
    last_error: Mapped[str | None] = mapped_column(String(80), nullable=True)
    date: Mapped[datetime] = mapped_column(DateTime, default=now)
