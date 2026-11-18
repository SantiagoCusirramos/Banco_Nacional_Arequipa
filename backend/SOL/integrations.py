"""Clientes HTTP de SOL, todos por el Bus de Servicios. SOL no tiene base propia.

- COREDB: el borrador, la bandeja, el detalle y la bitácora. Lo que hace una persona va con el
  token de esa persona (la auditoría la registra a ella); lo que hace SOL, con su usuario de
  servicio (`svc-sol`).
- CAPTACION (CR-INT-01): referencias de clientes, con el token de SOL ante Captación.
- EVALUACION (CR-INT-02): recibe el expediente, con el token de SOL ante Evaluación.

Cada petición lleva además la credencial de SOL ante el Bus (X-Bus-Token). Nunca se usa un
simulador como respaldo ante una falla, y los errores no repiten URLs, cuerpos remotos ni
secretos.
"""
import threading
import time
from datetime import date
from urllib.parse import quote

import httpx
from fastapi import HTTPException

from .clock import business_today

CLIENT_FIELDS = {
    "id_cliente", "cod_tipo_documento", "numero_documento", "nombres",
    "apellido_paterno", "apellido_materno", "estado_cliente", "id_caso",
    "id_verificacion", "fecha_verificacion", "vigente_hasta",
    "estado_habilitante", "version_contrato", "simulado",
}
CAP_SEARCH_PATH = "/cap/references/search"
CAP_REFERENCE_PATH = "/cap/references/{idCliente}"
EVA_SEND_PATH = "/eva/applications"
MARGEN_TOKEN_SEGUNDOS = 60


class IntegrationError(Exception):
    """La dependencia no respondió o respondió algo que no cumple el contrato."""

    def __init__(self, code="DEPENDENCIA_NO_DISPONIBLE", permanent=False):
        self.code, self.permanent = code, permanent
        super().__init__(code)


class RemoteRejection(Exception):
    """La dependencia respondió con un rechazo de negocio (4xx con su código)."""

    def __init__(self, status, code, message=""):
        self.status, self.code, self.message = status, code, message
        super().__init__(code)


class Integrations:
    def __init__(self, settings, transport=None):
        self.settings = settings
        if hasattr(settings, "validate"):
            settings.validate()
        bus_token = getattr(settings, "bus_token", "")
        # Sin reintentos ocultos del transporte: los controlamos explícitamente.
        self._http = httpx.Client(transport=transport, follow_redirects=False, trust_env=False,
                                  headers={"X-Bus-Token": bus_token} if bus_token else None)
        self._service_token = None
        self._lock = threading.Lock()

    def close(self):
        self._http.close()

    # ------------------------------------------------------------------ transporte
    def _send(self, method, base, path, token, correlation, *, payload=None, params=None, operation=None):
        # Una ruta nunca puede elegir otro host ni llevar el token a una URL absoluta.
        if not path.startswith("/") or path.startswith("//") or "\\" in path or "://" in path:
            raise IntegrationError("RUTA_PROVEEDOR_INVALIDA", permanent=True)
        headers = {"Authorization": "Bearer " + token, "X-Correlation-ID": correlation}
        if operation:
            headers["X-Idempotency-Key"] = operation
        try:
            return self._http.request(method, base + path, headers=headers, json=payload, params=params,
                                      timeout=self.settings.http_timeout)
        except httpx.TransportError:
            raise IntegrationError() from None

    @staticmethod
    def _json(response):
        try:
            data = response.json()
        except ValueError:
            raise IntegrationError("RESPUESTA_INVALIDA", permanent=True) from None
        if data is None:
            raise IntegrationError("RESPUESTA_INVALIDA", permanent=True)
        return data

    def _read(self, method, base, path, token, correlation, *, payload=None, allow_missing=False):
        """Una consulta sin efectos: se reintenta. La búsqueda es POST solo para que el texto
        buscado (un documento) no viaje en la URL."""
        for attempt in range(self.settings.max_retries + 1):
            try:
                response = self._send(method, base, path, token, correlation, payload=payload)
                if response.status_code == 404 and allow_missing:
                    return None
                if response.status_code in {408, 429, 500, 502, 503, 504}:
                    raise IntegrationError()
                if not response.is_success:
                    raise IntegrationError("RECHAZO_CONTRATO", permanent=True)
                return self._json(response)
            except IntegrationError as exc:
                if exc.permanent or attempt == self.settings.max_retries:
                    raise

    # ------------------------------------------------------------------ CAPTACION (CR-INT-01)
    def reference(self, identifier, correlation):
        """La referencia vigente de un cliente, con las reglas de SOL (ACTIVO, HABILITADO, vigente)."""
        path = CAP_REFERENCE_PATH.replace("{idCliente}", quote(identifier, safe=""))
        try:
            data = self._read("GET", self.settings.cap_url, path, self.settings.cap_token, correlation,
                              allow_missing=True)
        except IntegrationError:
            raise HTTPException(503, "Captación no disponible o contrato incompatible.") from None
        if data is None:
            raise HTTPException(422, "Referencia de Captación no encontrada.")
        return validate_reference(data, identifier)

    def identity(self, identifier, correlation):
        """La identidad para mostrar un expediente ya guardado: sin exigir que siga habilitado.
        Si Captación no responde, solo el código del cliente."""
        path = CAP_REFERENCE_PATH.replace("{idCliente}", quote(identifier, safe=""))
        try:
            data = self._read("GET", self.settings.cap_url, path, self.settings.cap_token, correlation,
                              allow_missing=True)
            if data is not None:
                return normalize_reference(data)
        except (IntegrationError, ValueError, TypeError, KeyError):
            pass
        return unavailable_identity(identifier)

    def clients(self, search, correlation):
        # Una búsqueda acotada; no se descarga todo el maestro de clientes.
        try:
            data = self._read("POST", self.settings.cap_url, CAP_SEARCH_PATH, self.settings.cap_token, correlation,
                              payload={"search": search, "limit": 50})
            if not isinstance(data, list) or len(data) > 50:
                raise IntegrationError("RESPUESTA_INVALIDA", True)
            return [normalize_reference(r) for r in data]
        except (IntegrationError, KeyError, TypeError, ValueError):
            raise HTTPException(503, "Búsqueda de Captación no disponible o contrato incompatible.") from None

    # ------------------------------------------------------------------ EVALUACION (CR-INT-02)
    def deliver(self, envelope):
        """Envía el expediente. COREDB reconoce la misma versión con el mismo contenido, así que
        reenviar tras un timeout es seguro (devuelve el mismo acuse)."""
        response = self._send("POST", self.settings.eva_url, EVA_SEND_PATH, self.settings.eva_token,
                              envelope["idCorrelacion"], payload=envelope, operation=envelope["idOperacion"])
        if response.status_code in {408, 429, 500, 502, 503, 504}:
            raise IntegrationError()
        if not response.is_success:
            raise RemoteRejection(response.status_code, _error_code(response))
        return validate_receipt(self._json(response), envelope)

    # ------------------------------------------------------------------ COREDB
    def coredb(self, method, path, token, correlation, *, payload=None, params=None):
        """(estado, cuerpo) de COREDB. Un rechazo (4xx) es RemoteRejection con su código."""
        response = self._send(method, self.settings.coredb_url, path, token, correlation,
                              payload=payload, params=params)
        if response.status_code >= 500:
            raise IntegrationError()
        if not response.is_success:
            raise RemoteRejection(response.status_code, _error_code(response), _error_message(response))
        return response.status_code, self._json(response)

    def login(self, username, password, correlation):
        try:
            response = self._http.post(self.settings.coredb_url + "/coredb/auth/login",
                                       json={"username": username, "password": password},
                                       headers={"X-Correlation-ID": correlation}, timeout=self.settings.http_timeout)
        except httpx.TransportError:
            raise IntegrationError() from None
        if response.status_code >= 500:
            raise IntegrationError()
        if not response.is_success:
            raise RemoteRejection(response.status_code, _error_code(response))
        return self._json(response)

    def service_token(self, correlation, renew=False):
        with self._lock:
            if not renew and self._service_token and self._service_token[1] > time.monotonic():
                return self._service_token[0]
            try:
                data = self.login(self.settings.coredb_usuario, self.settings.coredb_secreto, correlation)
            except RemoteRejection:
                raise IntegrationError("SERVICIO_SIN_SESION", permanent=True) from None
            expires = time.monotonic() + max(0, int(data.get("expires_in", 0)) - MARGEN_TOKEN_SEGUNDOS)
            self._service_token = (data["access_token"], expires)
            return data["access_token"]

    def coredb_service(self, method, path, correlation, **options):
        try:
            return self.coredb(method, path, self.service_token(correlation), correlation, **options)
        except RemoteRejection as exc:
            if exc.status != 401:
                raise
            return self.coredb(method, path, self.service_token(correlation, renew=True), correlation, **options)

    def audit(self, event, correlation):
        """Registra un evento de SOL en la bitácora de COREDB. (acuse, repetido)."""
        try:
            status, data = self.coredb_service("POST", "/coredb/auditoria/eventos", correlation, payload=event)
        except RemoteRejection as exc:
            raise IntegrationError(exc.code, permanent=True) from None
        if (not isinstance(data, dict) or data.get("idEvento") != event["idEvento"]
                or data.get("confirmado") is not True or not isinstance(data.get("acuse"), str)):
            raise IntegrationError("ACUSE_AUDITORIA_INVALIDO", True)
        return data["acuse"], status == 200

    def ready(self, correlation):
        try:
            return self._http.get(self.settings.coredb_url + "/coredb/salud", headers={"X-Correlation-ID": correlation},
                                  timeout=self.settings.http_timeout).status_code == 200
        except httpx.TransportError:
            return False


def _error_code(response):
    try:
        error = response.json().get("error")
        return str(error.get("code")) if isinstance(error, dict) else "RECHAZO"
    except (ValueError, AttributeError):
        return "RECHAZO"


def _error_message(response):
    try:
        error = response.json().get("error")
        return str(error.get("message", ""))[:300] if isinstance(error, dict) else ""
    except (ValueError, AttributeError):
        return ""


def project_identity(data):
    """Proyección mínima; ausencia de segundo apellido se representa sin inventarlo."""
    result = {key: value for key, value in data.items() if key in CLIENT_FIELDS}
    if result.get("apellido_materno") is None:
        result["apellido_materno"] = ""
    return result


def unavailable_identity(identifier):
    return {"id_cliente": identifier, "numero_documento": "", "nombres": identifier, "apellido_paterno": "",
            "apellido_materno": "", "estado_cliente": "NO_DISPONIBLE", "id_caso": "", "id_verificacion": "",
            "fecha_verificacion": "", "vigente_hasta": "", "estado_habilitante": "NO_DISPONIBLE",
            "version_contrato": ""}


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
    # Nunca conservar campos adicionales del maestro que SOL no necesita.
    return project_identity(data)


def validate_reference(data, identifier):
    try:
        data = normalize_reference(data)
    except (ValueError, TypeError):
        raise HTTPException(503, "El contrato de referencia de Captación es inválido.") from None
    if data["id_cliente"] != identifier:
        raise HTTPException(503, "Captación devolvió una referencia diferente.")
    if (data["estado_cliente"] != "ACTIVO" or data["estado_habilitante"] != "HABILITADO"
            or not date.fromisoformat(data["fecha_verificacion"]) <= business_today()
            <= date.fromisoformat(data["vigente_hasta"])):
        raise HTTPException(422, "Captación no habilita esta solicitud o su verificación ha vencido.")
    return data


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
