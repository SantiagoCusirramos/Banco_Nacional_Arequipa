"""Emisión y validación de JWT de acceso (RFC 7519) para CORE.

- Firma simétrica HMAC (HS256 por defecto) con `SECRET_KEY` del .env.
- El algoritmo se fija en el servidor: jamás se confía en el `alg` que
  declare el encabezado del token (evita `alg=none` y confusión de claves).
- El token NO lleva permisos: solo identidad (sub, username, rol). Los
  permisos se consultan en cada petición contra `rbac.json`, de modo que
  un cambio de rol o de permisos surte efecto de inmediato.
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

from CORE.config import get_settings
from CORE.exceptions import AuthenticationError

ISSUER = "bna-core"
TIPO_ACCESO = "access"
ALGORITMOS_PERMITIDOS = ("HS256", "HS384", "HS512")
LONGITUD_MINIMA_CLAVE = 32
MARCADOR_DE_EJEMPLO = "change_me"  # valor de .env.example


def _configuracion():
    s = get_settings()
    if s.algorithm not in ALGORITMOS_PERMITIDOS:
        raise RuntimeError(
            f"ALGORITHM={s.algorithm!r} no admitido. Use uno de {ALGORITMOS_PERMITIDOS}."
        )
    if len(s.secret_key) < LONGITUD_MINIMA_CLAVE or s.secret_key.startswith(MARCADOR_DE_EJEMPLO):
        raise RuntimeError(
            f"SECRET_KEY debe ser propia y tener al menos {LONGITUD_MINIMA_CLAVE} "
            "caracteres. Genere una con: openssl rand -hex 32"
        )
    return s


def crear_token_acceso(*, id_usuario: str, username: str, rol: str) -> tuple[str, int]:
    """Devuelve (token, segundos_de_vigencia)."""
    s = _configuracion()
    ahora = datetime.now(timezone.utc)
    vigencia = timedelta(minutes=s.access_token_expire_minutes)
    claims: dict[str, Any] = {
        "sub": id_usuario,
        "username": username,
        "rol": rol,
        "type": TIPO_ACCESO,
        "iss": ISSUER,
        "iat": int(ahora.timestamp()),
        "exp": int((ahora + vigencia).timestamp()),
        "jti": str(uuid4()),
    }
    token = jwt.encode(claims, s.secret_key, algorithm=s.algorithm)
    return token, int(vigencia.total_seconds())


def decodificar_token(token: str) -> dict[str, Any]:
    """Valida firma, emisor, vencimiento y tipo. Lanza AuthenticationError (401)."""
    s = _configuracion()
    try:
        claims = jwt.decode(
            token,
            s.secret_key,
            algorithms=[s.algorithm],
            issuer=ISSUER,
            options={"require_exp": True, "require_iat": True, "require_sub": True,
                     "require_iss": True},
        )
    except ExpiredSignatureError as exc:
        raise AuthenticationError("TOKEN_EXPIRADO", "La sesión expiró. Inicie sesión nuevamente.") from exc
    except JWTError as exc:
        raise AuthenticationError("TOKEN_INVALIDO", "Token inválido.") from exc

    if claims.get("type") != TIPO_ACCESO:
        raise AuthenticationError("TOKEN_INVALIDO", "Token inválido.")
    return claims
