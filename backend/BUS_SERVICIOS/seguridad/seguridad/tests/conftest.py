import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from seguridad.app import app
from seguridad.config import Settings
from seguridad.store import Store
from seguridad.security import HASHER


@pytest.fixture
def client(tmp_path):
    state = Store(Settings(str(tmp_path / 'test.sqlite3'), 'test-only-' + 'x' * 40))
    with state.transaction() as db:
        for name, role in [('admin', 'ADMINISTRADOR'), ('cliente', 'CLIENTE'), ('auditor', 'AUDITOR')]:
            db.execute('INSERT INTO users(id,username,password_hash,role) VALUES(?,?,?,?)',
                       (str(uuid4()), name, HASHER.hash('Local-Test-2026!'), role))
    app.state.seguridad_store = state
    with TestClient(app, headers={'X-Correlation-ID': 'pytest-seguridad'}) as c:
        yield c


def login(client, username='admin'):
    r = client.post('/seguridad/auth/login', json={'username': username, 'password': 'Local-Test-2026!'})
    assert r.status_code == 200, r.text
    return {'Authorization': 'Bearer ' + r.json()['access_token']}
