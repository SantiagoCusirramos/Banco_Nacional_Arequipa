"""Inicialización explícita de MySQL. No ejecuta el script unificado del banco."""

import argparse
import getpass
import os
import re
from sqlalchemy import create_engine, text, update
from sqlalchemy.engine import make_url
from .database import make_database
from .models import Base, Delivery, AuditOutbox, now
from .migrations import migrate
from .integrations import Integrations
from .operations import maintenance
from .policy import load_policy
from .seed import DEMO_USERS, seed
from .settings import Settings


def main():
    parser = argparse.ArgumentParser(description="Preparar el laboratorio SOL en MySQL")
    parser.add_argument("command", choices=["init", "check", "migrate", "maintain", "retry-errors"])
    args = parser.parse_args()
    settings = Settings.from_env()
    policy = load_policy(settings.policy_path)
    url = make_url(settings.database_url)
    # Impide apuntar accidentalmente a la BD `bna` del proyecto compartido.
    if not url.database or not re.fullmatch(
        r"bna_sol_mvp(?:_[a-zA-Z0-9]+)?", url.database
    ):
        raise SystemExit(
            "SOL_DB_NAME debe ser bna_sol_mvp o bna_sol_mvp_<sufijo>. No uses bna."
        )
    if args.command == "init":
        # URL.set(database=None) conserva el valor anterior en SQLAlchemy.
        # _replace sí elimina el nombre: permite conectar antes de crear la BD.
        admin = create_engine(url._replace(database=None), pool_pre_ping=True)
        with admin.begin() as connection:
            connection.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{url.database}` CHARACTER SET utf8mb4"
                )
            )
        admin.dispose()
    engine, factory = make_database(settings, for_maintenance=True)
    if args.command == "init":
        password = os.getenv("SOL_INITIAL_PASSWORD") or getpass.getpass(
            "Clave inicial para las 4 cuentas DEMO (mínimo 12 caracteres): "
        )
        if len(password) < 12:
            raise SystemExit("La clave debe contener al menos 12 caracteres.")
        migrate(engine)
        seed(factory, password)
        print("Laboratorio creado. Usuarios:", ", ".join(u[0] for u in DEMO_USERS))
        print("Las cuentas existentes conservan su clave; init no elimina datos.")
    if args.command == "migrate":
        migrate(engine)
        print("Migración SOL v2 aplicada; datos y claves conservados.")
    if args.command == "retry-errors":
        settings.validate()
        with factory.begin() as db:
            for model in [Delivery, AuditOutbox]:
                count = db.execute(update(model).where(model.mode == settings.mode, model.status == "ERROR_CONTRATO").values(status="PENDIENTE", next_attempt=now(), last_error=None, lease_until=None)).rowcount
                print(model.__tablename__, "reencolados:", count)
    if args.command == "maintain":
        settings.validate()
        integrations = Integrations(settings)
        try:
            print(maintenance(factory, integrations))
        finally:
            integrations.close()
    with engine.connect() as connection:
        print("MySQL:", connection.execute(text("SELECT VERSION()")).scalar())
        print(
            "Solicitudes guardadas:",
            connection.execute(
                text("SELECT COUNT(*) FROM mvp_sol_expediente")
            ).scalar(),
        )
    print("Política:", policy.version, "·", policy.estado_aprobacion)
    engine.dispose()


if __name__ == "__main__":
    main()
