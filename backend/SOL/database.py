"""La conexión es explícita. Un fallo MySQL nunca activa otra BD automáticamente."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def make_database(settings, for_maintenance=False):
    options = {"pool_pre_ping": True}
    # Exclusivo de las pruebas automatizadas, que inyectan Settings explícito.
    if settings.database_url.startswith("sqlite"):
        options.update(connect_args={"check_same_thread": False}, poolclass=StaticPool)
    else:
        # Los bloqueos de expediente y las lecturas posteriores ven la misma
        # revisión vigente, incluso cuando otro envío acaba de confirmarse.
        options["isolation_level"] = "READ COMMITTED"
        # El DDL puede tardar más que una consulta del canal digital.
        wait = 30 if for_maintenance else 2
        options["connect_args"] = {"connect_timeout": 2, "read_timeout": wait, "write_timeout": wait}
    engine = create_engine(settings.database_url, **options)
    return engine, sessionmaker(engine, expire_on_commit=False)
