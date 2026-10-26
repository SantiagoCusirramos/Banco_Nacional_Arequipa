# codigos de CORE -> (http, error_code ITIL-02)
MAPA_CORE = {
    "SALDO_INSUFICIENTE": (400, "ERR-CTA-FONDOS-INSUFICIENTES"),
    "TOPE_DIARIO_EXCEDIDO": (400, "ERR-CTA-TOPE-EXCEDIDO"),
    "CUENTA_NO_OPERATIVA": (403, "ERR-CTA-BLOQUEADA"),
    "CUENTA_NO_ENCONTRADA": (404, "ERR-CTA-NO-ENCONTRADA"),
    "CLIENTE_NO_ENCONTRADO": (404, "ERR-CLI-NO-ENCONTRADO"),
    "PRODUCTO_NO_ENCONTRADO": (404, "ERR-CTA-PRODUCTO-NO-ENCONTRADO"),
    "AGENCIA_NO_ENCONTRADA": (404, "ERR-CTA-AGENCIA-NO-ENCONTRADA"),
    "CANAL_NO_ENCONTRADO": (400, "ERR-CTA-CANAL-INVALIDO"),
    "TIPO_CAMBIO_NO_ENCONTRADO": (400, "ERR-COR-TC-NO-VIGENTE"),
    "CUENTA_MANCOMUNADA_INCOMPLETA": (400, "ERR-CTA-MANCOMUNADA-SIN-COTITULARES"),
    "TRANSFERENCIA_MISMA_CUENTA": (400, "ERR-CTA-CUENTAS-IGUALES"),
    "MONTO_INVALIDO": (400, "ERR-CTA-MONTO-INVALIDO"),
}


def _http(status: int) -> int:
    # ITIL-02: 422 se homologa a 400
    return 400 if status == 422 else status


def traducir(code: str, status: int) -> tuple[int, str]:
    if code in MAPA_CORE:
        return MAPA_CORE[code]
    if code.startswith("ERR-"):
        return _http(status), code
    return _http(status), "ERR-COR-" + code.replace("_", "-")
