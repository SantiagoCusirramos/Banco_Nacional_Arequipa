"""Dos tablas: ciudadanos y plantillas biométricas (solo RENIEC guarda biometría)."""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Ciudadano(Base):
    __tablename__ = "ciudadanos"
    numero_documento: Mapped[str] = mapped_column(String(8), primary_key=True)  # DNI
    nombres: Mapped[str] = mapped_column(String(100))
    apellidos: Mapped[str] = mapped_column(String(100))
    fecha_nacimiento: Mapped[date] = mapped_column(Date)
    genero: Mapped[str] = mapped_column(String(1))  # M | F


class PlantillaBiometrica(Base):
    __tablename__ = "plantillas_biometricas"
    __table_args__ = (UniqueConstraint("numero_documento", "tipo_biometria", name="uq_plantilla_dni_tipo"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    numero_documento: Mapped[str] = mapped_column(ForeignKey("ciudadanos.numero_documento", ondelete="CASCADE"))
    tipo_biometria: Mapped[str] = mapped_column(String(10))  # FACIAL | HUELLA
    formato: Mapped[str] = mapped_column(String(30))  # ARCFACE_EMBEDDING | ISO_19794_2_2005
    plantilla: Mapped[str] = mapped_column(Text)  # FACIAL: lista JSON de 512 números; HUELLA: Base64
    algoritmo: Mapped[str] = mapped_column(String(80))
    version: Mapped[str] = mapped_column(String(20))
    fecha_registro: Mapped[datetime] = mapped_column(DateTime)
