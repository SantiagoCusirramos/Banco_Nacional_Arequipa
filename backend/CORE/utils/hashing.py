"""Hash de contraseñas.

Las contraseñas nuevas se guardan con bcrypt (algoritmo_hash='BCRYPT').
El esquema `bna` define usuario_sistema.hash_password como CHAR(64): un
hash bcrypt ocupa 60 caracteres y cabe sin cambiar el modelo, Argon2 no.

SHA-256 se conserva solo para verificar los usuarios existentes
(algoritmo_hash='SHA256', los seeds usan MySQL SHA2(pass,256)), que pasan
a bcrypt en su primer login exitoso. No se guarda jamás la contraseña en
claro.
"""

import hashlib
import hmac

from passlib.context import CryptContext

ALGORITMO_SHA256 = "SHA256"
ALGORITMO_BCRYPT = "BCRYPT"
LIMITE_BCRYPT_BYTES = 72

_contexto = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_sha256(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_sha256(password: str, hash_almacenado: str | None) -> bool:
    if not hash_almacenado or not isinstance(hash_almacenado, str):
        return False
    try:
        return hmac.compare_digest(hash_sha256(password), hash_almacenado)
    except (TypeError, UnicodeEncodeError):  # hash corrupto o contraseña sin UTF-8 válido
        return False


def es_utf8_valida(password: str) -> bool:
    """Una cadena con un surrogate aislado no se puede codificar en UTF-8."""
    try:
        password.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def bcrypt_admite(password: str) -> bool:
    """bcrypt trunca en silencio a los 72 bytes y no admite el carácter nulo."""
    return (
        es_utf8_valida(password)
        and len(password.encode("utf-8")) <= LIMITE_BCRYPT_BYTES
        and "\x00" not in password
    )


def hash_bcrypt(password: str) -> str:
    if not bcrypt_admite(password):
        raise ValueError("La contraseña no es admitida por bcrypt.")
    return _contexto.hash(password)


def simular_verificacion() -> None:
    """Gasta el tiempo de una verificación bcrypt sin comparar nada real."""
    _contexto.dummy_verify()


def verify_bcrypt(password: str, hash_almacenado: str | None) -> bool:
    if not hash_almacenado or not isinstance(hash_almacenado, str) or not bcrypt_admite(password):
        simular_verificacion()
        return False
    try:
        return _contexto.verify(password, hash_almacenado)
    except ValueError:  # hash malformado o de otro esquema
        simular_verificacion()
        return False


def verify_password(
    password: str, hash_almacenado: str | None, algoritmo: str | None
) -> bool:
    """Verifica según usuario_sistema.algoritmo_hash; cualquier otro valor se deniega."""
    if algoritmo == ALGORITMO_BCRYPT:
        return verify_bcrypt(password, hash_almacenado)
    if algoritmo == ALGORITMO_SHA256:
        return verify_sha256(password, hash_almacenado)
    return False
