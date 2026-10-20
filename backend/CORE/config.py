"""Configuración del módulo CORE cargada desde variables de entorno (.env)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "development"
    app_debug: bool = True

    db_host: str = "localhost"
    db_port: int = 3306
    # Los scripts de Infraestructura - BD/Trabajo_hecho/BD crean la BD `bna`.
    db_name: str = "bna"
    db_user: str = "bna_user"
    db_password: str = ""

    secret_key: str = "change_me_super_secret_key_32_chars_minimum"
    algorithm: str = "HS256"

    @property
    def database_url(self) -> str:
        password = self.db_password or ""
        return (
            f"mysql+pymysql://{self.db_user}:{password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
