from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # COREDB se alcanza a través del Bus de Servicios (fase 2), nunca directo.
    core_base_url: str = "http://localhost:8018/bus/coredb"
    # Credencial de este módulo ante el Bus (X-Bus-Token). Sin valor por omisión.
    bus_token: str = ""
    core_timeout_seconds: float = 5.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
