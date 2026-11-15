"""Configuración de Evaluación, leída del entorno. Ninguna clave tiene valor por omisión."""
from __future__ import annotations

import os
from dataclasses import dataclass

# SOL exige tokens de al menos 32 caracteres en su modo REAL; aquí se pide lo mismo.
LONGITUD_MINIMA_TOKEN = 32


@dataclass(frozen=True)
class Config:
    database_url: str
    coredb_url: str = "http://127.0.0.1:8012"
    # Bearer con el que SOL entrega expedientes (CR-INT-02). Es el SOL_BUS_TOKEN de SOL.
    token_sol: str = ""
    # Base de SOL para devolverle el resultado (CR-INT-03). Vacía mientras SOL siga en modo SIMULADO.
    sol_url: str = ""
    # Bearer para el resultado: el SOL_EVA_CALLBACK_TOKEN de SOL.
    sol_token_resultados: str = ""
    vigencia_dias: int = 30
    envio_intervalo_seg: float = 5.0
    timeout_seg: float = 3.0
    sesion_cache_seg: float = 30.0

    @classmethod
    def desde_entorno(cls) -> "Config":
        url = os.environ.get("EVALUACION_DATABASE_URL", "").strip()
        if not url:
            raise RuntimeError("Falta EVALUACION_DATABASE_URL.")
        config = cls(
            database_url=url,
            coredb_url=os.environ.get("COREDB_URL", "http://127.0.0.1:8012").strip().rstrip("/"),
            token_sol=os.environ.get("EVALUACION_TOKEN_SOL", "").strip(),
            sol_url=os.environ.get("EVALUACION_SOL_URL", "").strip().rstrip("/"),
            sol_token_resultados=os.environ.get("EVALUACION_SOL_TOKEN_RESULTADOS", "").strip(),
            vigencia_dias=int(os.environ.get("EVALUACION_VIGENCIA_DIAS", "30")),
            envio_intervalo_seg=float(os.environ.get("EVALUACION_ENVIO_INTERVALO_SEG", "5")),
            timeout_seg=float(os.environ.get("EVALUACION_TIMEOUT_SEG", "3")),
            sesion_cache_seg=float(os.environ.get("EVALUACION_SESION_CACHE_SEG", "30")),
        )
        config.validar()
        return config

    def validar(self) -> None:
        if self.vigencia_dias < 1:
            raise RuntimeError("EVALUACION_VIGENCIA_DIAS debe ser 1 o más.")
        for nombre, valor in (("EVALUACION_TOKEN_SOL", self.token_sol),
                              ("EVALUACION_SOL_TOKEN_RESULTADOS", self.sol_token_resultados)):
            if valor and len(valor) < LONGITUD_MINIMA_TOKEN:
                # El mensaje nunca repite el valor.
                raise RuntimeError(f"{nombre} debe tener al menos {LONGITUD_MINIMA_TOKEN} caracteres.")
        if self.token_sol and self.token_sol == self.sol_token_resultados:
            raise RuntimeError("EVALUACION_TOKEN_SOL y EVALUACION_SOL_TOKEN_RESULTADOS deben ser distintos.")
        if self.sol_url and not self.sol_token_resultados:
            raise RuntimeError("Con EVALUACION_SOL_URL hace falta EVALUACION_SOL_TOKEN_RESULTADOS.")
