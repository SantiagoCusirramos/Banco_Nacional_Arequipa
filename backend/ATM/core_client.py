"""Cliente HTTP para llamar a TARJETAS y CUENTAS a través del Bus de Servicios."""

import httpx
from ATM.config import settings
from ATM.exceptions import AtmError


class CoreClient:
    def __init__(self, base_url: str | None = None, timeout: float | None = None,
                 transport: httpx.BaseTransport | None = None, bus_token: str | None = None):
        token = bus_token if bus_token is not None else settings.bus_token
        self._http = httpx.Client(
            base_url=base_url or settings.bus_base_url,
            timeout=timeout or settings.core_timeout_seconds,
            transport=transport,
            # Credencial ante el Bus en cada llamada; el Bus no la reenvía a TARJETAS/CUENTAS.
            headers={"X-Bus-Token": token} if token else None,
        )

    def close(self) -> None:
        self._http.close()

    def _request(self, method: str, path: str, *, json: dict | None = None,
                 params: dict | None = None,
                 correlation_id: str | None = None,
                 authorization: str | None = None,
                 idempotency_key: str | None = None,
                 sin_cuerpo: bool = False) -> dict:
        headers = {}
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key
        if authorization:
            headers["Authorization"] = f"Bearer {authorization}"
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id
        try:
            resp = self._http.request(method, path, json=json, params=params, headers=headers)
        except httpx.ConnectError:
            raise AtmError("ERR-ATM-COR-NO-DISPONIBLE", "No se pudo contactar con el Bus de Servicios", 503)
        except httpx.TimeoutException:
            raise AtmError("ERR-ATM-TIMEOUT-BUS", "El Bus no respondió a tiempo", 504)
        except httpx.HTTPError:
            raise AtmError("ERR-ATM-RESPUESTA_INVALIDA", "El Bus cortó la respuesta", 502)

        if resp.status_code >= 400:
            raise self._error_de_bus(resp)
        if sin_cuerpo:
            return {}
        cuerpo = resp.json()
        # TARJETAS y CUENTAS envuelven la respuesta: {success, status_code, message, data, metadata}.
        if isinstance(cuerpo, dict) and cuerpo.get("success") is True and "data" in cuerpo:
            return cuerpo["data"]
        return cuerpo

    @staticmethod
    def _error_de_bus(resp: httpx.Response) -> AtmError:
        try:
            cuerpo = resp.json()
        except ValueError:
            return AtmError("ERR-ATM-RESPUESTA_INVALIDA", resp.text[:200], 502)

        # El Bus devuelve errores propios (401, 404, 503, 504, 502) con formato {"detail": ..., "codigo": ..., "modulo": ...}
        if isinstance(cuerpo, dict) and "codigo" in cuerpo:
            return AtmError(cuerpo["codigo"], cuerpo.get("detail", ""), resp.status_code)

        # Errores de TARJETAS/CUENTAS/COREDB vienen en formato ITIL-02 con success=false
        if isinstance(cuerpo, dict) and cuerpo.get("success") is False:
            return AtmError(
                cuerpo.get("error_code", "DESCONOCIDO"),
                cuerpo.get("message", ""),
                resp.status_code,
                cuerpo.get("details")
            )

        # Errores de módulos a través del Bus: {"error": {"code": "...", "message": "..."}}
        if isinstance(cuerpo, dict) and isinstance(cuerpo.get("error"), dict):
            error = cuerpo["error"]
            if "code" in error:
                return AtmError(error["code"], error.get("message", ""), resp.status_code)

        # Error 422 de validación
        if resp.status_code == 422:
            return AtmError("ERR-ATM-VALIDACION-ESQUEMA",
                            "El módulo destino rechazó el formato de la solicitud",
                            400, {"detail": cuerpo.get("detail") if isinstance(cuerpo, dict) else None})

        return AtmError("ERR-ATM-RESPUESTA_INVALIDA", "Respuesta inesperada del Bus", 502)

    # ── TARJETAS ─────────────────────────────────────────────────────────

    def validar_pin(self, id_tarjeta: str, pin: str, id_terminal: str,
                    correlation_id: str | None = None, authorization: str | None = None) -> dict:
        """POST /bus/tarjetas/api/v1/tarjetas/{id_tarjeta}/credenciales/PIN_ATM/validacion"""
        path = f"/bus/tarjetas/api/v1/tarjetas/{id_tarjeta}/credenciales/PIN_ATM/validacion"
        payload = {"valor": pin, "id_terminal": id_terminal}
        return self._request("POST", path, json=payload, correlation_id=correlation_id, authorization=authorization)

    def autorizar(self, id_tarjeta: str, num_cuenta: str, moneda: str, monto: str,
                  id_canal: str | None, id_terminal: str | None,
                  uuid_transaccion: str, correlation_id: str | None = None,
                  authorization: str | None = None, idempotency_key: str | None = None) -> dict:
        """POST /bus/tarjetas/api/v1/tarjetas/{id_tarjeta}/autorizaciones"""
        path = f"/bus/tarjetas/api/v1/tarjetas/{id_tarjeta}/autorizaciones"
        payload = {
            "num_cuenta": num_cuenta,
            "tipo_operacion": "RETIRO",
            "monto": monto,
        }
        if id_canal:
            payload["id_canal"] = id_canal
        else:
            payload["id_terminal"] = id_terminal
        return self._request("POST", path, json=payload, correlation_id=correlation_id,
                             authorization=authorization, idempotency_key=idempotency_key)

    def confirmar(self, uuid_autorizacion: str, id_canal: str | None, id_terminal: str | None,
                  idempotency_key: str, correlation_id: str | None = None,
                  authorization: str | None = None) -> dict:
        """POST /bus/tarjetas/api/v1/tarjetas/autorizaciones/{uuid_autorizacion}/confirmacion
        con X-Idempotency-Key (#103): repetirla con la misma llave no debita dos veces."""
        path = f"/bus/tarjetas/api/v1/tarjetas/autorizaciones/{uuid_autorizacion}/confirmacion"
        payload = {"id_canal": id_canal} if id_canal else {"id_terminal": id_terminal}
        return self._request("POST", path, json=payload, correlation_id=correlation_id,
                             authorization=authorization, idempotency_key=idempotency_key)

    def extornar(self, uuid_autorizacion: str, motivo: str,
                 correlation_id: str | None = None,
                 authorization: str | None = None) -> dict:
        """POST /bus/tarjetas/api/v1/tarjetas/autorizaciones/{uuid_autorizacion}/extorno"""
        path = f"/bus/tarjetas/api/v1/tarjetas/autorizaciones/{uuid_autorizacion}/extorno"
        payload = {"motivo": motivo}
        return self._request("POST", path, json=payload, correlation_id=correlation_id, authorization=authorization)

    # ── CUENTAS ──────────────────────────────────────────────────────────

    def consultar_saldo(self, cod_cliente: str,
                        correlation_id: str | None = None,
                        authorization: str | None = None) -> dict:
        """GET /bus/cuentas/api/v1/cuentas/consolidada/{cod_cliente}"""
        path = f"/bus/cuentas/api/v1/cuentas/consolidada/{cod_cliente}"
        return self._request("GET", path, params={}, correlation_id=correlation_id, authorization=authorization)

    def consultar_movimientos(self, num_cuenta: str,
                              correlation_id: str | None = None,
                              authorization: str | None = None) -> dict:
        """GET /bus/cuentas/api/v1/cuentas/{num_cuenta}/movimientos"""
        path = f"/bus/cuentas/api/v1/cuentas/{num_cuenta}/movimientos"
        return self._request("GET", path, params={}, correlation_id=correlation_id, authorization=authorization)

    def obtener_cliente_de_tarjeta(self, id_tarjeta: str,
                                    correlation_id: str | None = None,
                                    authorization: str | None = None) -> dict:
        """GET /bus/tarjetas/api/v1/tarjetas/{id_tarjeta} para obtener el cod_cliente"""
        path = f"/bus/tarjetas/api/v1/tarjetas/{id_tarjeta}"
        return self._request("GET", path, params={}, correlation_id=correlation_id, authorization=authorization)