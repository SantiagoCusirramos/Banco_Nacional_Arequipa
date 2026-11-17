"""Adaptadores HTTP vía Bus. Los esquemas v2 son propuesta para homologación.

Las rutas y secretos se configuran fuera del código. Nunca se usa el simulador
como respaldo ante una falla real. Las escrituras usan identificadores estables.
"""
from datetime import date
from time import monotonic
from urllib.parse import quote
from uuid import uuid4
import httpx
from fastapi import HTTPException
from .clock import business_today
from .models import ClientReference
from .settings import provider_connection

CLIENT_FIELDS = {
    "id_cliente", "cod_tipo_documento", "numero_documento", "nombres",
    "apellido_paterno", "apellido_materno", "estado_cliente", "id_caso",
    "id_verificacion", "fecha_verificacion", "vigente_hasta",
    "estado_habilitante", "version_contrato", "simulado",
}


class IntegrationError(Exception):
    def __init__(self, code="DEPENDENCIA_NO_DISPONIBLE", permanent=False):
        self.code, self.permanent = code, permanent
        super().__init__(code)


class Integrations:
    def __init__(self, settings, transport=None):
        self.settings = settings
        if hasattr(settings, "validate"):
            settings.validate()
        # Sin reintentos ocultos del transporte: los controlamos explícitamente.
        self._connections = {"bus": (settings.bus_base_url, settings.bus_token)}
        self._connections.update({p: provider_connection(settings, p) for p in ("cap", "eva", "audit")})
        clients = {}
        self._clients = {}
        for provider, connection in self._connections.items():
            if connection not in clients:
                url, token = connection
                clients[connection] = httpx.Client(
                    base_url=url or "http://simulador.invalid",
                    headers={"Authorization": "Bearer " + token},
                    transport=transport, follow_redirects=False, trust_env=False,
                )
            self._clients[provider] = clients[connection]
        # Compatibilidad del cliente y request/read públicos para el Bus legado.
        self.client = self._clients["bus"]

    def close(self):
        for client in set(self._clients.values()):
            client.close()

    def request(self, method, path, correlation, operation=None, payload=None,
                params=None, deadline=None, allow_missing=False, provider="bus"):
        remaining = (deadline or monotonic() + self.settings.request_budget) - monotonic()
        if remaining <= 0:
            raise IntegrationError("PRESUPUESTO_AGOTADO")
        if provider not in self._clients or not all(self._connections[provider]):
            raise IntegrationError("PROVEEDOR_NO_CONFIGURADO", permanent=True)
        # Una ruta nunca puede elegir otro host ni enviar el token a una URL absoluta.
        if not path.startswith("/") or path.startswith("//") or "\\" in path or "://" in path:
            raise IntegrationError("RUTA_PROVEEDOR_INVALIDA", permanent=True)
        headers = {"X-Correlation-ID": correlation}
        if operation:
            headers["X-Idempotency-Key"] = operation
        try:
            response = self._clients[provider].request(
                method, path, headers=headers, json=payload, params=params,
                timeout=min(self.settings.http_timeout, remaining),
            )
        except httpx.TransportError:
            raise IntegrationError() from None
        if response.status_code == 404 and allow_missing:
            return None
        if response.status_code in {408, 429, 500, 502, 503, 504}:
            raise IntegrationError()
        if not response.is_success:
            # No devolver URLs, cuerpo remoto o secretos en errores/logs.
            raise IntegrationError("RECHAZO_CONTRATO_BUS", permanent=True)
        try:
            data = response.json()
        except ValueError:
            raise IntegrationError("RESPUESTA_BUS_INVALIDA", permanent=True) from None
        # Solo un 404 explícito significa ausencia. JSON null no es un acuse
        # ni una referencia válidos y no debe confundirse con ese resultado.
        if data is None:
            raise IntegrationError("RESPUESTA_BUS_INVALIDA", permanent=True)
        return data

    def read(self, path, correlation, params=None, deadline=None, allow_missing=False, provider="bus"):
        deadline = deadline or monotonic() + self.settings.request_budget
        for attempt in range(self.settings.max_retries + 1):
            try:
                return self.request("GET", path, correlation, params=params,
                                    deadline=deadline, allow_missing=allow_missing, provider=provider)
            except IntegrationError as exc:
                if exc.permanent or attempt == self.settings.max_retries:
                    raise

    def reference(self, identifier, correlation):
        path = self.settings.cap_reference_path.replace("{idCliente}", quote(identifier, safe=""))
        try:
            data = self.read(path, correlation, allow_missing=True, provider="cap")
        except IntegrationError:
            raise HTTPException(503, "Captación no disponible o contrato incompatible.") from None
        if data is None:
            raise HTTPException(422, "Referencia de Captación no encontrada.")
        return validate_reference(data, identifier)

    def clients(self, search, correlation):
        # Una búsqueda acotada; no se descarga todo el maestro de Clientes.
        try:
            data = self.read(self.settings.cap_search_path, correlation,
                             params={"search": search, "limit": 50}, provider="cap")
            if not isinstance(data, list) or len(data) > 50:
                raise IntegrationError("RESPUESTA_BUS_INVALIDA", True)
            return [normalize_reference(r) for r in data]
        except (IntegrationError, KeyError, TypeError, ValueError):
            raise HTTPException(503, "Búsqueda de Captación no disponible o contrato incompatible.") from None

    def deliver(self, envelope):
        """Consultar por idOperacion ANTES de cada POST, incluso tras un timeout.

        Un 404 significa 'no recibido' según el contrato propuesto. Si consultar
        falla, no se repite el POST a ciegas. El receptor debe deduplicar la clave.
        """
        if self.settings.mode == "SIMULADO":
            return {"idSolicitud": envelope["idSolicitud"],
                    "versionSolicitud": envelope["versionSolicitud"],
                    "idOperacion": envelope["idOperacion"],
                    "idEvaluacion": "EVA-DEMO-" + str(uuid4())[:12],
                    "ronda": envelope["versionSolicitud"],
                    "acuse": "EVA-DEMO-" + str(uuid4())[:12]}
        deadline = monotonic() + self.settings.request_budget
        key, trace = envelope["idOperacion"], envelope["idCorrelacion"]
        path = self.settings.eva_status_path.replace("{idOperacion}", quote(key, safe=""))
        last = IntegrationError()
        for attempt in range(self.settings.max_retries + 1):
            try:
                received = self.request("GET", path, trace, deadline=deadline, allow_missing=True, provider="eva")
                if received is not None:
                    return validate_receipt(received, envelope)
                receipt = self.request("POST", self.settings.eva_send_path, trace,
                                       operation=key, payload=envelope, deadline=deadline, provider="eva")
                return validate_receipt(receipt, envelope)
            except IntegrationError as exc:
                last = exc
                if exc.permanent:
                    raise
        raise last

    def audit(self, payload):
        if self.settings.mode == "SIMULADO":
            return "AUD-DEMO-" + payload["idEvento"]
        deadline = monotonic() + self.settings.request_budget
        for attempt in range(self.settings.max_retries + 1):
            try:
                data = self.request("POST", self.settings.audit_path,
                                    payload["idCorrelacion"], payload["idEvento"],
                                    payload, deadline=deadline, provider="audit")
                if (not isinstance(data, dict) or data.get("idEvento") != payload["idEvento"]
                        or data.get("confirmado") is not True
                        or not isinstance(data.get("acuse"), str) or not 1 <= len(data["acuse"]) <= 80
                        or not data["acuse"].strip()):
                    raise IntegrationError("ACUSE_AUDITORIA_INVALIDO", True)
                return data["acuse"]
            except IntegrationError as exc:
                if exc.permanent or attempt == self.settings.max_retries:
                    raise


def project_identity(data):
    """Proyección mínima; ausencia de segundo apellido se representa sin inventarlo."""
    result = {key: value for key, value in data.items() if key in CLIENT_FIELDS}
    if result.get("apellido_materno") is None:
        result["apellido_materno"] = ""
    return result


def normalize_reference(data):
    if not isinstance(data, dict):
        raise ValueError("Referencia inválida")
    required = CLIENT_FIELDS - {"simulado", "cod_tipo_documento", "apellido_materno"}
    if any(not isinstance(data.get(k), str) or not data[k].strip() for k in required):
        raise ValueError("Campos de Captación incompletos")
    if "cod_tipo_documento" in data and (
            not isinstance(data["cod_tipo_documento"], str) or not data["cod_tipo_documento"].strip()):
        raise ValueError("Tipo de documento de Captación inválido")
    if "simulado" in data and type(data["simulado"]) is not bool:
        raise ValueError("Indicador de simulación inválido")
    if data.get("apellido_materno") is not None and not isinstance(data["apellido_materno"], str):
        raise ValueError("Apellido materno de Captación inválido")
    if len(data["id_cliente"]) > 36 or len(data["numero_documento"]) > 20:
        raise ValueError("Identificador de Captación inválido")
    verified, expires = date.fromisoformat(data["fecha_verificacion"]), date.fromisoformat(data["vigente_hasta"])
    if verified.isoformat() != data["fecha_verificacion"] or expires.isoformat() != data["vigente_hasta"]:
        raise ValueError("Captación requiere fechas YYYY-MM-DD")
    # Nunca almacenar campos adicionales del maestro que SOL no necesita.
    return project_identity(data)


def validate_reference(data, identifier):
    try:
        data = normalize_reference(data)
    except (ValueError, TypeError):
        raise HTTPException(503, "El contrato de referencia de Captación es inválido.") from None
    if data["id_cliente"] != identifier:
        raise HTTPException(503, "Captación devolvió una referencia diferente.")
    if (data["estado_cliente"] != "ACTIVO" or data["estado_habilitante"] != "HABILITADO"
            or not date.fromisoformat(data["fecha_verificacion"]) <= business_today() <= date.fromisoformat(data["vigente_hasta"])):
        raise HTTPException(422, "Captación no habilita esta solicitud o su verificación ha vencido.")
    return data


def captacion_reference(db, identifier):
    integration = db.info.get("integrations")
    trace = db.info.get("correlation", str(uuid4()))
    if db.info.get("integration_mode") == "REAL" and (
            integration is None or integration.settings.mode != "REAL"):
        raise HTTPException(503, "El adaptador de Captación REAL no está configurado.")
    if integration and integration.settings.mode == "REAL":
        data = integration.reference(identifier, trace)
        ref = db.get(ClientReference, identifier)
        if ref:
            ref.snapshot, ref.document = data, data["numero_documento"]
        else:
            db.add(ClientReference(id=identifier, document=data["numero_documento"], snapshot=data))
            db.flush()
        return data
    ref = db.get(ClientReference, identifier)
    if not ref:
        raise HTTPException(422, "No se encontró la referencia del cliente en Captación simulada.")
    return validate_reference(ref.snapshot, identifier)


def guarantor_reference(db, identifier):
    """Borde de identidad RF008: solo referencia local explícitamente simulada.

    No reutiliza CR-INT-01 como verificación institucional de un fiador. El
    contrato y el adaptador REAL deben homologarse antes de habilitarlo.
    """
    if db.info.get("integration_mode") == "REAL":
        raise HTTPException(422, "La referencia institucional de fiadores requiere homologar su contrato; no se usan datos simulados en REAL.")
    ref = db.get(ClientReference, identifier)
    if not ref or ref.snapshot.get("estado_cliente") != "ACTIVO":
        raise HTTPException(422, "El fiador requiere una referencia de identidad activa.")
    return {
        "id_cliente": identifier,
        "identidad": project_identity(ref.snapshot),
        "validacion": "SIMULADA",
    }


def validate_receipt(data, envelope):
    if (not isinstance(data, dict)
            or type(data.get("versionSolicitud")) is not int
            or any(data.get(k) != envelope[k] for k in ["idSolicitud", "versionSolicitud", "idOperacion"])
            or not isinstance(data.get("idEvaluacion"), str) or not 1 <= len(data["idEvaluacion"]) <= 80
            or not data["idEvaluacion"].strip() or data["idEvaluacion"] != data["idEvaluacion"].strip()
            or type(data.get("ronda")) is not int or data["ronda"] < 1
            or not isinstance(data.get("acuse"), str) or not 1 <= len(data["acuse"]) <= 60
            or not data["acuse"].strip()):
        raise IntegrationError("ACUSE_EVALUACION_INVALIDO", True)
    return data


def evaluation_envelope(application, version, operation, correlation, mode="SIMULADO"):
    return {"versionContrato": "CR-INT-02-PROPUESTA-v2",
            "idSolicitud": application.id, "versionSolicitud": version.number,
            "idOperacion": operation, "idCorrelacion": correlation,
            "expediente": version.snapshot, "simulado": mode == "SIMULADO"}
