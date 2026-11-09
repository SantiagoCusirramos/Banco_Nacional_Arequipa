"""Pruebas aisladas: SQLite por defecto; MySQL solo en bna_sol_mvp_test."""

import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from SOL.app import create_app
from SOL.database import make_database
from SOL.models import Base
from SOL.seed import seed
from SOL.settings import Settings, ROOT

PASSWORD = "PruebaBNA2026!"


@pytest.fixture
def lab(tmp_path):
    policy_path = tmp_path / "politica.json"
    policy_path.write_text(
        (ROOT / "config" / "politica_demo.json").read_text(), encoding="utf-8"
    )
    database = os.getenv("SOL_TEST_DATABASE_URL", "sqlite://")
    if (
        not database.startswith("sqlite")
        and make_url(database).database != "bna_sol_mvp_test"
    ):
        pytest.fail(
            "La BD MySQL de pruebas debe llamarse exactamente bna_sol_mvp_test."
        )
    app = create_app(Settings(database, policy_path, worker_seconds=0))
    ddl_engine = app.state.engine if database.startswith("sqlite") else make_database(app.state.settings, for_maintenance=True)[0]
    Base.metadata.drop_all(ddl_engine)
    Base.metadata.create_all(ddl_engine)
    seed(app.state.factory, PASSWORD)
    with TestClient(app) as client:
        yield client, app
    Base.metadata.drop_all(ddl_engine)
    ddl_engine.dispose()
    app.state.engine.dispose()


def auth(client, username="asesor.bna"):
    response = client.post(
        "/gateway/sol/auth/login", json={"username": username, "password": PASSWORD}
    )
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["token"]}
