import httpx

from CUENTAS.config import settings
from CUENTAS.exceptions import CuentasError


class CoreClient:
    def __init__(self, base_url: str | None = None, timeout: float | None = None,
                 transport: httpx.BaseTransport | None = None):
        self._http = httpx.Client(
            base_url=base_url or settings.core_base_url,
            timeout=timeout or settings.core_timeout_seconds,
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    def _request(self, method: str, path: str, *, json: dict | None = None,
                 correlation_id: str | None = None,
                 idempotency_key: str | None = None,
                 authorization: str | None = None,
                 afecta_saldo: bool = False):
        headers = {}
        if authorization:
            headers["Authorization"] = authorization
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key
        try:
            resp = self._http.request(method, path, json=json, headers=headers)
        except httpx.ConnectError:
            raise CuentasError("ERR-COR-NO-DISPONIBLE", "No se pudo conectar con COREDB (puerto 8012)", 503)
        except httpx.HTTPError:
            if afecta_saldo:
                raise CuentasError(
                    "ERR-CTA-OPERACION-NO-CONFIRMADA",
                    "COREDB no respondió, la operación no está confirmada. Reintentar con la misma llave de idempotencia",
                    504,
                )
            raise CuentasError("ERR-CTA-TIMEOUT-CORE", "COREDB no respondió a tiempo", 504)
        if resp.status_code >= 400:
            raise self._error_de_core(resp)
        return resp.json()

    @staticmethod
    def _error_de_core(resp: httpx.Response) -> CuentasError:
        try:
            cuerpo = resp.json()
        except ValueError:
            return CuentasError("ERR-COR-RESPUESTA-INVALIDA", resp.text[:200], 502)
        if isinstance(cuerpo, dict) and "error" in cuerpo:
            error = cuerpo["error"]
            return CuentasError(error.get("code", "DESCONOCIDO"), error.get("message", ""),
                                resp.status_code, error.get("details"))
        if resp.status_code == 422:
            return CuentasError("ERR-COR-VALIDACION-ESQUEMA", "COREDB rechazó el formato de la solicitud",
                                400, {"detail": cuerpo.get("detail") if isinstance(cuerpo, dict) else None})
        return CuentasError("ERR-COR-RESPUESTA-INVALIDA", "Respuesta inesperada de COREDB", 502)

    def crear_cuenta(self, payload: dict, correlation_id: str | None = None,
                     authorization: str | None = None):
        return self._request("POST", "/coredb/cuentas", json=payload,
                             correlation_id=correlation_id, authorization=authorization)

    def ver_cuenta(self, num_cuenta: str, correlation_id: str | None = None,
                   authorization: str | None = None):
        return self._request("GET", f"/coredb/cuentas/{num_cuenta}",
                             correlation_id=correlation_id, authorization=authorization)

    def registrar_movimiento(self, payload: dict, idempotency_key: str,
                             correlation_id: str | None = None, authorization: str | None = None):
        return self._request("POST", "/coredb/movimientos", json=payload,
                             correlation_id=correlation_id, idempotency_key=idempotency_key,
                             authorization=authorization, afecta_saldo=True)

    def transferir(self, payload: dict, idempotency_key: str,
                   correlation_id: str | None = None, authorization: str | None = None):
        return self._request("POST", "/coredb/movimientos/transferencias", json=payload,
                             correlation_id=correlation_id, idempotency_key=idempotency_key,
                             authorization=authorization, afecta_saldo=True)

    def listar_movimientos(self, num_cuenta: str, correlation_id: str | None = None,
                           authorization: str | None = None):
        return self._request("GET", f"/coredb/movimientos/cuenta/{num_cuenta}",
                             correlation_id=correlation_id, authorization=authorization)

    def ver_movimiento(self, uuid_transaccion: str, correlation_id: str | None = None,
                       authorization: str | None = None):
        return self._request("GET", f"/coredb/movimientos/{uuid_transaccion}",
                             correlation_id=correlation_id, authorization=authorization)
