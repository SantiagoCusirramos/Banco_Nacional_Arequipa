"""Tarea diaria de Cobranza: marca las cuotas vencidas y recalcula los créditos.

La ejecuta el usuario de servicio `svc-cobranza` (`SERVICIO:COBRANZA`), no una persona: usa su
token de COREDB y la misma operación que la ruta `/api/v1/vencimientos`. Desde backend/:

    python -m COBRANZA.scripts.tarea_diaria [AAAA-MM-DD]

Sin fecha, COREDB usa el día de hoy.
"""
from __future__ import annotations

import logging
import sys
from datetime import date

from COBRANZA.config import Config
from COBRANZA.coredb import ClienteCoreDb

log = logging.getLogger("cobranza.tarea_diaria")


def ejecutar(cliente: ClienteCoreDb, fecha: date | str | None = None) -> dict:
    """Pide a COREDB los vencimientos de `fecha` (hoy si no se indica) con el token del servicio."""
    if isinstance(fecha, date):
        fecha = fecha.isoformat()
    cuerpo = {"fecha": fecha} if fecha else {}
    return cliente.como_servicio("POST", "/coredb/creditos/vencimientos", json=cuerpo)[1]


def main(argumentos: list[str] | None = None) -> int:
    argumentos = sys.argv[1:] if argumentos is None else argumentos
    fecha = argumentos[0] if argumentos else None
    config = Config.desde_entorno()
    cliente = ClienteCoreDb(config.coredb_url, config.servicio_usuario, config.servicio_secreto,
                            timeout=config.timeout_seg, bus_token=config.bus_token)
    try:
        resultado = ejecutar(cliente, fecha)
    finally:
        cliente.cerrar()
    log.info("vencimientos", extra={"contexto": {"resultado": resultado}})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
