"""Tablas de la base propia de CAPTACION.

Guardan el expediente de captación: quién pidió, qué consintió, cómo se verificó su
identidad, qué dijeron las centrales y si quedó habilitado. Del cliente solo se guarda
el `cod_cliente` que genera COREDB: el maestro de clientes vive en la base integrada.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

# En MySQL, DATETIME sin fracción redondea al segundo: dos registros del mismo segundo
# empatan y el último resultado de una validación podría no ser el más reciente.
Instante = DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql")

from CAPTACION.database import Base


class Solicitante(Base):
    __tablename__ = "cap_solicitante"
    __table_args__ = (UniqueConstraint("tipo_documento", "numero_documento", name="uk_cap_solicitante_doc"),)

    id_solicitante: Mapped[str] = mapped_column(String(36), primary_key=True)
    tipo_documento: Mapped[str] = mapped_column(String(10))
    numero_documento: Mapped[str] = mapped_column(String(12))
    nombres: Mapped[str] = mapped_column(String(100))
    apellido_paterno: Mapped[str] = mapped_column(String(100))
    apellido_materno: Mapped[str | None] = mapped_column(String(100), nullable=True)
    celular: Mapped[str] = mapped_column(String(9))
    correo: Mapped[str] = mapped_column(String(150))
    # Lo genera COREDB al registrar al cliente (CLI y nueve dígitos).
    cod_cliente: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    creado_por: Mapped[str] = mapped_column(String(40))
    creado_en: Mapped[datetime] = mapped_column(Instante)


class Caso(Base):
    __tablename__ = "cap_caso"
    __table_args__ = (Index("ix_cap_caso_estado", "estado"),)

    id_caso: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_solicitante: Mapped[str] = mapped_column(ForeignKey("cap_solicitante.id_solicitante"), index=True)
    canal: Mapped[str] = mapped_column(String(10))
    id_agencia: Mapped[str | None] = mapped_column(String(10), nullable=True)
    producto_interes: Mapped[str | None] = mapped_column(String(60), nullable=True)
    estado: Mapped[str] = mapped_column(String(15), default="INICIADO")
    # Observación puesta a mano por el asesor; mientras exista el caso no avanza.
    observacion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    motivo_cierre: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Resultado de la habilitación, la referencia que consulta Solicitud de Crédito.
    cod_cliente: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    cliente_nuevo: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    id_verificacion_captacion: Mapped[str | None] = mapped_column(String(36), nullable=True)
    estado_cliente: Mapped[str | None] = mapped_column(String(15), nullable=True)
    fecha_verificacion: Mapped[date | None] = mapped_column(Date, nullable=True)
    vigente_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    creado_por: Mapped[str] = mapped_column(String(40))
    creado_en: Mapped[datetime] = mapped_column(Instante)
    cerrado_en: Mapped[datetime | None] = mapped_column(Instante, nullable=True)


class Consentimiento(Base):
    __tablename__ = "cap_consentimiento"

    id_consentimiento: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_caso: Mapped[str] = mapped_column(ForeignKey("cap_caso.id_caso"), index=True)
    tipo: Mapped[str] = mapped_column(String(20))
    aceptado: Mapped[bool] = mapped_column(Boolean)
    medio: Mapped[str] = mapped_column(String(12))
    version: Mapped[str | None] = mapped_column(String(10), nullable=True)
    registrado_por: Mapped[str] = mapped_column(String(40))
    fecha: Mapped[datetime] = mapped_column(Instante)


class CodigoOtp(Base):
    __tablename__ = "cap_otp"

    id_otp: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_caso: Mapped[str] = mapped_column(ForeignKey("cap_caso.id_caso"), index=True)
    canal: Mapped[str] = mapped_column(String(5))  # SMS o EMAIL
    destino: Mapped[str] = mapped_column(String(150))
    codigo_hmac: Mapped[str] = mapped_column(String(64))
    intentos_fallidos: Mapped[int] = mapped_column(Integer, default=0)
    estado: Mapped[str] = mapped_column(String(10), default="PENDIENTE")
    creado_en: Mapped[datetime] = mapped_column(Instante)
    expira_en: Mapped[datetime] = mapped_column(Instante)


class Validacion(Base):
    __tablename__ = "cap_validacion"

    id_validacion: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_caso: Mapped[str] = mapped_column(ForeignKey("cap_caso.id_caso"), index=True)
    # RENIEC, LISTAS_NEGRAS, PEP, BIOMETRIA, CELULAR o CORREO.
    tipo: Mapped[str] = mapped_column(String(15))
    resultado: Mapped[str] = mapped_column(String(10))  # APROBADO, OBSERVADO o RECHAZADO
    proveedor: Mapped[str] = mapped_column(String(40))
    detalle: Mapped[str | None] = mapped_column(String(200), nullable=True)
    registrado_por: Mapped[str] = mapped_column(String(40))
    fecha: Mapped[datetime] = mapped_column(Instante)


class ConsultaRiesgo(Base):
    __tablename__ = "cap_consulta_riesgo"

    id_consulta: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_caso: Mapped[str] = mapped_column(ForeignKey("cap_caso.id_caso"), index=True)
    central: Mapped[str] = mapped_column(String(10))
    calificacion: Mapped[str] = mapped_column(String(12))
    deuda_total: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    entidades: Mapped[int] = mapped_column(Integer)
    dias_mora: Mapped[int] = mapped_column(Integer)
    fuente: Mapped[str] = mapped_column(String(12))  # SIMULADO o MANUAL
    registrado_por: Mapped[str] = mapped_column(String(40))
    fecha: Mapped[datetime] = mapped_column(Instante)


class PerfilRiesgo(Base):
    __tablename__ = "cap_perfil_riesgo"

    id_perfil: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_caso: Mapped[str] = mapped_column(ForeignKey("cap_caso.id_caso"), index=True)
    puntaje: Mapped[int] = mapped_column(Integer)
    calificacion: Mapped[str] = mapped_column(String(10))  # BAJO, MEDIO, ALTO o MUY_ALTO
    observacion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    fecha: Mapped[datetime] = mapped_column(Instante)


class Evento(Base):
    """Bitácora del módulo: cada acción sobre un expediente, con su actor y su correlación."""

    __tablename__ = "cap_evento"

    id_evento: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_caso: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    accion: Mapped[str] = mapped_column(String(40))
    actor: Mapped[str] = mapped_column(String(40))
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detalle: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fecha: Mapped[datetime] = mapped_column(Instante)
