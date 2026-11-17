"""Configuración aislada: nunca reutiliza los secretos publicados del CORE."""
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database: str
    secret: str
    token_minutes: int = 15
    lock_seconds: int = 900

    @classmethod
    def from_env(cls):
        secret = os.environ.get('SEGURIDAD_SECRET_KEY', '')
        if len(secret) < 32 or secret.startswith('change_me'):
            raise RuntimeError('Defina SEGURIDAD_SECRET_KEY aleatoria de al menos 32 caracteres')
        path = os.environ.get('SEGURIDAD_DB', str(Path(__file__).parent / 'runtime' / 'seguridad.sqlite3'))
        return cls(path, secret)
