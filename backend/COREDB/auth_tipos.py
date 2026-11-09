"""Quién actúa en una petición. Aparte de auth.py para que permisos.py no dependa
de la base ni de FastAPI."""

import uuid
from dataclasses import dataclass

# Origen de un cambio de estado de tarjeta según el módulo del usuario de servicio
# (tarjetas.origen_cambio); un módulo sin fila propia registra SISTEMA.
ORIGEN_POR_MODULO = {"CLIENTES": "MODULO_CLIENTES"}


@dataclass(frozen=True)
class Actor:
    id_usuario: uuid.UUID
    usuario: str
    rol: str
    modulo: str | None = None

    @property
    def es_servicio(self) -> bool:
        return self.rol == "SERVICIO"

    @property
    def clave_permisos(self) -> str:
        return f"SERVICIO:{self.modulo}" if self.es_servicio else self.rol

    @property
    def origen(self) -> str:
        """Origen de un cambio de estado de tarjeta: lo deriva el token, no la petición."""
        if self.es_servicio:
            return ORIGEN_POR_MODULO.get(self.modulo or "", "SISTEMA")
        return "OPERADOR"
