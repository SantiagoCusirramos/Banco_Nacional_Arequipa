"""Sesión de tarjeta del cajero (K-3): sin un PIN validado no hay saldo ni retiro.

`/api/validar-pin` con resultado EXITOSO abre una sesión ligada a esa tarjeta y devuelve su
token (`token_sesion`). Cada operación lo presenta en la cabecera X-ATM-Sesion: la sesión
solo vale para su tarjeta, solo confirma o extorna las autorizaciones que ella misma pidió y
vence a los DURACION_S segundos. Vive en la memoria del proceso (el cajero corre con una
réplica): si el servicio se reinicia, el cliente vuelve a ingresar su clave.
"""

import secrets
import threading
import time
from dataclasses import dataclass, field

from ATM.exceptions import AtmError

DURACION_S = 180
CABECERA = "X-ATM-Sesion"


@dataclass
class Sesion:
    id_tarjeta: str
    vence: float
    autorizaciones: set[str] = field(default_factory=set)
    cuentas: set[str] = field(default_factory=set)


_sesiones: dict[str, Sesion] = {}
_candado = threading.Lock()


def abrir(id_tarjeta: str) -> str:
    token = secrets.token_urlsafe(32)
    ahora = time.monotonic()
    with _candado:
        for vencido in [t for t, s in _sesiones.items() if s.vence <= ahora]:
            del _sesiones[vencido]
        _sesiones[token] = Sesion(id_tarjeta=id_tarjeta, vence=ahora + DURACION_S)
    return token


def exigir(token: str | None, id_tarjeta: str | None = None) -> Sesion:
    with _candado:
        sesion = _sesiones.get(token or "")
        if sesion is None or sesion.vence <= time.monotonic():
            _sesiones.pop(token or "", None)
            raise AtmError("ERR-ATM-SESION-REQUERIDA",
                           "Ingrese la clave de la tarjeta para operar (sesión ausente o vencida).", 401)
    if id_tarjeta is not None and id_tarjeta != sesion.id_tarjeta:
        raise AtmError("ERR-ATM-SESION-OTRA-TARJETA", "La sesión es de otra tarjeta.", 403)
    return sesion


def exigir_autorizacion(token: str | None, uuid_autorizacion: str) -> Sesion:
    sesion = exigir(token)
    if uuid_autorizacion not in sesion.autorizaciones:
        raise AtmError("ERR-ATM-AUTORIZACION-AJENA",
                       "La autorización no fue pedida en esta sesión.", 403)
    return sesion


def cerrar(token: str | None) -> None:
    with _candado:
        _sesiones.pop(token or "", None)
