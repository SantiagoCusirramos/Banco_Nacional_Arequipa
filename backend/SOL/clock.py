"""Fecha de negocio en Lima; los instantes de auditoría siguen guardándose UTC."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

LIMA = ZoneInfo("America/Lima")


def utc_now():
    return datetime.now(timezone.utc)


def business_today():
    # Depende del instante, nunca de la zona configurada en Windows o Linux.
    return utc_now().astimezone(LIMA).date()
