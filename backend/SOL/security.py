"""Autenticación local de laboratorio; sustituible por Seguridad del BNA.

Se guardan hashes de claves y de tokens. El rol se obtiene de la sesión en
servidor; nunca se acepta un rol enviado por un formulario.
"""

import hashlib
import hmac
import secrets


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 260_000
    ).hex()
    return f"pbkdf2_sha256$260000${salt}${digest}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        _, rounds, salt, digest = encoded.split("$")
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), int(rounds)
        ).hex()
        return hmac.compare_digest(digest, actual)
    except (ValueError, TypeError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
