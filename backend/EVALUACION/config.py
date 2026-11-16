"""Configuración de Evaluación, leída del entorno. Ninguna clave tiene valor por omisión."""
from __future__ import annotations

import os
from dataclasses import dataclass

# SOL exige tokens de al menos 32 caracteres en su modo REAL; aquí se pide lo mismo, también
# para el secreto del usuario de servicio de COREDB.
LONGITUD_MINIMA_TOKEN = 32


@dataclass(frozen=True)
class Config:
    # Secreto del usuario de servicio de COREDB (svc-evaluacion). Con él se registra el
    # expediente de SOL y se leen los resultados para CR-INT-03.
    servicio_secreto: str
    servicio_usuario: str = "svc-evaluacion"
    coredb_url: str = "http://127.0.0.1:8012"
    # Bearer con el que SOL entrega expedientes (CR-INT-02). Es el SOL_BUS_TOKEN de SOL.
    token_sol: str = ""
    # Base de SOL para devolverle el resultado (CR-INT-03). Vacía mientras SOL siga en modo SIMULADO.
    sol_url: str = ""
    # Bearer para el resultado: el SOL_EVA_CALLBACK_TOKEN de SOL.
    sol_token_resultados: str = ""
    # CR-INT-03 sin estado propio: cada ciclo reenvía los resultados de las solicitudes de los
    # últimos `envio_ventana_dias` días; SOL reconoce un reintento por su idOperacion determinista.
    envio_intervalo_seg: float = 30.0
    envio_ventana_dias: int = 7
    timeout_seg: float = 5.0
    sesion_cache_seg: float = 30.0

    @classmethod
    def desde_entorno(cls) -> "Config":
        config = cls(
            servicio_secreto=os.environ.get("EVALUACION_COREDB_SECRETO", "").strip(),
            servicio_usuario=os.environ.get("EVALUACION_COREDB_USUARIO", "svc-evaluacion").strip(),
            coredb_url=os.environ.get("COREDB_URL", "http://127.0.0.1:8012").strip().rstrip("/"),
            token_sol=os.environ.get("EVALUACION_TOKEN_SOL", "").strip(),
            sol_url=os.environ.get("EVALUACION_SOL_URL", "").strip().rstrip("/"),
            sol_token_resultados=os.environ.get("EVALUACION_SOL_TOKEN_RESULTADOS", "").strip(),
            envio_intervalo_seg=float(os.environ.get("EVALUACION_ENVIO_INTERVALO_SEG", "30")),
            envio_ventana_dias=int(os.environ.get("EVALUACION_ENVIO_VENTANA_DIAS", "7")),
            timeout_seg=float(os.environ.get("EVALUACION_TIMEOUT_SEG", "5")),
            sesion_cache_seg=float(os.environ.get("EVALUACION_SESION_CACHE_SEG", "30")),
        )
        config.validar()
        return config

    def validar(self) -> None:
        # Los mensajes nunca repiten el valor.
        if len(self.servicio_secreto) < LONGITUD_MINIMA_TOKEN:
            raise RuntimeError(f"EVALUACION_COREDB_SECRETO debe tener al menos {LONGITUD_MINIMA_TOKEN} caracteres.")
        if not self.servicio_usuario:
            raise RuntimeError("Falta EVALUACION_COREDB_USUARIO.")
        if self.envio_ventana_dias < 1:
            raise RuntimeError("EVALUACION_ENVIO_VENTANA_DIAS debe ser 1 o más.")
        for nombre, valor in (("EVALUACION_TOKEN_SOL", self.token_sol),
                              ("EVALUACION_SOL_TOKEN_RESULTADOS", self.sol_token_resultados)):
            if valor and len(valor) < LONGITUD_MINIMA_TOKEN:
                raise RuntimeError(f"{nombre} debe tener al menos {LONGITUD_MINIMA_TOKEN} caracteres.")
        if self.token_sol and self.token_sol == self.sol_token_resultados:
            raise RuntimeError("EVALUACION_TOKEN_SOL y EVALUACION_SOL_TOKEN_RESULTADOS deben ser distintos.")
        if self.sol_url and not self.sol_token_resultados:
            raise RuntimeError("Con EVALUACION_SOL_URL hace falta EVALUACION_SOL_TOKEN_RESULTADOS.")
