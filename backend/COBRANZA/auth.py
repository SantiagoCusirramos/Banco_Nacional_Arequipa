"""Autenticacion simple por rol (I-04), header X-API-Key. Las claves viven en .env, nunca en el
codigo (ver .env.example). Roles: COBRANZA_LEER (consultas, auditoria, conciliacion, metricas),
COBRANZA_EJECUTAR (mora, recalcular-estado, resolver pagos) e INTEGRACION_BUS (CR-INT-06/CR-INT-08).
Sin clave -> 401. Clave valida pero rol sin permiso -> 403. /salud queda libre."""
import os

from fastapi import Security
from fastapi.security import APIKeyHeader

from .servicio import ErrorNegocio

ROLES = ("COBRANZA_LEER", "COBRANZA_EJECUTAR", "INTEGRACION_BUS")

# APIKeyHeader (en vez de HTTPException manual) para que Swagger muestre el boton "Authorize".
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _claves_por_rol():
    return {rol: os.environ.get(f"API_KEY_{rol}", "").strip() for rol in ROLES}


def _rol_de_la_clave(clave):
    for rol, valor in _claves_por_rol().items():
        if valor and clave == valor:
            return rol
    return None


def requerir_rol(*roles_permitidos):
    """Dependencia de FastAPI: exige X-API-Key y que su rol este en roles_permitidos.
    Devuelve el rol (str), usado luego como usuarioOperador de la auditoria (RN-CR-GEN-004)."""

    def dependencia(api_key: str = Security(_api_key_header)):
        if not api_key:
            raise ErrorNegocio(401, "Falta la clave X-API-Key", "AUTENTICACION")
        rol = _rol_de_la_clave(api_key)
        if rol is None:
            raise ErrorNegocio(401, "X-API-Key invalida", "AUTENTICACION")
        if rol not in roles_permitidos:
            raise ErrorNegocio(
                403, f"El rol {rol} no tiene permiso para esta operacion "
                     f"(se requiere: {', '.join(roles_permitidos)})", "AUTORIZACION")
        return rol

    return dependencia
