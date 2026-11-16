"""Configuración de Desembolso, leída del entorno. El secreto no tiene valor por omisión."""
from __future__ import annotations

import os
from dataclasses import dataclass

LONGITUD_MINIMA_SECRETO = 32


@dataclass(frozen=True)
class Config:
    # Secreto del usuario de servicio de COREDB (svc-desembolso). Con él Desembolso lee las
    # aprobaciones (CR-INT-04) y las cuentas del titular, y comprueba que COREDB responde.
    servicio_secreto: str
    servicio_usuario: str = "svc-desembolso"
    coredb_url: str = "http://127.0.0.1:8012"
    timeout_seg: float = 5.0
    sesion_cache_seg: float = 30.0

    @classmethod
    def desde_entorno(cls) -> "Config":
        config = cls(
            servicio_secreto=os.environ.get("DESEMBOLSO_COREDB_SECRETO", "").strip(),
            servicio_usuario=os.environ.get("DESEMBOLSO_COREDB_USUARIO", "svc-desembolso").strip(),
            coredb_url=os.environ.get("COREDB_URL", "http://127.0.0.1:8012").strip().rstrip("/"),
            timeout_seg=float(os.environ.get("DESEMBOLSO_TIMEOUT_SEG", "5")),
            sesion_cache_seg=float(os.environ.get("DESEMBOLSO_SESION_CACHE_SEG", "30")),
        )
        config.validar()
        return config

    def validar(self) -> None:
        # Los mensajes nunca repiten el valor.
        if len(self.servicio_secreto) < LONGITUD_MINIMA_SECRETO:
            raise RuntimeError(f"DESEMBOLSO_COREDB_SECRETO debe tener al menos {LONGITUD_MINIMA_SECRETO} caracteres.")
        if not self.servicio_usuario:
            raise RuntimeError("Falta DESEMBOLSO_COREDB_USUARIO.")
