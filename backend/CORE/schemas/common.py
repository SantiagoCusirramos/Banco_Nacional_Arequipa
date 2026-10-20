"""Schemas Pydantic v2 compartidos del módulo CORE."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class CoreModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorBody(CoreModel):
    code: str
    message: str
    details: dict[str, Any] = {}


class ErrorRespuesta(CoreModel):
    error: ErrorBody
    correlation_id: str | None = None


class PaginacionParams(CoreModel):
    limite: int = 50
    offset: int = 0


class ActorParams(CoreModel):
    actor: str = "sistema"
    correlation_id: str | None = None
