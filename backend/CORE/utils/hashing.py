"""Hash de contraseñas.

El esquema `bna` define usuario_sistema.hash_password como CHAR(64) con
algoritmo_hash='SHA256' (los seeds usan MySQL SHA2(pass,256)). CORE
reproduce ese mismo esquema con hashlib para poder validar los usuarios
semilla. No se guarda jamás la contraseña en claro.
"""

import hashlib
import hmac


def hash_sha256(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_sha256(password: str, hash_almacenado: str) -> bool:
    return hmac.compare_digest(hash_sha256(password), hash_almacenado)
