import httpx

from TARJETAS.config import settings
from TARJETAS.exceptions import TarjetasError


class CoreClient:
    def __init__(self, base_url: str | None = None, timeout: float | None = None,
                 transport: httpx.BaseTransport | None = None, bus_token: str | None = None):
        token = settings.bus_token if bus_token is None else bus_token
        self._http = httpx.Client(
            base_url=base_url or settings.core_base_url,
            timeout=timeout or settings.core_timeout_seconds,
            transport=transport,
            # Credencial ante el Bus en cada llamada; el Bus no la reenvía a COREDB.
            headers={"X-Bus-Token": token} if token else None,
        )

    def close(self) -> None:
        self._http.close()

    def _request(self, method: str, path: str, *, json: dict | None = None,
                 params: dict | None = None,
                 correlation_id: str | None = None,
                 authorization: str | None = None,
                 sin_cuerpo: bool = False):
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
        if sin_cuerpo:
            return None
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

    def salud(self):
        # Publica en COREDB: responde si COREDB y su base estan disponibles
        return self._request("GET", "/coredb/salud")

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

    def autorizar(self, payload: dict, correlation_id: str | None = None, authorization: str | None = None):
        return self._request("POST", "/coredb/autorizaciones", json=payload,
                             correlation_id=correlation_id, authorization=authorization)

    def ver_autorizacion(self, uuid_autorizacion: str, correlation_id: str | None = None,
                         authorization: str | None = None):
        return self._request("GET", f"/coredb/autorizaciones/{uuid_autorizacion}",
                             correlation_id=correlation_id, authorization=authorization)

    def extornar(self, uuid_autorizacion: str, payload: dict, correlation_id: str | None = None,
                 authorization: str | None = None):
        return self._request("POST", f"/coredb/autorizaciones/{uuid_autorizacion}/extorno", json=payload,
                             correlation_id=correlation_id, authorization=authorization)

    def confirmar_autorizacion(self, uuid_autorizacion: str, payload: dict, correlation_id: str | None = None,
                               authorization: str | None = None):
        return self._request("POST", f"/coredb/autorizaciones/{uuid_autorizacion}/confirmacion", json=payload,
                             correlation_id=correlation_id, authorization=authorization)

    def registrar_credencial(self, id_tarjeta: str, tipo: str, payload: dict,
                             correlation_id: str | None = None, authorization: str | None = None):
        # 204 sin cuerpo
        self._request("PUT", f"/coredb/tarjetas/{id_tarjeta}/credenciales/{tipo}", json=payload,
                      correlation_id=correlation_id, authorization=authorization, sin_cuerpo=True)

    def validar_credencial(self, id_tarjeta: str, tipo: str, payload: dict,
                           correlation_id: str | None = None, authorization: str | None = None):
        return self._request("POST", f"/coredb/tarjetas/{id_tarjeta}/credenciales/{tipo}/validacion",
                             json=payload, correlation_id=correlation_id, authorization=authorization)
