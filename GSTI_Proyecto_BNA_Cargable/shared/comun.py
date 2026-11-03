"""Utilidades comunes a los cuatro servicios: errores JSON, tokens de servicio y logging.

Formato de error de TODAS las APIs:
    {"correcto": false, "codigo": "CLIENTE_DUPLICADO", "mensaje": "El cliente ya está registrado"}
"""
import hmac
import logging
import os

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader, HTTPBasic, HTTPBasicCredentials
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("bna")


def configurar_logging() -> None:
    nivel = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=nivel, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # Nunca registrar cuerpos de petición: pueden contener plantillas biométricas.
    logging.getLogger("httpx").setLevel(logging.WARNING)


def entorno(nombre: str, defecto: str | None = None) -> str:
    """Lee una variable de entorno; si no existe y no hay valor por defecto, el servicio no arranca."""
    valor = os.getenv(nombre, defecto)
    if valor is None or valor == "":
        raise RuntimeError(f"Falta la variable de entorno obligatoria: {nombre}")
    return valor


def enmascarar_doc(numero: str) -> str:
    """12345678 -> *****678 (para logs)."""
    return "*" * max(len(numero) - 3, 0) + numero[-3:]


class ApiError(Exception):
    def __init__(self, status: int, codigo: str, mensaje: str, **extra):
        self.status, self.codigo, self.mensaje, self.extra = status, codigo, mensaje, extra


def respuesta_error(status: int, codigo: str, mensaje: str, **extra) -> JSONResponse:
    return JSONResponse(status_code=status, content={"correcto": False, "codigo": codigo, "mensaje": mensaje, **extra})


_CODIGOS_HTTP = {401: "NO_AUTORIZADO", 403: "PROHIBIDO", 404: "NO_ENCONTRADO", 405: "METODO_NO_PERMITIDO"}


def instalar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, e: ApiError):
        return respuesta_error(e.status, e.codigo, e.mensaje, **e.extra)

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, e: RequestValidationError):
        # Solo ubicación y mensaje del error: jamás el valor recibido (podría ser una plantilla biométrica).
        detalle = [{"campo": ".".join(str(p) for p in err["loc"][1:]) or "cuerpo", "mensaje": err["msg"]} for err in e.errors()[:10]]
        return respuesta_error(422, "DATOS_INVALIDOS", "Los datos enviados no son válidos", detalle=detalle)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, e: StarletteHTTPException):
        resp = respuesta_error(e.status_code, _CODIGOS_HTTP.get(e.status_code, "ERROR_HTTP"), str(e.detail))
        if e.headers:
            resp.headers.update(e.headers)
        return resp

    @app.exception_handler(Exception)
    async def _inesperado(_: Request, e: Exception):
        log.exception("Error no controlado")
        return respuesta_error(500, "ERROR_INTERNO", "Error interno del servicio")


_cabecera_token = APIKeyHeader(name="X-Service-Token", auto_error=False, description="Credencial de servicio")


def requerir_token(token_esperado: str):
    """Dependencia FastAPI: exige la cabecera X-Service-Token con el valor configurado."""

    def dependencia(token: str | None = Depends(_cabecera_token)) -> None:
        if not token or not hmac.compare_digest(token.encode(), token_esperado.encode()):
            raise ApiError(401, "NO_AUTORIZADO", "Credencial de servicio inválida o ausente")

    return dependencia


def requerir_basic(usuario: str, clave: str, realm: str):
    """Dependencia FastAPI: autenticación HTTP Basic sencilla para las interfaces administrativas."""
    esquema = HTTPBasic(auto_error=False, realm=realm)

    def dependencia(cred: HTTPBasicCredentials | None = Depends(esquema)) -> None:
        ok = cred is not None and hmac.compare_digest(cred.username.encode(), usuario.encode()) \
            and hmac.compare_digest(cred.password.encode(), clave.encode())
        if not ok:
            raise StarletteHTTPException(status_code=401, detail="Autenticación administrativa requerida",
                                         headers={"WWW-Authenticate": f'Basic realm="{realm}"'})

    return dependencia
