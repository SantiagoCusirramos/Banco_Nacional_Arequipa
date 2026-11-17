"""Traducción de errores de TARJETAS/CUENTAS/COREDB a códigos del ATM."""

from ATM.exceptions import AtmError


def traducir(code: str, status_code: int) -> tuple[int, str]:
    """Convierte un código de error del módulo llamado (TARJETAS, CUENTAS, COREDB)
    al código y HTTP status que debe devolver el ATM."""
    # Errores de validación de cabecera
    if code in ("ERR-TAR-HEADER-REQUERIDO", "ERR-TAR-HEADER-INVALIDO"):
        return 400, f"ERR-ATM-{code.split('-')[-1]}"
    if code == "ERR-VALIDACION-ESQUEMA":
        return 400, "ERR-ATM-VALIDACION-ESQUEMA"

    # Errores de tarjeta
    if code == "ERR-TAR-NO-ENCONTRADA":
        return 404, "ERR-ATM-TARJETA-NO-ENCONTRADA"
    if code == "ERR-TAR-ID-INVALIDO":
        return 400, "ERR-ATM-ID-INVALIDO"
    if code == "ERR-TAR-CUENTA-INVALIDA":
        return 400, "ERR-ATM-CUENTA-INVALIDA"
    if code == "ERR-TAR-CREDENCIAL-INVALIDA":
        return 400, "ERR-ATM-CREDENCIAL-INVALIDA"
    if code == "ERR-TAR-003":  # tarjeta no operativa
        return 400, "ERR-ATM-TARJETA-NO-OPERATIVA"
    if code == "ERR-TAR-PERMISO-DENEGADO":
        return 403, "ERR-ATM-PERMISO-DENEGADO"

    # Errores de autorización / idempotencia
    if code == "ERR-TAR-IDEMPOTENCIA":
        return 409, "ERR-ATM-IDEMPOTENCIA"
    if code == "ERR-TAR-EXTORNO-NO-PERMITIDO":
        return 409, "ERR-ATM-EXTORNO-NO-PERMITIDO"
    if code == "ERR-TAR-AUTORIZACION-NO-ENCONTRADA":
        return 404, "ERR-ATM-AUTORIZACION-NO-ENCONTRADA"

    # Errores de COREDB / Bus
    if code == "ERR-COR-NO-DISPONIBLE":
        return 503, "ERR-ATM-COR-NO-DISPONIBLE"
    if code == "ERR-TAR-TIMEOUT-CORE":
        return 504, "ERR-ATM-TIMEOUT-BUS"
    if code == "ERR-COR-RESPUESTA-INVALIDA":
        return 502, "ERR-ATM-RESPUESTA_INVALIDA"
    if code == "ERR-COR-VALIDACION-ESQUEMA":
        return 400, "ERR-ATM-VALIDACION-ESQUEMA"
    if code == "ERR-COR-TOKEN-REQUERIDO":
        return 401, "ERR-ATM-TOKEN-REQUERIDO"
    if code == "ERR-COR-TOKEN-INVALIDO":
        return 401, "ERR-ATM-TOKEN-INVALIDO"
    if code == "ERR-COR-TOKEN-EXPIRADO":
        return 401, "ERR-ATM-TOKEN-EXPIRADO"

    # Errores de cliente (CUENTAS)
    if code == "ERR-CLI-NO-ENCONTRADO":
        return 404, "ERR-ATM-CLIENTE-NO-ENCONTRADO"

    # Errores de tope (vienen de TARJETAS como código de respuesta 61)
    # Se manejan en la respuesta de autorización (201 con aprobada=false)

    # Por omisión: devolver el código tal cual con status 400
    return status_code, code


def validar_monto(monto: str, moneda: str) -> tuple[bool, str | None]:
    """Valida que el monto sea múltiplo de 10 y moneda soportada.
    Devuelve (es_valido, codigo_error)."""
    try:
        valor = float(monto)
    except (TypeError, ValueError):
        return False, "ERR-ATM-MONTO_INVALIDO"
    if valor <= 0 or valor != int(valor) or int(valor) % 10 != 0:
        return False, "ERR-ATM-MONTO_INVALIDO"
    if moneda not in ("PEN", "USD"):
        return False, "ERR-ATM-MONEDA_INVALIDA"
    return True, None


def validar_resultado_dispensacion(resultado: str) -> tuple[bool, str | None]:
    if resultado not in ("DISPENSADO", "NO_DISPENSADO"):
        return False, "ERR-ATM-RESULTADO_INVALIDO"
    return True, None