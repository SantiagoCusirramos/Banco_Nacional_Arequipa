"""Configuración, leída del entorno. Ningún secreto tiene valor por omisión."""
from __future__ import annotations

import os
from dataclasses import dataclass

LONGITUD_MINIMA = 32


@dataclass(frozen=True)
class Config:
    # Clave de los HMAC: el del código de un desafío y el de los sellos de la bitácora. La base
    # guarda los HMAC pero nunca ve esta clave.
    clave: str
    # Secreto del usuario de servicio de COREDB (svc-seguridad, módulo SEGURIDAD).
    servicio_secreto: str
    servicio_usuario: str = "svc-seguridad"
    # COREDB se alcanza a través del Bus de Servicios, nunca directo.
    coredb_url: str = "http://127.0.0.1:8018/bus/coredb"
    # Credencial de este módulo ante el Bus (X-Bus-Token).
    bus_token: str = ""
    timeout_seg: float = 5.0
    # Cada cuánto se sella la bitácora (0: no sella solo) y qué antigüedad mínima tiene un
    # evento para sellarlo: una transacción más lenta podría confirmar después un evento con un
    # id menor, que quedaría fuera de su tramo.
    sellado_seg: float = 60.0
    sellado_antiguedad_seg: float = 60.0

    @classmethod
    def desde_entorno(cls) -> "Config":
        config = cls(
            clave=os.environ.get("SEGURIDAD_SECRET_KEY", "").strip(),
            servicio_secreto=os.environ.get("SEGURIDAD_COREDB_SECRETO", "").strip(),
            servicio_usuario=os.environ.get("SEGURIDAD_COREDB_USUARIO", "svc-seguridad").strip(),
            coredb_url=os.environ.get("COREDB_URL", "http://127.0.0.1:8018/bus/coredb").strip().rstrip("/"),
            bus_token=os.environ.get("BUS_TOKEN", "").strip(),
            timeout_seg=float(os.environ.get("SEGURIDAD_TIMEOUT_SEG", "5")),
            sellado_seg=float(os.environ.get("SEGURIDAD_SELLADO_SEG", "60")),
            sellado_antiguedad_seg=float(os.environ.get("SEGURIDAD_SELLADO_ANTIGUEDAD_SEG", "60")),
        )
        config.validar()
        return config

    def validar(self) -> None:
        # Los mensajes nunca repiten el valor.
        if len(self.clave) < LONGITUD_MINIMA or self.clave.startswith("change_me"):
            raise RuntimeError(f"Defina SEGURIDAD_SECRET_KEY aleatoria de al menos {LONGITUD_MINIMA} caracteres.")
        if len(self.servicio_secreto) < LONGITUD_MINIMA:
            raise RuntimeError(f"SEGURIDAD_COREDB_SECRETO debe tener al menos {LONGITUD_MINIMA} caracteres.")
        if not self.servicio_usuario:
            raise RuntimeError("Falta SEGURIDAD_COREDB_USUARIO.")
