"""Configuración de SOL. Sin base propia: todo llega por el Bus de Servicios.

COREDB guarda el borrador y la bitácora, CAPTACION da las referencias de clientes
(CR-INT-01) y EVALUACION recibe el expediente (CR-INT-02) y devuelve el resultado
(CR-INT-03). Ningún secreto ni límite comercial vive en la UI.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent

# Lo que cada token de SOL abre; deben ser distintos entre sí.
TOKENS = ("bus_token", "coredb_secreto", "cap_token", "eva_token", "callback_token")


@dataclass(frozen=True)
class Settings:
    bus_url: str
    bus_token: str
    coredb_usuario: str
    coredb_secreto: str
    cap_token: str
    eva_token: str
    callback_token: str
    policy_path: Path = ROOT / "config" / "politica_demo.json"
    http_timeout: float = 3.0
    max_retries: int = 1
    # Ventana en la que se recuerda una sesión validada en COREDB (/auth/me).
    session_cache_seconds: float = 30.0

    @property
    def coredb_url(self) -> str:
        return self.bus_url + "/coredb"

    @property
    def cap_url(self) -> str:
        return self.bus_url + "/captacion"

    @property
    def eva_url(self) -> str:
        return self.bus_url + "/evaluacion"

    def validate(self):
        try:
            parsed = urlparse(self.bus_url)
            valid = (parsed.scheme in {"http", "https"} and parsed.hostname and parsed.username is None
                     and parsed.password is None and not parsed.query and not parsed.fragment
                     and not self.bus_url.endswith("/") and not any(c.isspace() for c in self.bus_url))
            parsed.port  # También rechaza puertos inválidos.
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("Configura SOL_BUS_URL: URL HTTP del Bus, sin credenciales, consulta ni barra final.")
        if not self.coredb_usuario or any(c.isspace() for c in self.coredb_usuario):
            raise ValueError("Configura SOL_COREDB_USUARIO (el usuario de servicio de SOL en COREDB).")
        valores = [getattr(self, nombre) for nombre in TOKENS]
        for nombre, valor in zip(TOKENS, valores):
            if not isinstance(valor, str) or len(valor) < 32 or any(c.isspace() for c in valor):
                raise ValueError(f"Configura SOL_{nombre.upper()} con al menos 32 caracteres sin espacios.")
        if len(set(valores)) != len(valores):
            raise ValueError("Los tokens de SOL deben ser distintos entre sí.")
        if not 0 < self.http_timeout <= 10 or not 0 <= self.max_retries <= 2:
            raise ValueError("El timeout va de 0 a 10 s y se permiten como máximo dos reintentos.")

    @classmethod
    def from_env(cls):
        return cls(
            bus_url=os.getenv("SOL_BUS_URL", "").strip(),
            bus_token=os.getenv("SOL_BUS_TOKEN", "").strip(),
            coredb_usuario=os.getenv("SOL_COREDB_USUARIO", "svc-sol").strip(),
            coredb_secreto=os.getenv("SOL_COREDB_SECRETO", "").strip(),
            cap_token=os.getenv("SOL_CAP_TOKEN", "").strip(),
            eva_token=os.getenv("SOL_EVA_TOKEN", "").strip(),
            callback_token=os.getenv("SOL_EVA_CALLBACK_TOKEN", "").strip(),
            policy_path=Path(os.getenv("SOL_POLICY_FILE", str(ROOT / "config" / "politica_demo.json"))),
            http_timeout=float(os.getenv("SOL_HTTP_TIMEOUT_SECONDS", "3")),
            max_retries=int(os.getenv("SOL_HTTP_MAX_RETRIES", "1")),
        )
