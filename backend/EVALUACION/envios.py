"""CR-INT-03: devuelve a SOL el resultado final de cada evaluación, sin estado propio.

Evaluación no guarda nada: cada ciclo lee de COREDB, con su usuario de servicio, las
solicitudes de los últimos `envio_ventana_dias` días con un resultado final (APROBADO o
RECHAZADO, por la regla o por el analista) y se lo envía a SOL. El `idOperacion` y el cuerpo
salen solo del resultado, así que repetir el envío manda exactamente el mismo mensaje y SOL lo
reconoce sin duplicarlo (`reintento_reconocido`). Un OBSERVADO de la regla no se envía: espera
la decisión del analista (por omisión del equipo, T1, no vuelve a SOL como pedido de corrección).

Sigue el contrato de SOL (Documents/solicitud-credito/CONTRATOS_HTTP_V2.md): POST
/sol/integrations/evaluation-results con su token de resultados, X-Idempotency-Key igual a
idOperacion y X-Correlation-ID igual a idCorrelacion. Sin `EVALUACION_SOL_URL` no hay a quién
entregar y el ciclo no corre; en el producto se entrega a SOL por el Bus.
"""
from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timedelta, timezone

import httpx

from .comun import ErrorEva
from .config import Config
from .coredb import ClienteCoreDb

log = logging.getLogger("evaluacion.envios")

RUTA_RESULTADOS = "/sol/integrations/evaluation-results"
# Espacio de nombres propio para los idOperacion de CR-INT-03 (uuid5).
ESPACIO_CR_INT_03 = uuid.UUID("6f1d3c2a-8b4e-5f70-9a1c-2e3d4b5c6a7f")
ESTADOS_CON_RESULTADO = ("APROBADA", "RECHAZADA", "DESEMBOLSADA")
LIMITE_BANDEJA = 200


def id_operacion(id_evaluacion: str, decision: str) -> str:
    return str(uuid.uuid5(ESPACIO_CR_INT_03, f"CR-INT-03:{id_evaluacion}:{decision}"))


def resultado_para_sol(detalle: dict) -> dict | None:
    """El mensaje CR-INT-03 de una solicitud, o None si su ronda vigente no tiene resultado final."""
    ultima = next((e for e in detalle.get("evaluaciones", []) if e.get("esUltima")), None)
    if ultima is None or ultima["resultado"] not in ("APROBADO", "RECHAZADO"):
        return None
    decision = ultima["resultado"]
    if ultima.get("decision"):
        observaciones = ultima.get("comentario") or f"Decisión del analista: {decision}."
    else:
        observaciones = f"{decision.capitalize()} por la regla {ultima['regla']} (RN-EVA-002-P)."
    operacion = id_operacion(ultima["idEvaluacion"], decision)
    return {"idSolicitud": detalle["idSolicitud"], "versionSolicitud": detalle["versionSolicitud"],
            "idEvaluacion": ultima["idEvaluacion"], "ronda": ultima["ronda"], "idOperacion": operacion,
            "idCorrelacion": operacion, "decision": decision, "observaciones": observaciones}


class DespachadorResultados:
    def __init__(self, config: Config, coredb: ClienteCoreDb, transporte: httpx.BaseTransport | None = None):
        self._config = config
        self._coredb = coredb
        # SOL se alcanza por el Bus (EVALUACION_SOL_URL=http://bus:8018/bus/sol): cada entrega lleva
        # la credencial de Evaluación ante el Bus, que el Bus no reenvía a SOL.
        self._http = httpx.Client(base_url=config.sol_url or "http://sol.invalid", timeout=config.timeout_seg,
                                  transport=transporte, follow_redirects=False, trust_env=False,
                                  headers={"X-Bus-Token": config.bus_token} if config.bus_token else None)

    def cerrar(self) -> None:
        self._http.close()

    @property
    def configurado(self) -> bool:
        return bool(self._config.sol_url and self._config.sol_token_resultados)

    def resultados(self) -> list[dict]:
        """Los mensajes CR-INT-03 de las solicitudes recientes con resultado final."""
        desde = datetime.now(timezone.utc) - timedelta(days=self._config.envio_ventana_dias)
        mensajes = []
        for estado in ESTADOS_CON_RESULTADO:
            _, bandeja = self._coredb.como_servicio(
                "GET", "/coredb/creditos/solicitudes", params={"estado": estado, "limite": LIMITE_BANDEJA})
            for s in bandeja:
                creada = datetime.fromisoformat(s["fechaCreacion"].replace("Z", "+00:00"))
                if (creada if creada.tzinfo else creada.replace(tzinfo=timezone.utc)) < desde:
                    continue
                _, detalle = self._coredb.como_servicio("GET", f"/coredb/creditos/solicitudes/{s['idSolicitud']}")
                mensaje = resultado_para_sol(detalle)
                if mensaje is not None:
                    mensajes.append(mensaje)
        return mensajes

    def ciclo(self) -> int:
        """Envía los resultados recientes. Devuelve cuántos aceptó SOL (nuevos o reconocidos)."""
        if not self.configurado:
            return 0
        return sum(self._entregar(m) for m in self.resultados())

    def _entregar(self, mensaje: dict) -> int:
        try:
            r = self._http.post(RUTA_RESULTADOS, content=json.dumps(mensaje, ensure_ascii=False).encode(),
                                headers={"Authorization": f"Bearer {self._config.sol_token_resultados}",
                                         "Content-Type": "application/json",
                                         "X-Idempotency-Key": mensaje["idOperacion"],
                                         "X-Correlation-ID": mensaje["idCorrelacion"]})
        except httpx.HTTPError as exc:
            log.warning("Resultado %s sin entregar a SOL (%s); se reintenta en el próximo ciclo",
                        mensaje["idOperacion"], type(exc).__name__)
            return 0
        if r.is_success:
            return 1
        # 409: SOL aún no concilia el acuse o ya cerró la solicitud; 5xx: no disponible. El próximo
        # ciclo lo intenta otra vez, mientras la solicitud esté dentro de la ventana.
        log.warning("SOL respondió %s al resultado %s", r.status_code, mensaje["idOperacion"])
        return 0


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
            except ErrorEva as exc:
                log.warning("Ciclo de resultados a SOL sin COREDB: %s", exc.codigo)
            except Exception:  # noqa: BLE001 - un ciclo fallido no debe detener los siguientes
                log.exception("Falló un ciclo de entrega de resultados a SOL")

    def detener(self) -> None:
        self._parar.set()
