
"""Configuración del módulo CORE cargada desde variables de entorno (.env)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_debug: bool = True

    db_host: str = "localhost"
    db_port: int = 3306
    # Los scripts de Infraestructura - BD/Trabajo_hecho/BD crean la BD `bna`.
    db_name: str = "bna"
    db_user: str = "bna_user"
    db_password: str = ""

    # La clave se saca del .env
    secret_key: str
    algorithm: str = "HS256"
    # Vigencia del access token (variable ACCESS_TOKEN_EXPIRE_MINUTES del .env)
    access_token_expire_minutes: int = 30

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

