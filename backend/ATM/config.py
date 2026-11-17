from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # TARJETAS y CUENTAS se alcanzan a través del Bus de Servicios, nunca directo.
    # URL base del Bus (no de COREDB): el ATM llama a TARJETAS y CUENTAS por /bus/tarjetas/... y /bus/cuentas/...
    bus_base_url: str = "http://localhost:8018/bus"
    # Credencial de este módulo ante el Bus (X-Bus-Token). Sin valor por omisión.
    bus_token: str = ""
    # Timeout para llamadas al Bus
    core_timeout_seconds: float = 5.0
    # Identificador del cajero
    atm_id: str = "ATM-AQP-001"
    # Modo de pruebas (para simular fallos de dispensador, etc.)
    pruebas: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()