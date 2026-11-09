"""Logs estructurados sin cuerpos, claves, tokens ni datos del cliente."""
import json
import logging
import math
import re
from collections import defaultdict, deque
from threading import Lock
from .clock import utc_now

LOG = logging.getLogger("sol")
if not LOG.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    LOG.addHandler(handler)
LOG.setLevel(logging.INFO)
SAFE_ID = re.compile(r"[A-Za-z0-9._:-]{1,100}\Z")


def valid_id(value):
    return bool(value and SAFE_ID.fullmatch(value))


def log(action, correlation, operation=None, **fields):
    LOG.info(json.dumps({"fecha": utc_now().isoformat(), "accion": action,
                         "idCorrelacion": correlation, "idOperacion": operation,
                         **fields}, ensure_ascii=False))


class Metrics:
    """Ventana de 10 000 muestras por operación/proceso. No fija un SLA."""
    def __init__(self):
        self.lock = Lock()
        self.samples = defaultdict(lambda: deque(maxlen=10000))
        self.errors = defaultdict(int)

    def observe(self, route, duration, status):
        with self.lock:
            self.samples[route].append(duration)
            self.errors[route] += int(status >= 500)

    def snapshot(self):
        with self.lock:
            return {"alcance": "Ventana en memoria por proceso; se reinicia con el servicio.",
                    "unidad": "milisegundos", "operaciones": [
                        {"operacion": key, "muestras": len(values),
                         "p95_ms": round(sorted(values)[math.ceil(.95 * len(values))-1], 3),
                         "errores_5xx_acumulados": self.errors[key]}
                        for key, values in sorted(self.samples.items()) if values]}
