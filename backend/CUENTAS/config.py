from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    core_base_url: str = "http://localhost:8012"
    core_timeout_seconds: float = 5.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
