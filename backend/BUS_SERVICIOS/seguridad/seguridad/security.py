"""JWT con emisor/audiencia y contraseñas Argon2id; sin claves incorporadas."""
import time
from uuid import uuid4
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from jose import jwt, JWTError
from fastapi import HTTPException

HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
# Hash ficticio para no omitir trabajo criptográfico ante usuarios desconocidos.
DUMMY = HASHER.hash(str(uuid4()))


def matches(encoded, password):
    try:
        return HASHER.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def issue(user, settings, level='password'):
    now = int(time.time())
    return jwt.encode(dict(sub=user['id'], ver=user['token_version'],
                           iss='bna-seguridad', aud='bna-modulos', iat=now,
                           exp=now + settings.token_minutes * 60, jti=str(uuid4()), amr=level),
                      settings.secret, algorithm='HS256')


def decode(token, settings):
    try:
        claims = jwt.decode(token, settings.secret, algorithms=['HS256'],
                            audience='bna-modulos', issuer='bna-seguridad',
                            options={'require_exp': True, 'require_sub': True, 'require_iat': True})
        if not isinstance(claims.get('ver'), int):
            raise ValueError('version')
        return claims
    except (JWTError, ValueError, TypeError):
        raise HTTPException(401, 'Token inválido o vencido', headers={'WWW-Authenticate': 'Bearer'})
