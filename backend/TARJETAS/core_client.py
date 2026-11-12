import httpx

from TARJETAS.config import settings
from TARJETAS.exceptions import TarjetasError


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
                 params: dict | None = None,
                 correlation_id: str | None = None,
                 authorization: str | None = None):
        headers = {}
        if authorization:
            headers["Authorization"] = authorization
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id
        try:
            resp = self._http.request(method, path, json=json, params=params, headers=headers)
        except httpx.ConnectError:
            raise TarjetasError("ERR-COR-NO-DISPONIBLE", "No se pudo conectar con COREDB (puerto 8012)", 503)
        except httpx.HTTPError:
            raise TarjetasError("ERR-TAR-TIMEOUT-CORE", "COREDB no respondió a tiempo", 504)
        if resp.status_code >= 400:
            raise self._error_de_core(resp)
        return resp.json()

    @staticmethod
    def _error_de_core(resp: httpx.Response) -> TarjetasError:
        try:
            cuerpo = resp.json()
        except ValueError:
            return TarjetasError("ERR-COR-RESPUESTA-INVALIDA", resp.text[:200], 502)
        if isinstance(cuerpo, dict) and "error" in cuerpo:
            error = cuerpo["error"]
            return TarjetasError(error.get("code", "DESCONOCIDO"), error.get("message", ""),
                                 resp.status_code, error.get("details"))
        if resp.status_code == 422:
            return TarjetasError("ERR-COR-VALIDACION-ESQUEMA", "COREDB rechazó el formato de la solicitud",
                                 400, {"detail": cuerpo.get("detail") if isinstance(cuerpo, dict) else None})
        return TarjetasError("ERR-COR-RESPUESTA-INVALIDA", "Respuesta inesperada de COREDB", 502)

    def tarjetas_de_cliente(self, cod_cliente: str, correlation_id: str | None = None,
                            authorization: str | None = None):
        return self._request("GET", "/coredb/tarjetas", params={"cod_cliente": cod_cliente},
                             correlation_id=correlation_id, authorization=authorization)

    def ver_tarjeta(self, id_tarjeta: str, correlation_id: str | None = None,
                    authorization: str | None = None):
        return self._request("GET", f"/coredb/tarjetas/{id_tarjeta}",
                             correlation_id=correlation_id, authorization=authorization)

    def emitir_tarjeta(self, payload: dict, correlation_id: str | None = None,
                       authorization: str | None = None):
        return self._request("POST", "/coredb/tarjetas", json=payload,
                             correlation_id=correlation_id, authorization=authorization)

    def cambiar_estado(self, id_tarjeta: str, payload: dict, correlation_id: str | None = None,
                       authorization: str | None = None):
        return self._request("POST", f"/coredb/tarjetas/{id_tarjeta}/estado", json=payload,
                             correlation_id=correlation_id, authorization=authorization)
