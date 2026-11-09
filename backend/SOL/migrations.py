"""Migración incremental v1 -> v2, exclusiva de las tablas mvp_sol_*.

No borra datos. MySQL hace commit implícito del DDL; cada columna se verifica
antes de crearla para poder reanudar un corte. Respaldar antes de ejecutar.
"""
from sqlalchemy import inspect, text
from .models import Base

ADDITIONS = {
    "mvp_sol_evento": {"revision": "INTEGER NOT NULL DEFAULT 0"},
    "mvp_sol_usuario": {"active": "BOOLEAN NOT NULL DEFAULT 1"},
    "mvp_sol_envio": {
        "status": "VARCHAR(24) NOT NULL DEFAULT 'CONFIRMADO'",
        "mode": "VARCHAR(12) NOT NULL DEFAULT 'SIMULADO'",
        "evaluation_id": "VARCHAR(80) NULL", "round": "INTEGER NULL",
        "lease_until": "DATETIME NULL",
        "next_attempt": "DATETIME NOT NULL DEFAULT '2000-01-01 00:00:00'",
        "attempts": "INTEGER NOT NULL DEFAULT 0", "last_error": "VARCHAR(80) NULL",
    },
    "mvp_sol_resultado": {"evaluation_id": "VARCHAR(80) NULL", "round": "INTEGER NULL"},
}


def migrate(engine):
    Base.metadata.create_all(engine)  # Solo crea tablas SOL que todavía no existan.
    for table, definitions in ADDITIONS.items():
        columns = {c["name"] for c in inspect(engine).get_columns(table)}
        for column, definition in definitions.items():
            if column not in columns:
                with engine.begin() as connection:
                    connection.execute(text(f'ALTER TABLE `{table}` ADD COLUMN `{column}` {definition}'))
