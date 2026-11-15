"""Migración v1, rollback y bloqueo real; solo en MySQL efímero Compose E06.

Ejecutar dentro del servicio sol con worker 0 y documentación montada ro.
No usa ni borra bases institucionales; crea una base scratch sin DROP.
"""
import json
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from SOL.database import make_database
from SOL.migrations import ADDITIONS, migrate
from SOL.settings import Settings


def main():
    settings = Settings.from_env()
    url = make_url(settings.database_url)
    assert url.host == "mysql" and url.database == "bna_sol_mvp_e06"
    database = "bna_sol_mvp_e06migration"
    admin = create_engine(url._replace(database=None))
    with admin.begin() as c:
        c.execute(text("CREATE DATABASE IF NOT EXISTS bna_sol_mvp_e06migration CHARACTER SET utf8mb4"))
    admin.dispose()
    from dataclasses import replace
    engine, _ = make_database(replace(settings, database_url=url.set(database=database).render_as_string(hide_password=False)), for_maintenance=True)
    assert not inspect(engine).get_table_names(), "Requiere scratch nueva; no sobrescribir datos de otro ensayo"
    checks = []
    with engine.begin() as c:
        c.execute(text("CREATE TABLE mvp_sol_usuario (id VARCHAR(36) PRIMARY KEY, username VARCHAR(60), name VARCHAR(100), role VARCHAR(20), password_hash VARCHAR(250))"))
        c.execute(text("INSERT INTO mvp_sol_usuario VALUES ('original', 'sintetico', 'Prueba', 'ASESOR', 'marcador-no-credencial')"))
    migrate(engine)
    migrate(engine)
    with engine.connect() as c:
        assert c.execute(text("SELECT password_hash, active FROM mvp_sol_usuario")).first() == ("marcador-no-credencial", 1)
        version = c.scalar(text("SELECT VERSION()"))
        assert c.scalar(text("SELECT @@transaction_isolation")) == "READ-COMMITTED"
    checks += ["migracion_v1_preserva_registro", "migracion_reentrante", "read_committed"]
    for table, additions in ADDITIONS.items():
        assert set(additions).issubset({c["name"] for c in inspect(engine).get_columns(table)})
    checks.append("columnas_incrementales_presentes")
    with engine.connect() as c:
        c.execute(text("UPDATE mvp_sol_usuario SET name='NO-PERSISTIR' WHERE id='original'"))
        c.rollback()
        assert c.scalar(text("SELECT name FROM mvp_sol_usuario WHERE id='original'")) == "Prueba"
    checks.append("rollback_efectivo")
    with engine.connect() as one, engine.connect() as two:
        one.execute(text("SELECT id FROM mvp_sol_usuario WHERE id='original' FOR UPDATE"))
        try:
            two.execute(text("SELECT id FROM mvp_sol_usuario WHERE id='original' FOR UPDATE NOWAIT"))
        except OperationalError as exc:
            assert exc.orig.args[0] == 3572  # ER_LOCK_NOWAIT
            two.rollback()
        else:
            raise AssertionError("El segundo proceso adquirió un lock incompatible")
        one.rollback()
        assert two.scalar(text("SELECT id FROM mvp_sol_usuario WHERE id='original' FOR UPDATE NOWAIT")) == "original"
        two.rollback()
    checks += ["for_update_exclusion_dos_conexiones", "lock_liberado_tras_rollback"]
    print(json.dumps({"mysql": version, "checks": len(checks), "resultados": checks}, ensure_ascii=False))
    engine.dispose()


if __name__ == "__main__":
    main()
