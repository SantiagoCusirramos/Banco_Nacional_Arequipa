from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Login(Strict):
    username: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=1, max_length=128)


class Operation(Strict):
    operation_id: str = Field(min_length=8, max_length=80, pattern=r'^[a-zA-Z0-9_-]+$')
    amount: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    currency: Literal['PEN', 'USD']
    channel: Literal['ATM', 'HOME_BANKING', 'BILLETERA']
    challenge_id: str | None = None
    otp: str | None = Field(default=None, pattern=r'^\d{6}$')


class Incident(Strict):
    title: str = Field(min_length=8, max_length=200)
    priority: Literal['P1', 'P2', 'P3', 'P4']


class IncidentUpdate(Strict):
    status: Literal['EN_PROGRESO', 'RESUELTO', 'CERRADO']
    resolution: str | None = Field(default=None, min_length=8, max_length=500)
