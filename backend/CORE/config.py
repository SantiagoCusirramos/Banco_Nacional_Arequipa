
"""Configuración del módulo CORE cargada desde variables de entorno (.env)."""

from functools import lru_cache

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

LONGITUD_MINIMA_SECRET_KEY = 32
MARCADOR_DE_EJEMPLO = "change_me"  # valor de .env.example
AYUDA_SECRET_KEY = (
    "Copie backend/.env.example a backend/.env y defina SECRET_KEY con al menos "
    f"{LONGITUD_MINIMA_SECRET_KEY} caracteres propios. Genérela con: "
    'python -c "import secrets; print(secrets.token_urlsafe(48))"'
)


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


def verificar_configuracion() -> None:
    """Detiene el arranque si falta configuración. El error nunca repite los valores."""
    try:
        clave = get_settings().secret_key
    except ValidationError as exc:
        campos = ", ".join(str(error["loc"][0]).upper() for error in exc.errors())
        raise RuntimeError(f"Configuración inválida o incompleta: {campos}. {AYUDA_SECRET_KEY}") from None
    if len(clave) < LONGITUD_MINIMA_SECRET_KEY or clave.startswith(MARCADOR_DE_EJEMPLO):
        raise RuntimeError(f"SECRET_KEY no es válida. {AYUDA_SECRET_KEY}")

