"""Configuración del laboratorio. Ningún secreto ni límite comercial vive en la UI."""

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL

ROOT = Path(__file__).resolve().parent
# Se utiliza un archivo propio para no interferir con el .env del CORE.
load_dotenv(ROOT.parent / ".env.sol")


@dataclass(frozen=True)
class Settings:
    """Variables operativas; las políticas editables están en politica_demo.json."""

    database_url: str
    policy_path: Path = ROOT / "config" / "politica_demo.json"
    mode: str = "SIMULADO"
    session_hours: int = 8
    bus_base_url: str = ""
    bus_token: str = ""
    callback_token: str = ""
    cap_search_path: str = ""
    cap_reference_path: str = ""
    eva_send_path: str = ""
    eva_status_path: str = ""
    audit_path: str = ""
    http_timeout: float = 0.6
    max_retries: int = 2
    request_budget: float = 2.4
    worker_seconds: float = 5

    def validate(self):
        from urllib.parse import urlparse
        if self.mode not in {"SIMULADO", "REAL"}:
            raise ValueError("SOL_INTEGRATION_MODE debe ser SIMULADO o REAL.")
        if not 0 < self.http_timeout <= 3 or not 0 < self.request_budget < 3:
            raise ValueError("El timeout debe ser <= 3 s y el presupuesto total < 3 s.")
        if not 0 <= self.max_retries <= 2 or self.worker_seconds < 0:
            raise ValueError("Se permiten como máximo dos reintentos.")
        if self.mode == "REAL":
            parsed = urlparse(self.bus_base_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError("Configura una URL del Bus válida, sin credenciales ni query.")
            if min(len(self.bus_token), len(self.callback_token)) < 32 or self.bus_token == self.callback_token:
                raise ValueError("REAL requiere dos tokens distintos de al menos 32 caracteres.")
            for path in [self.cap_search_path, self.cap_reference_path, self.eva_send_path, self.eva_status_path, self.audit_path]:
                if not path.startswith("/") or path.startswith("//") or ".." in path or "://" in path or "?" in path:
                    raise ValueError("Configura todas las rutas relativas homologadas del Bus.")
            if "{idCliente}" not in self.cap_reference_path or "{idOperacion}" not in self.eva_status_path:
                raise ValueError("Faltan {idCliente} o {idOperacion} en las rutas de consulta.")

    @classmethod
    def from_env(cls):
        database = os.getenv("SOL_DB_NAME", "bna_sol_mvp")
        if not re.fullmatch(r"bna_sol_mvp(?:_[a-zA-Z0-9]+)?", database):
            raise ValueError(
                "Usa una BD bna_sol_mvp o bna_sol_mvp_<sufijo>; no apuntes a la BD compartida bna."
            )
        url = URL.create(
            "mysql+pymysql",
            username=os.getenv("SOL_DB_USER", "root"),
            password=os.getenv("SOL_DB_PASSWORD", ""),
            host=os.getenv("SOL_DB_HOST", "127.0.0.1"),
            port=int(os.getenv("SOL_DB_PORT", "3306")),
            database=database,
            query={"charset": "utf8mb4"},
        )
        return cls(
            database_url=url.render_as_string(hide_password=False),
            policy_path=Path(
                os.getenv(
                    "SOL_POLICY_FILE", str(ROOT / "config" / "politica_demo.json")
                )
            ),
            mode=os.getenv("SOL_INTEGRATION_MODE", "SIMULADO"),
            bus_base_url=os.getenv("SOL_BUS_BASE_URL", ""),
            bus_token=os.getenv("SOL_BUS_TOKEN", ""),
            callback_token=os.getenv("SOL_EVA_CALLBACK_TOKEN", ""),
            cap_search_path=os.getenv("SOL_CAP_SEARCH_PATH", ""),
            cap_reference_path=os.getenv("SOL_CAP_REFERENCE_PATH", ""),
            eva_send_path=os.getenv("SOL_EVA_SEND_PATH", ""),
            eva_status_path=os.getenv("SOL_EVA_STATUS_PATH", ""),
            audit_path=os.getenv("SOL_AUDIT_PATH", ""),
            http_timeout=float(os.getenv("SOL_HTTP_TIMEOUT_SECONDS", "0.6")),
            max_retries=int(os.getenv("SOL_HTTP_MAX_RETRIES", "2")),
            request_budget=float(os.getenv("SOL_REQUEST_BUDGET_SECONDS", "2.4")),
            worker_seconds=float(os.getenv("SOL_WORKER_SECONDS", "5")),
        )
