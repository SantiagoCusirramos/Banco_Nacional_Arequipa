"""Configuración de CAPTACION, leída del entorno. Ninguna clave tiene valor por omisión.

Sin pydantic-settings a propósito: así el módulo carga también en la imagen de SOL, donde
corre su prueba de contrato (tests/test_contrato_sol.py).
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.engine import URL


def _texto(nombre: str, defecto: str = "") -> str:
    return os.environ.get(nombre, defecto)


def _entero(nombre: str, defecto: int) -> int:
    return int(os.environ.get(nombre, defecto))


def _logico(nombre: str) -> bool:
    return os.environ.get(nombre, "").strip().lower() in {"1", "true", "si", "sí", "yes"}


@dataclass
class Settings:
    # COREDB, la única entrada a la base integrada (clientes).
    core_base_url: str = field(default_factory=lambda: _texto("CORE_BASE_URL", "http://localhost:8012"))
    core_timeout_seconds: float = field(default_factory=lambda: float(_texto("CORE_TIMEOUT_SECONDS", "5")))
    # Usuario de servicio con el que CAPTACION registra clientes en COREDB. Lo crea
    # `python -m CAPTACION.manage init` con el administrador y guarda su secreto en el
    # archivo; también puede venir directo en CAP_CORE_SECRETO.
    cap_core_usuario: str = field(default_factory=lambda: _texto("CAP_CORE_USUARIO", "svc-captacion"))
    cap_core_secreto: str = field(default_factory=lambda: _texto("CAP_CORE_SECRETO"))
    cap_core_secreto_archivo: str = field(
        default_factory=lambda: _texto("CAP_CORE_SECRETO_ARCHIVO", "/datos/coredb_secreto"))

    # Base propia, en la base auxiliar (db-aux). CAP_DB_URL la reemplaza entera (pruebas).
    cap_db_url: str = field(default_factory=lambda: _texto("CAP_DB_URL"))
    cap_db_host: str = field(default_factory=lambda: _texto("CAP_DB_HOST", "127.0.0.1"))
    cap_db_port: int = field(default_factory=lambda: _entero("CAP_DB_PORT", 3306))
    cap_db_user: str = field(default_factory=lambda: _texto("CAP_DB_USER", "cap_user"))
    cap_db_password: str = field(default_factory=lambda: _texto("CAP_DB_PASSWORD"))
    cap_db_name: str = field(default_factory=lambda: _texto("CAP_DB_NAME", "bna_captacion"))

    # Token con el que Solicitud de Crédito (SOL) consulta las referencias CR-INT-01.
    cap_sol_token: str = field(default_factory=lambda: _texto("CAP_SOL_TOKEN"))
    # Clave del HMAC de los códigos OTP.
    cap_otp_clave: str = field(default_factory=lambda: _texto("CAP_OTP_CLAVE"))
    # Sin proveedor de SMS ni de correo, el código vuelve en la respuesta. Solo laboratorio.
    cap_otp_simulado: bool = field(default_factory=lambda: _logico("CAP_OTP_SIMULADO"))
    # Días que dura una habilitación antes de exigir una verificación nueva.
    cap_vigencia_dias: int = field(default_factory=lambda: _entero("CAP_VIGENCIA_DIAS", 30))
    # Versión de los términos que acepta el solicitante; COREDB la guarda en el cliente.
    cap_version_terminos: str = field(default_factory=lambda: _texto("CAP_VERSION_TERMINOS", "v1"))

    def url_base(self) -> str | URL:
        if self.cap_db_url:
            return self.cap_db_url
        return URL.create(
            "mysql+pymysql", username=self.cap_db_user, password=self.cap_db_password,
            host=self.cap_db_host, port=self.cap_db_port, database=self.cap_db_name,
            query={"charset": "utf8mb4"},
        )

    def secreto_coredb(self) -> str:
        if self.cap_core_secreto:
            return self.cap_core_secreto
        archivo = Path(self.cap_core_secreto_archivo)
        try:
            return archivo.read_text(encoding="utf-8").strip()
        except OSError:
            return ""


settings = Settings()
