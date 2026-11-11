"""Contratos del prototipo. Montable en main:app, con estado independiente."""
import hashlib
import hmac
import json
import re
import secrets
import time
from datetime import datetime
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .schemas import Login, Operation, Incident, IncidentUpdate
from .security import HASHER, DUMMY, matches, issue, decode
from .store import Store, utcnow

bearer = HTTPBearer(auto_error=False)
LIMITS = {'ATM': Decimal('1000.00'), 'HOME_BANKING': Decimal('5000.00'), 'BILLETERA': Decimal('500.00')}
SLA = {'P1': (15, 120), 'P2': (30, 240), 'P3': (120, 1440), 'P4': (480, 4320)}


def store(request: Request):
    # Inicialización diferida: importar el CORE no exige configurar este prototipo.
    if not getattr(request.app.state, 'seguridad_store', None):
        from .config import Settings
        request.app.state.seguridad_store = Store(Settings.from_env())
    return request.app.state.seguridad_store


def correlation(request: Request):
    cid = request.headers.get('X-Correlation-ID', '')
    if not re.fullmatch(r'[a-zA-Z0-9_.:-]{1,100}', cid):
        raise HTTPException(400, 'X-Correlation-ID obligatorio: 1–100 caracteres seguros')
    return cid


def current_user(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if credentials is None:
        raise HTTPException(401, 'Bearer requerido', headers={'WWW-Authenticate': 'Bearer'})
    state = store(request)
    claims = decode(credentials.credentials, state.settings)
    with state.transaction() as db:
        user = db.execute('SELECT * FROM users WHERE id=?', (claims['sub'],)).fetchone()
        if not user or not user['active'] or user['token_version'] != claims['ver'] or user['locked_until'] > time.time():
            raise HTTPException(401, 'Sesión no vigente')
        return dict(user)


def roles(*allowed):
    def dependency(user=Depends(current_user)):
        if user['role'] not in allowed:
            raise HTTPException(403, 'Acción no autorizada para el rol')
        return user
    return dependency


router = APIRouter(prefix='/seguridad', tags=['Módulo 9 · Seguridad'], dependencies=[Depends(correlation)])


@router.get('/estado')
def status():
    return dict(module='SEGURIDAD', mode='PROTOTIPO_LOCAL', version='0.2.0',
                real_integrations=[], pending=['Bus M8', 'identidades CORE/MySQL', 'M4 Token Matriz',
                 'M3 topes y saldos', 'M5 extorno', 'RENIEC', 'HSM', 'SIEM', 'SMS'],
                currency_policy='Topes de demostración por moneda; sin conversión FX')


@router.post('/auth/login')
def login(body: Login, request: Request):
    state = store(request)
    valid = False
    with state.transaction() as db:
        user = db.execute('SELECT * FROM users WHERE username=?', (body.username,)).fetchone()
        now = time.time()
        verified = matches(user['password_hash'] if user else DUMMY, body.password)
        if user and user['active'] and user['locked_until'] <= now:
            valid = verified
            if valid:
                db.execute('UPDATE users SET failures=0,locked_until=0 WHERE id=?', (user['id'],))
            else:
                failures = (user['failures'] if not user['locked_until'] else 0) + 1
                locked = now + state.settings.lock_seconds if failures >= 3 else 0
                db.execute('UPDATE users SET failures=?,locked_until=?,token_version=token_version+? WHERE id=?',
                           (failures, locked, int(locked > 0), user['id']))
        state.audit(db, 'LOGIN_OK' if valid else 'LOGIN_RECHAZADO', user['id'] if user else 'desconocido',
                    correlation(request), {'canal': 'PROTOTIPO'})
        token = issue(user, state.settings) if valid else None
    # El rechazo se emite después del commit: los intentos y el bloqueo persisten.
    if not valid:
        raise HTTPException(401, 'Usuario o contraseña incorrectos', headers={'WWW-Authenticate': 'Bearer'})
    return dict(access_token=token, token_type='bearer', expires_in=state.settings.token_minutes * 60)


@router.get('/auth/me')
def me(user=Depends(current_user)):
    return {key: user[key] for key in ('id', 'username', 'role')}


@router.post('/auth/logout')
def logout(request: Request, user=Depends(current_user)):
    state = store(request)
    with state.transaction() as db:
        db.execute('UPDATE users SET token_version=token_version+1 WHERE id=?', (user['id'],))
        state.audit(db, 'LOGOUT_TODAS_SESIONES', user['id'], correlation(request))
    return {'revoked': True}


@router.post('/operaciones/evaluar')
def evaluate(body: Operation, request: Request, user=Depends(roles('CLIENTE', 'ADMINISTRADOR'))):
    """Decisión local, NO movimiento contable. Acumula autorizaciones, sin confiar en body."""
    state = store(request)
    day = datetime.now(ZoneInfo('America/Lima')).date().isoformat()
    error = None
    result = None
    with state.transaction() as db:
        existing = db.execute('SELECT * FROM decisions WHERE operation_id=?', (body.operation_id,)).fetchone()
        amount = format(body.amount, '.2f')
        if existing:
            if (existing['user_id'], existing['amount'], existing['currency'], existing['channel']) != (user['id'], amount, body.currency, body.channel):
                raise HTTPException(409, 'operation_id ya utilizado con otros datos')
            return json.loads(existing['result'])
        rows = db.execute('SELECT amount FROM decisions WHERE user_id=? AND currency=? AND channel=? AND day=?',
                          (user['id'], body.currency, body.channel, day)).fetchall()
        accumulated = sum((Decimal(row['amount']) for row in rows), Decimal('0.00'))
        total = accumulated + body.amount
        limit = LIMITS[body.channel]
        if total > limit:
            state.audit(db, 'TOPE_RECHAZADO', user['id'], correlation(request), {'operation_id': body.operation_id})
            error = (403, 'Tope diario de demostración excedido')
        elif total > limit * Decimal('0.80'):
            challenge = db.execute('SELECT * FROM challenges WHERE id=?', (body.challenge_id or '',)).fetchone()
            binding = challenge and (challenge['user_id'], challenge['operation_id'], challenge['amount'], challenge['currency'], challenge['channel']) == (user['id'], body.operation_id, amount, body.currency, body.channel)
            if not body.challenge_id and not body.otp:
                cid, otp = str(uuid4()), f'{secrets.randbelow(1000000):06d}'
                digest = hmac.new(state.settings.secret.encode(), (cid + ':' + otp).encode(), hashlib.sha256).hexdigest()
                db.execute('INSERT INTO challenges(id,user_id,operation_id,amount,currency,channel,expires,digest) VALUES(?,?,?,?,?,?,?,?)',
                           (cid, user['id'], body.operation_id, amount, body.currency, body.channel, time.time() + 120, digest))
                state.audit(db, 'DESAFIO_LOCAL_CREADO', user['id'], correlation(request), {'operation_id': body.operation_id})
                # El OTP viaja por el mismo canal SOLO para la demostración. No constituye 2FA real.
                return dict(decision='DESAFIO_REQUERIDO', challenge_id=cid, expires_in=120,
                            demo_otp=otp, warning='SIMULACION: mismo canal; pendiente proveedor de segundo factor')
            digest = hmac.new(state.settings.secret.encode(), ((body.challenge_id or '') + ':' + (body.otp or '')).encode(), hashlib.sha256).hexdigest()
            if not binding or challenge['used'] or challenge['expires'] < time.time() or challenge['tries'] >= 3 or not hmac.compare_digest(challenge['digest'], digest):
                if binding:
                    db.execute('UPDATE challenges SET tries=tries+1 WHERE id=?', (body.challenge_id,))
                state.audit(db, 'DESAFIO_RECHAZADO', user['id'], correlation(request))
                error = (401, 'Desafío inválido, vencido o agotado')
            else:
                db.execute('UPDATE challenges SET used=1 WHERE id=?', (body.challenge_id,))
        if error is None:
            result = dict(decision='AUTORIZADA_LOCAL', operation_id=body.operation_id,
                          accumulated=format(total, '.2f'), limit=format(limit, '.2f'),
                          currency=body.currency, financial_effect=False)
            db.execute('INSERT INTO decisions VALUES(?,?,?,?,?,?,?)',
                       (body.operation_id, user['id'], amount, body.currency, body.channel, day, json.dumps(result)))
            state.audit(db, 'OPERACION_AUTORIZADA_LOCAL', user['id'], correlation(request),
                        {'operation_id': body.operation_id, 'amount': amount, 'currency': body.currency})
    if error:
        raise HTTPException(*error)
    return result


@router.get('/auditoria')
def audit_list(request: Request, user=Depends(roles('ADMINISTRADOR', 'AUDITOR'))):
    with store(request).transaction() as db:
        rows = db.execute('SELECT * FROM audit ORDER BY seq DESC LIMIT 100').fetchall()
        return [dict(seq=r['seq'], **json.loads(r['payload']), signature=r['signature']) for r in rows]


@router.get('/auditoria/verificar')
def audit_verify(request: Request, user=Depends(roles('ADMINISTRADOR', 'AUDITOR'))):
    state = store(request)
    with state.transaction() as db:
        return state.verify(db)


@router.post('/incidentes', status_code=201)
def create_incident(body: Incident, request: Request, user=Depends(roles('ADMINISTRADOR', 'OPERADOR'))):
    state, iid = store(request), str(uuid4())
    now = utcnow()
    with state.transaction() as db:
        db.execute('INSERT INTO incidents VALUES(?,?,?,?,?,?,?,?)',
                   (iid, body.priority, body.title, 'ABIERTO', user['id'], now, now, None,))
        state.audit(db, 'INCIDENTE_ABIERTO', user['id'], correlation(request), {'incident_id': iid})
    return dict(id=iid, status='ABIERTO', response_minutes=SLA[body.priority][0],
                resolution_minutes=SLA[body.priority][1], targets='propuestos; reloj de demostración continuo')


@router.get('/incidentes')
def incidents(request: Request, user=Depends(roles('ADMINISTRADOR', 'AUDITOR', 'OPERADOR'))):
    with store(request).transaction() as db:
        return [dict(r) for r in db.execute('SELECT * FROM incidents ORDER BY created DESC')]


@router.patch('/incidentes/{iid}')
def update_incident(iid: str, body: IncidentUpdate, request: Request, user=Depends(roles('ADMINISTRADOR', 'OPERADOR'))):
    transitions = {'ABIERTO': 'EN_PROGRESO', 'EN_PROGRESO': 'RESUELTO', 'RESUELTO': 'CERRADO'}
    state = store(request)
    with state.transaction() as db:
        row = db.execute('SELECT * FROM incidents WHERE id=?', (iid,)).fetchone()
        if not row:
            raise HTTPException(404, 'Incidente no encontrado')
        if transitions.get(row['status']) != body.status:
            raise HTTPException(409, 'Transición de estado inválida')
        if body.status == 'RESUELTO' and not body.resolution:
            raise HTTPException(422, 'La resolución requiere descripción')
        db.execute('UPDATE incidents SET status=?,updated=?,resolution=COALESCE(?,resolution) WHERE id=?',
                   (body.status, utcnow(), body.resolution, iid))
        state.audit(db, 'INCIDENTE_' + body.status, user['id'], correlation(request), {'incident_id': iid})
    return dict(id=iid, status=body.status)


def mount(app):
    app.include_router(router)
