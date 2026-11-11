import json
import time
from concurrent.futures import ThreadPoolExecutor
from jose import jwt
import pytest
from .conftest import login


def op(**kwargs):
    return dict(operation_id='operation-0001', amount='100.00', currency='PEN', channel='ATM', **kwargs)


def test_correlation_obligatoria(client):
    assert client.get('/seguridad/estado', headers={'X-Correlation-ID': ''}).status_code == 400
    assert client.get('/seguridad/estado', headers={'X-Correlation-ID': '<script>'}).status_code == 400
    assert client.get('/seguridad/estado').json()['mode'] == 'PROTOTIPO_LOCAL'


def test_login_jwt_actor_y_logout(client):
    headers = login(client)
    assert client.get('/seguridad/auth/me', headers=headers).json()['role'] == 'ADMINISTRADOR'
    events = client.get('/seguridad/auditoria', headers=headers).json()
    assert events[0]['event'] == 'LOGIN_OK'
    assert 'password' not in json.dumps(events).lower()
    assert client.post('/seguridad/auth/logout', headers=headers).status_code == 200
    assert client.get('/seguridad/auth/me', headers=headers).status_code == 401


def test_bloqueo_tercer_intento_persistente(client):
    for _ in range(3):
        r = client.post('/seguridad/auth/login', json={'username': 'cliente', 'password': 'incorrecta'})
        assert r.status_code == 401
    assert client.post('/seguridad/auth/login', json={'username': 'cliente', 'password': 'Local-Test-2026!'}).status_code == 401
    with client.app.state.seguridad_store.transaction() as db:
        u = db.execute("SELECT * FROM users WHERE username='cliente'").fetchone()
        assert u['failures'] == 3 and u['locked_until'] > time.time()


def test_usuario_inexistente_mensaje_generico(client):
    a = client.post('/seguridad/auth/login', json={'username': 'no-existe', 'password': 'incorrecta'})
    b = client.post('/seguridad/auth/login', json={'username': 'cliente', 'password': 'incorrecta'})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_rol_no_autorizado_y_actor_body(client):
    h = login(client, 'cliente')
    assert client.get('/seguridad/auditoria', headers=h).status_code == 403
    assert client.post('/seguridad/incidentes', headers=h, json={'title': 'Prueba no autorizada', 'priority': 'P1'}).status_code == 403
    assert client.post('/seguridad/operaciones/evaluar', headers=h, json={**op(), 'actor': 'admin'}).status_code == 422


@pytest.mark.parametrize('kind', ['expired', 'signature', 'audience'])
def test_jwt_rechazado(client, kind):
    state = client.app.state.seguridad_store
    with state.transaction() as db:
        uid = db.execute("SELECT id FROM users WHERE username='admin'").fetchone()['id']
    claims = dict(sub=uid, ver=0, iss='bna-seguridad', aud='bna-modulos', iat=int(time.time()) - 20, exp=int(time.time()) + 60)
    secret = state.settings.secret
    if kind == 'expired': claims['exp'] = int(time.time()) - 1
    if kind == 'signature': secret = 'otra-clave-' + 'a' * 40
    if kind == 'audience': claims['aud'] = 'otro-servicio'
    t = jwt.encode(claims, secret, algorithm='HS256')
    assert client.get('/seguridad/auth/me', headers={'Authorization': 'Bearer ' + t}).status_code == 401


def test_tope_desafio_idempotencia_y_sin_dinero(client):
    h = login(client, 'cliente')
    a = {**op(), 'amount': '850.00'}
    r = client.post('/seguridad/operaciones/evaluar', headers=h, json=a).json()
    assert r['decision'] == 'DESAFIO_REQUERIDO'
    assert 'SIMULACION' in r['warning']
    confirmed = client.post('/seguridad/operaciones/evaluar', headers=h, json={**a, 'challenge_id': r['challenge_id'], 'otp': r['demo_otp']})
    assert confirmed.status_code == 200
    assert confirmed.json()['accumulated'] == '850.00'
    assert confirmed.json()['financial_effect'] is False
    assert client.post('/seguridad/operaciones/evaluar', headers=h, json=a).json() == confirmed.json()
    assert client.post('/seguridad/operaciones/evaluar', headers=h, json={**a, 'amount': '849.00'}).status_code == 409
    assert client.post('/seguridad/operaciones/evaluar', headers=h, json={**a, 'operation_id': 'operation-0002', 'amount': '150.01'}).status_code == 403


def test_desafio_ligado_a_operacion_y_limite_intentos(client):
    h = login(client, 'cliente')
    a = {**op(), 'amount': '850.00'}
    r = client.post('/seguridad/operaciones/evaluar', headers=h, json=a).json()
    stolen = {**a, 'operation_id': 'operation-otra', 'challenge_id': r['challenge_id'], 'otp': r['demo_otp']}
    assert client.post('/seguridad/operaciones/evaluar', headers=h, json=stolen).status_code == 401
    wrong = '000000' if r['demo_otp'] != '000000' else '111111'
    for _ in range(3):
        assert client.post('/seguridad/operaciones/evaluar', headers=h, json={**a, 'challenge_id': r['challenge_id'], 'otp': wrong}).status_code == 401
    assert client.post('/seguridad/operaciones/evaluar', headers=h, json={**a, 'challenge_id': r['challenge_id'], 'otp': r['demo_otp']}).status_code == 401


def test_montos_moneda_y_aislamiento(client):
    h = login(client, 'cliente')
    for value in ['-1', '0', '1.001', 'NaN', 'Infinity']:
        assert client.post('/seguridad/operaciones/evaluar', headers=h, json={**op(), 'amount': value}).status_code == 422
    assert client.post('/seguridad/operaciones/evaluar', headers=h, json={**op(), 'currency': 'EUR'}).status_code == 422
    for currency in ['PEN', 'USD']:
        r = client.post('/seguridad/operaciones/evaluar', headers=h, json={**op(), 'operation_id': 'moneda-'+currency, 'amount': '800.00', 'currency': currency})
        assert r.json()['accumulated'] == '800.00'


def test_auditoria_detecta_manipulacion(client):
    h = login(client)
    assert client.get('/seguridad/auditoria/verificar', headers=h).json()['valid'] is True
    with client.app.state.seguridad_store.transaction() as db:
        db.execute("UPDATE audit SET payload='{}' WHERE seq=1")
    assert client.get('/seguridad/auditoria/verificar', headers=h).json()['valid'] is False


def test_incidente_ciclo_y_resolucion_obligatoria(client):
    h = login(client)
    r = client.post('/seguridad/incidentes', headers=h, json={'title': 'Caída de autenticación local', 'priority': 'P1'})
    assert r.status_code == 201, r.text
    iid = r.json()['id']
    assert r.json()['response_minutes'] == 15
    path = '/seguridad/incidentes/' + iid
    assert client.patch(path, headers=h, json={'status': 'CERRADO'}).status_code == 409
    assert client.patch(path, headers=h, json={'status': 'EN_PROGRESO'}).status_code == 200
    assert client.patch(path, headers=h, json={'status': 'RESUELTO'}).status_code == 422
    assert client.patch(path, headers=h, json={'status': 'RESUELTO', 'resolution': 'Servicio restaurado y validado'}).status_code == 200
    assert client.patch(path, headers=h, json={'status': 'CERRADO'}).status_code == 200
    assert client.get('/seguridad/incidentes', headers=h).json()[0]['status'] == 'CERRADO'


def test_autorizacion_concurrente_no_duplica_acumulado(client):
    h = login(client, 'cliente')
    def evaluate(_):
        return client.post('/seguridad/operaciones/evaluar', headers=h, json=op()).json()
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(evaluate, range(8)))
    assert all(r['accumulated'] == '100.00' for r in results)
    with client.app.state.seguridad_store.transaction() as db:
        assert db.execute('SELECT count(*) FROM decisions').fetchone()[0] == 1


def test_desafio_vencido(client):
    h = login(client, 'cliente')
    a = {**op(), 'amount': '850.00'}
    r = client.post('/seguridad/operaciones/evaluar', headers=h, json=a).json()
    with client.app.state.seguridad_store.transaction() as db:
        db.execute('UPDATE challenges SET expires=0 WHERE id=?', (r['challenge_id'],))
    assert client.post('/seguridad/operaciones/evaluar', headers=h, json={**a, 'challenge_id': r['challenge_id'], 'otp': r['demo_otp']}).status_code == 401


def test_bloqueo_revoca_sesion_anterior_y_se_recupera(client):
    h = login(client, 'cliente')
    for _ in range(3):
        client.post('/seguridad/auth/login', json={'username': 'cliente', 'password': 'incorrecta'})
    assert client.get('/seguridad/auth/me', headers=h).status_code == 401
    with client.app.state.seguridad_store.transaction() as db:
        db.execute("UPDATE users SET locked_until=? WHERE username='cliente'", (time.time() - 1,))
    assert login(client, 'cliente')
    assert client.get('/seguridad/auth/me', headers=h).status_code == 401


def test_inactivo_sin_acceso(client):
    h = login(client, 'cliente')
    with client.app.state.seguridad_store.transaction() as db:
        db.execute("UPDATE users SET active=0 WHERE username='cliente'")
    assert client.get('/seguridad/auth/me', headers=h).status_code == 401
    assert client.post('/seguridad/auth/login', json={'username': 'cliente', 'password': 'Local-Test-2026!'}).status_code == 401


def test_persistencia_y_backup_restaurable(client, tmp_path):
    import sqlite3
    from seguridad.store import Store
    h = login(client)
    state = client.app.state.seguridad_store
    backup = str(tmp_path / 'restored.sqlite3')
    with sqlite3.connect(state.settings.database) as source, sqlite3.connect(backup) as target:
        source.backup(target)
    from seguridad.config import Settings
    restored = Store(Settings(backup, state.settings.secret))
    with restored.transaction() as db:
        assert restored.verify(db)['valid'] is True
        assert db.execute('SELECT count(*) FROM users').fetchone()[0] == 3
    client.app.state.seguridad_store = restored
    assert client.get('/seguridad/auth/me', headers=h).status_code == 200


def test_sin_token_y_auditor_solo_lectura(client):
    assert client.get('/seguridad/auditoria').status_code == 401
    h = login(client, 'auditor')
    assert client.get('/seguridad/auditoria', headers=h).status_code == 200
    assert client.post('/seguridad/operaciones/evaluar', headers=h, json=op()).status_code == 403
