"""Configuración de la API de la base integrada, tomada de CORE_DB_*."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).with_name(".env"),
        env_file_encoding="utf-8",
        env_prefix="CORE_DB_",
        extra="ignore",
    )

    host: str = "127.0.0.1"
    port: int = 3307
    app_user: str = "bna_app_user"
    app_password: str = ""

    @property
    def database_url(self) -> URL:
        # Sin base por defecto: cada modelo y procedimiento nombra su base.
        return URL.create(
            "mysql+pymysql",
            username=self.app_user,
            password=self.app_password,
            host=self.host,
            port=self.port,
            query={"charset": "utf8mb4"},
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
