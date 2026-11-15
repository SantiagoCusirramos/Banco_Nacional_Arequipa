"""CR-INT-03: entrega a SOL el resultado final de cada evaluación, al menos una vez.

Sigue el contrato de SOL (Documents/solicitud-credito/CONTRATOS_HTTP_V2.md): POST
/sol/integrations/evaluation-results con su token de resultados, X-Idempotency-Key igual a
idOperacion y X-Correlation-ID igual a idCorrelacion. SOL reconoce sin duplicar un mensaje
idéntico repetido, y responde 409 si recibe el resultado antes de conciliar su acuse: entonces
se reintenta. Un envío se reserva unos segundos antes de llamar, así que varios procesos pueden
trabajar a la vez sin enviar lo mismo dos veces en paralelo.

Mientras SOL siga en modo SIMULADO no hay a quién entregar: sin EVALUACION_SOL_URL los
resultados quedan PENDIENTE y se entregan cuando se configure.
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import timedelta

import httpx
from sqlalchemy import text
from sqlalchemy.engine import Engine

from .comun import utc_ahora
from .config import Config
from .servicio import _historial, _leer_json

log = logging.getLogger("evaluacion.envios")

RUTA_RESULTADOS = "/sol/integrations/evaluation-results"


class DespachadorResultados:
    RESERVA_SEG = 60
    ESPERA_MAXIMA_SEG = 300
    MAXIMO_CONFLICTOS = 20

    def __init__(self, engine: Engine, config: Config, transporte: httpx.BaseTransport | None = None):
        self._engine = engine
        self._config = config
        self._http = httpx.Client(base_url=config.sol_url or "http://sol.invalid", timeout=config.timeout_seg,
                                  transport=transporte, follow_redirects=False, trust_env=False)

    def cerrar(self) -> None:
        self._http.close()

    @property
    def configurado(self) -> bool:
        return bool(self._config.sol_url and self._config.sol_token_resultados)

    def ciclo(self, limite: int = 10) -> int:
        """Entrega los resultados que tocan. Devuelve cuántos quedaron ENTREGADO."""
        if not self.configurado:
            return 0
        ahora = utc_ahora()
        with self._engine.begin() as c:
            filas = c.execute(text(
                "SELECT id_operacion, id_evaluacion, contenido, intentos FROM eva_envio "
                "WHERE estado = 'PENDIENTE' AND siguiente_intento <= :ahora ORDER BY creado_en LIMIT :limite "
                "FOR UPDATE SKIP LOCKED"), {"ahora": ahora, "limite": limite}).all()
            for f in filas:
                c.execute(text("UPDATE eva_envio SET siguiente_intento = :hasta WHERE id_operacion = :op"),
                          {"hasta": ahora + timedelta(seconds=self.RESERVA_SEG), "op": f.id_operacion})
        return sum(self._entregar(f) for f in filas)

    def _entregar(self, fila) -> int:
        contenido = _leer_json(fila.contenido)
        intentos = fila.intentos + 1
        try:
            r = self._http.post(RUTA_RESULTADOS, content=json.dumps(contenido, ensure_ascii=False).encode(),
                                headers={"Authorization": f"Bearer {self._config.sol_token_resultados}",
                                         "Content-Type": "application/json",
                                         "X-Idempotency-Key": contenido["idOperacion"],
                                         "X-Correlation-ID": contenido["idCorrelacion"]})
        except httpx.HTTPError as exc:
            self._reprogramar(fila, intentos, f"SIN_RESPUESTA: {type(exc).__name__}")
            return 0
        if r.is_success:
            self._terminar(fila, intentos, "ENTREGADO", None)
            return 1
        if r.status_code in (408, 429) or r.status_code >= 500:
            self._reprogramar(fila, intentos, f"HTTP_{r.status_code}")
        elif r.status_code == 409 and intentos < self.MAXIMO_CONFLICTOS:
            # SOL todavía no concilia el acuse de esta ronda: el contrato pide reintentar.
            self._reprogramar(fila, intentos, "HTTP_409: SOL aún no concilia el acuse")
        else:
            # Credencial o contrato: hace falta revisarlo; se reintenta a mano desde la pantalla.
            self._terminar(fila, intentos, "ERROR", f"HTTP_{r.status_code}")
        return 0

    def _reprogramar(self, fila, intentos: int, error: str) -> None:
        espera = min(10 * 2 ** (intentos - 1), self.ESPERA_MAXIMA_SEG)
        with self._engine.begin() as c:
            c.execute(text("UPDATE eva_envio SET intentos = :intentos, ultimo_error = :error, "
                           "siguiente_intento = :siguiente WHERE id_operacion = :op AND estado = 'PENDIENTE'"),
                      {"intentos": intentos, "error": error[:200],
                       "siguiente": utc_ahora() + timedelta(seconds=espera), "op": fila.id_operacion})
        log.warning("Resultado %s sin entregar a SOL (%s); nuevo intento en %s s", fila.id_operacion, error, espera)

    def _terminar(self, fila, intentos: int, estado: str, error: str | None) -> None:
        ahora = utc_ahora()
        with self._engine.begin() as c:
            c.execute(text("UPDATE eva_envio SET estado = :estado, intentos = :intentos, ultimo_error = :error, "
                           "entregado_en = :entregado WHERE id_operacion = :op AND estado = 'PENDIENTE'"),
                      {"estado": estado, "intentos": intentos, "error": error,
                       "entregado": ahora if estado == "ENTREGADO" else None, "op": fila.id_operacion})
            _historial(c, "RESULTADO_ENTREGADO" if estado == "ENTREGADO" else "RESULTADO_CON_ERROR", "SISTEMA",
                       evaluacion=fila.id_evaluacion,
                       detalle={"idOperacion": fila.id_operacion, "intentos": intentos, "error": error})


class Trabajador(threading.Thread):
    """Ejecuta el despachador cada `intervalo` segundos dentro del proceso de la API."""

    def __init__(self, despachador: DespachadorResultados, intervalo: float):
        super().__init__(name="evaluacion-envios", daemon=True)
        self._despachador = despachador
        self._intervalo = intervalo
        self._parar = threading.Event()

    def run(self) -> None:
        while not self._parar.wait(self._intervalo):
            try:
                self._despachador.ciclo()
            except Exception:  # noqa: BLE001 - un ciclo fallido no debe detener los siguientes
                log.exception("Falló un ciclo de entrega de resultados a SOL")

    def detener(self) -> None:
        self._parar.set()
