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
                 afecta_saldo: bool = False):
        headers = {}
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key
        try:
            resp = self._http.request(method, path, json=json, headers=headers)
        except httpx.ConnectError:
            raise CuentasError("CORE_NO_DISPONIBLE", "No se pudo conectar con CORE", 503)
        except httpx.HTTPError:
            # la peticion pudo llegar a CORE, no se sabe si se aplico
            if afecta_saldo:
                raise CuentasError(
                    "OPERACION_NO_CONFIRMADA",
                    "CORE no respondio, la operacion no esta confirmada. Reintentar con la misma llave de idempotencia",
                    504,
                )
            raise CuentasError("CORE_TIMEOUT", "CORE no respondio a tiempo", 504)
        if resp.status_code >= 400:
            raise self._error_de_core(resp)
        return resp.json()

    @staticmethod
    def _error_de_core(resp: httpx.Response) -> CuentasError:
        try:
            error = resp.json()["error"]
            return CuentasError(error["code"], error["message"], resp.status_code,
                                error.get("details"))
        except (ValueError, KeyError, TypeError):
            return CuentasError("CORE_ERROR", resp.text[:200], 502)

    def crear_cuenta(self, payload: dict, correlation_id: str | None = None):
        return self._request("POST", "/core/cuentas", json=payload,
                             correlation_id=correlation_id)

    def ver_cuenta(self, num_cuenta: str, correlation_id: str | None = None):
        return self._request("GET", f"/core/cuentas/{num_cuenta}",
                             correlation_id=correlation_id)

    def cuentas_del_cliente(self, id_cliente: str, correlation_id: str | None = None):
        return self._request("GET", f"/core/cuentas/cliente/{id_cliente}",
                             correlation_id=correlation_id)

    def registrar_movimiento(self, payload: dict, idempotency_key: str,
                             correlation_id: str | None = None):
        return self._request("POST", "/core/movimientos", json=payload,
                             correlation_id=correlation_id,
                             idempotency_key=idempotency_key, afecta_saldo=True)

    def transferir(self, payload: dict, idempotency_key: str,
                   correlation_id: str | None = None):
        return self._request("POST", "/core/movimientos/transferencias", json=payload,
                             correlation_id=correlation_id,
                             idempotency_key=idempotency_key, afecta_saldo=True)
