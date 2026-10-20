"""Schemas de tarjetas (VER/CREAR/BLOQUEAR_TARJETA).

Ningún schema expone el PAN ni el hash completo: solo token parcial
(BIN + últimos 4), conforme a RNF-13.
"""

from datetime import date

from CORE.schemas.common import CoreModel


class TarjetaCrear(CoreModel):
    id_cliente: str
    num_cuenta: str
    tipo_tarjeta: str = "DEBITO"
    anios_vigencia: int = 4
    es_principal: bool = True
    habilitada_atm: bool = True
    actor: str = "sistema"
    correlation_id: str | None = None


class TarjetaEstadoCambiar(CoreModel):
    estado_nuevo: str
    motivo: str
    origen: str = "BANCO"
    actor: str = "sistema"
    correlation_id: str | None = None


class TarjetaRespuesta(CoreModel):
    id_tarjeta: str
    bin: str
    ultimos4: str
    id_cliente: str
    tipo_tarjeta: str
    fecha_emision: date
    fecha_vencimiento: date
    estado: str
