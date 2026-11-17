"""Configuración de CAPTACION, leída del entorno. Ninguna clave tiene valor por omisión.

Sin pydantic-settings a propósito: así el módulo carga también en la imagen de SOL, donde
corre su prueba de contrato (tests/test_contrato_sol.py). CAPTACION no tiene base propia:
el expediente vive en la base integrada y se trabaja por COREDB.
"""

import os
from dataclasses import dataclass, field


def _texto(nombre: str, defecto: str = "") -> str:
    return os.environ.get(nombre, defecto)


def _entero(nombre: str, defecto: int) -> int:
    return int(os.environ.get(nombre, defecto))


def _logico(nombre: str) -> bool:
    return os.environ.get(nombre, "").strip().lower() in {"1", "true", "si", "sí", "yes"}


@dataclass
class Settings:
    # COREDB, la única entrada a la base integrada.
    core_base_url: str = field(default_factory=lambda: _texto("CORE_BASE_URL", "http://localhost:8012"))
    core_timeout_seconds: float = field(default_factory=lambda: float(_texto("CORE_TIMEOUT_SECONDS", "5")))
    # Usuario de servicio de CAPTACION en COREDB (módulo CLIENTES). Lo crea el arranque de
    # COREDB (coredb-init, o el contenedor de arranque en Kubernetes) con este secreto.
    cap_core_usuario: str = field(default_factory=lambda: _texto("CAP_CORE_USUARIO", "svc-captacion"))
    cap_core_secreto: str = field(default_factory=lambda: _texto("CAP_CORE_SECRETO"))

    # Token con el que Solicitud de Crédito (SOL) consulta las referencias CR-INT-01.
    cap_sol_token: str = field(default_factory=lambda: _texto("CAP_SOL_TOKEN"))
    # Clave del HMAC de los códigos OTP: COREDB solo recibe el HMAC.
    cap_otp_clave: str = field(default_factory=lambda: _texto("CAP_OTP_CLAVE"))
    # Sin proveedor de SMS ni de correo, el código vuelve en la respuesta. Solo laboratorio.
    cap_otp_simulado: bool = field(default_factory=lambda: _logico("CAP_OTP_SIMULADO"))
    # Días que dura una habilitación antes de exigir una verificación nueva (1 a 365).
    cap_vigencia_dias: int = field(default_factory=lambda: _entero("CAP_VIGENCIA_DIAS", 30))
    # Versión de los términos que acepta el solicitante; COREDB la guarda en el cliente.
    cap_version_terminos: str = field(default_factory=lambda: _texto("CAP_VERSION_TERMINOS", "v1"))


settings = Settings()
