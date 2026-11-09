"""Emisión y validación del JWT de acceso de COREDB.

Portado de CORE/utils/tokens.py (Nicolas Ayerve), con PyJWT:
- Firma HMAC con CORE_DB_JWT_CLAVE. El algoritmo lo fija el servidor; nunca se acepta
  el que declare el token, así que `alg=none` y las firmas ajenas se rechazan.
- El token lleva solo identidad (sub, username, rol, modulo) y los claims iss, aud,
  iat, exp, jti y type, todos obligatorios. Los permisos se consultan en cada
  petición, y el usuario se vuelve a leer de la base.
- Emisor y audiencia propios (`bna-coredb`, `coredb`): un token de la API CORE no
  sirve aquí aunque compartieran la clave.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from COREDB.config import get_settings
from COREDB.errores import ErrorAutenticacion

EMISOR = "bna-coredb"
AUDIENCIA = "coredb"
TIPO_ACCESO = "access"
ALGORITMOS_PERMITIDOS = ("HS256", "HS384", "HS512")
LONGITUD_MINIMA_CLAVE = 32
MARCADOR_DE_EJEMPLO = "change_me"
CLAIMS_OBLIGATORIOS = ["sub", "iss", "aud", "iat", "exp", "jti"]
AYUDA = "Genérela con: openssl rand -hex 32"


def _configuracion():
    s = get_settings()
    if s.jwt_algoritmo not in ALGORITMOS_PERMITIDOS:
        raise RuntimeError(
            f"CORE_DB_JWT_ALGORITMO no admitido. Use uno de {ALGORITMOS_PERMITIDOS}."
        )
    if len(s.jwt_clave) < LONGITUD_MINIMA_CLAVE or s.jwt_clave.startswith(MARCADOR_DE_EJEMPLO):
        # El mensaje nunca repite la clave.
        raise RuntimeError(
            f"CORE_DB_JWT_CLAVE debe ser propia y tener al menos {LONGITUD_MINIMA_CLAVE} "
            f"caracteres. {AYUDA}"
        )
    return s


def verificar_clave() -> None:
    """Detiene el arranque si la clave o el algoritmo no sirven."""
    _configuracion()


def crear_token(
    *, id_usuario: uuid.UUID, username: str, rol: str, modulo: str | None
) -> tuple[str, int]:
    """Devuelve (token, segundos de vigencia)."""
    s = _configuracion()
    ahora = datetime.now(timezone.utc)
    vigencia = timedelta(minutes=s.jwt_minutos)
    claims: dict[str, Any] = {
        "sub": str(id_usuario),
        "username": username,
        "rol": rol,
        "modulo": modulo,
        "type": TIPO_ACCESO,
        "iss": EMISOR,
        "aud": AUDIENCIA,
        "iat": int(ahora.timestamp()),
        "exp": int((ahora + vigencia).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(claims, s.jwt_clave, algorithm=s.jwt_algoritmo), int(vigencia.total_seconds())


def decodificar(token: str) -> dict[str, Any]:
    """Valida firma, algoritmo, emisor, audiencia, vigencia y tipo; si no, 401."""
    s = _configuracion()
    try:
        claims = jwt.decode(
            token,
            s.jwt_clave,
            algorithms=[s.jwt_algoritmo],
            issuer=EMISOR,
            audience=AUDIENCIA,
            options={"require": CLAIMS_OBLIGATORIOS},
        )
    except jwt.ExpiredSignatureError as exc:
        raise ErrorAutenticacion(
            "TOKEN_EXPIRADO", "La sesión expiró. Inicie sesión nuevamente."
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise ErrorAutenticacion("TOKEN_INVALIDO", "Token inválido.") from exc
    if claims.get("type") != TIPO_ACCESO:
        raise ErrorAutenticacion("TOKEN_INVALIDO", "Token inválido.")
    try:
        uuid.UUID(str(claims["sub"]))
    except ValueError as exc:
        raise ErrorAutenticacion("TOKEN_INVALIDO", "Token inválido.") from exc
    return claims
