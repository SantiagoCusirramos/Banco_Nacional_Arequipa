"""Registros en JSON con correlation_id, para reconstruir una operacion desde la traza del Bus (RNF-07)."""
import json
import logging
from datetime import datetime, timezone

from .correlacion import correlacion_actual


class FormatoJson(logging.Formatter):
    def format(self, registro: logging.LogRecord) -> str:
        datos = {
            "ts": datetime.fromtimestamp(registro.created, timezone.utc).isoformat(timespec="milliseconds"),
            "nivel": registro.levelname,
            "origen": registro.name,
            "mensaje": registro.getMessage(),
            "correlation_id": correlacion_actual.get() or None,
        }
        if registro.exc_info:
            datos["excepcion"] = self.formatException(registro.exc_info)
        return json.dumps(datos, ensure_ascii=False)


def configurar_registros(nivel: int = logging.INFO) -> None:
    manejador = logging.StreamHandler()
    manejador.setFormatter(FormatoJson())
    raiz = logging.getLogger()
    raiz.handlers[:] = [manejador]
    raiz.setLevel(nivel)
    logging.getLogger("httpx").setLevel(logging.WARNING)
