# codigos de COREDB -> (http, error_code ITIL-02)
MAPA_CORE = {
    "TARJETA_NO_ENCONTRADA": (404, "ERR-TAR-NO-ENCONTRADA"),
    "CLIENTE_NO_ENCONTRADO": (404, "ERR-CLI-NO-ENCONTRADO"),
    "BNA-CUENTA": (404, "ERR-CTA-NO-ENCONTRADA"),
    "BNA-DESBLOQUEO": (403, "ERR-TAR-DESBLOQUEO-NO-PERMITIDO"),
    "RN-TOP-001": (400, "ERR-TAR-TOPE-EXCEDIDO"),
    "ERR-TAR-007": (400, "ERR-TAR-TOPE-EXCEDIDO"),
    "REGISTRO_DUPLICADO": (409, "ERR-TAR-DUPLICADA"),
    "DATOS_INVALIDOS": (400, "ERR-TAR-DATOS-INVALIDOS"),
    "TOKEN_REQUERIDO": (401, "ERR-TAR-TOKEN-REQUERIDO"),
    "TOKEN_INVALIDO": (401, "ERR-TAR-TOKEN-INVALIDO"),
    "TOKEN_EXPIRADO": (401, "ERR-TAR-TOKEN-EXPIRADO"),
    "USUARIO_NO_VIGENTE": (401, "ERR-TAR-TOKEN-INVALIDO"),
    "PERMISO_DENEGADO": (403, "ERR-TAR-PERMISO-DENEGADO"),
}


def _http(status: int) -> int:
    # ITIL-02: 422 se homologa a 400
    return 400 if status == 422 else status


def traducir(code: str, status: int) -> tuple[int, str]:
    if code in MAPA_CORE:
        return MAPA_CORE[code]
    # Las reglas de la base (ERR-TAR-001..009) ya tienen la forma de ITIL-02
    if code.startswith("ERR-"):
        return _http(status), code
    return _http(status), "ERR-COR-" + code.replace("_", "-")
