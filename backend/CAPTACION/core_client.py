"""Llamadas de CAPTACION a COREDB.

Dos identidades distintas:
- El token del asesor, que llega en la petición, solo se usa para saber quién es y qué
  puede hacer (`GET /coredb/auth/me`).
- El usuario de servicio de CAPTACION (rol SERVICIO, módulo CLIENTES) registra al
  cliente y sus validaciones. COREDB solo acepta un cliente HABILITADO de ese tipo de
  usuario (punto R-01 de CONTRATO_CLIENTES.md), porque es quien verificó la identidad.
"""

import threading
import time

import httpx

from CAPTACION.config import settings
from CAPTACION.errores import CaptacionError

# Códigos de COREDB que se traducen a un error del módulo (estado, código, mensaje).
TRADUCCION = {
    "CLIENTE_DUPLICADO": (409, "ERR-CAP-CLIENTE-DUPLICADO", "El documento ya pertenece a un cliente del banco."),
    "CORREO_DUPLICADO": (409, "ERR-CAP-CORREO-DUPLICADO", "El correo ya está registrado para otro cliente."),
    "CELULAR_DUPLICADO": (409, "ERR-CAP-CELULAR-DUPLICADO", "El celular ya está registrado para otro cliente."),
    "BNA-DOCUMENTO": (400, "ERR-CAP-DOCUMENTO-INVALIDO", "El número no cumple la regla de su tipo de documento."),
    "CLIENTE_NO_ENCONTRADO": (404, "ERR-CAP-CLIENTE-NO-ENCONTRADO", "COREDB no tiene ese cliente."),
    "HABILITACION_NO_PERMITIDA": (502, "ERR-CAP-CONFIGURACION-COREDB",
                                  "El usuario de servicio de CAPTACION no puede registrar clientes habilitados."),
    "PERMISO_DENEGADO": (502, "ERR-CAP-CONFIGURACION-COREDB",
                         "El usuario de servicio de CAPTACION no tiene permiso en COREDB."),
}


class CoreDb:
    def __init__(self, base_url: str | None = None, timeout: float | None = None,
                 transport: httpx.BaseTransport | None = None):
        self._http = httpx.Client(base_url=base_url or settings.core_base_url,
                                  timeout=timeout or settings.core_timeout_seconds,
                                  transport=transport, follow_redirects=False)
        self._token: str | None = None
        self._vence = 0.0
        self._candado = threading.Lock()
        # Perfil por token de usuario, por unos segundos: evita una ida a COREDB por cada clic.
        self._perfiles: dict[str, tuple[float, dict]] = {}

    def close(self) -> None:
        self._http.close()

    # ── transporte ────────────────────────────────────────────────────────
    def _enviar(self, metodo: str, ruta: str, *, token: str, correlation_id: str | None,
                json: dict | None = None) -> httpx.Response:
        cabeceras = {"Authorization": f"Bearer {token}"}
        if correlation_id:
            cabeceras["X-Correlation-ID"] = correlation_id
        try:
            return self._http.request(metodo, ruta, json=json, headers=cabeceras)
        except httpx.HTTPError:
            raise CaptacionError("ERR-CAP-COREDB-NO-DISPONIBLE", "COREDB no respondió.", 503) from None

    @staticmethod
    def _codigo(resp: httpx.Response) -> str:
        try:
            cuerpo = resp.json()
        except ValueError:
            return ""
        if isinstance(cuerpo, dict) and isinstance(cuerpo.get("error"), dict):
            return str(cuerpo["error"].get("code", ""))
        return ""

    def _fallo(self, resp: httpx.Response) -> CaptacionError:
        codigo = self._codigo(resp)
        if codigo in TRADUCCION:
            estado, propio, mensaje = TRADUCCION[codigo]
            return CaptacionError(propio, mensaje, estado, {"coredb": codigo})
        if resp.status_code >= 500:
            return CaptacionError("ERR-CAP-COREDB-NO-DISPONIBLE", "COREDB no pudo completar la operación.", 503)
        # 422 de esquema u otro rechazo: es un error de integración, no del usuario.
        return CaptacionError("ERR-CAP-COREDB-RECHAZO", "COREDB rechazó la operación.", 502,
                              {"coredb": codigo or resp.status_code})

    # ── usuario de servicio ───────────────────────────────────────────────
    def _token_servicio(self, correlation_id: str | None, renovar: bool = False) -> str:
        with self._candado:
            if not renovar and self._token and time.monotonic() < self._vence:
                return self._token
            secreto = settings.secreto_coredb()
            if not secreto:
                raise CaptacionError("ERR-CAP-CONFIGURACION-COREDB",
                                     "CAPTACION no tiene la credencial de su usuario de servicio.", 503)
            cabeceras = {"X-Correlation-ID": correlation_id} if correlation_id else {}
            try:
                resp = self._http.post("/coredb/auth/login", headers=cabeceras,
                                       json={"username": settings.cap_core_usuario, "password": secreto})
            except httpx.HTTPError:
                raise CaptacionError("ERR-CAP-COREDB-NO-DISPONIBLE", "COREDB no respondió.", 503) from None
            if resp.status_code != 200:
                raise CaptacionError("ERR-CAP-CONFIGURACION-COREDB",
                                     "COREDB no aceptó la credencial del usuario de servicio de CAPTACION.", 503)
            datos = resp.json()
            self._token = datos["access_token"]
            # Se renueva un minuto antes de que venza.
            self._vence = time.monotonic() + max(int(datos.get("expires_in", 300)) - 60, 30)
            return self._token

    def _servicio(self, metodo: str, ruta: str, correlation_id: str | None, json: dict | None = None,
                  aceptar: tuple[int, ...] = (200, 201)) -> dict:
        resp = self._enviar(metodo, ruta, token=self._token_servicio(correlation_id),
                            correlation_id=correlation_id, json=json)
        if resp.status_code == 401:  # token vencido o revocado: se inicia sesión otra vez, una sola vez
            resp = self._enviar(metodo, ruta, token=self._token_servicio(correlation_id, renovar=True),
                                correlation_id=correlation_id, json=json)
        if resp.status_code not in aceptar:
            raise self._fallo(resp)
        return resp.json()

    # ── identidad del asesor ──────────────────────────────────────────────
    def perfil(self, token: str, correlation_id: str | None) -> dict:
        ahora = time.monotonic()
        guardado = self._perfiles.get(token)
        if guardado and guardado[0] > ahora:
            return guardado[1]
        resp = self._enviar("GET", "/coredb/auth/me", token=token, correlation_id=correlation_id)
        if resp.status_code == 401:
            raise CaptacionError("ERR-CAP-TOKEN-INVALIDO", "La sesión no es válida o venció.", 401)
        if resp.status_code != 200:
            raise self._fallo(resp)
        perfil = resp.json()
        if len(self._perfiles) > 500:
            self._perfiles.clear()
        self._perfiles[token] = (ahora + 30, perfil)
        return perfil

    # ── clientes ──────────────────────────────────────────────────────────
    def verificar_documento(self, tipo: str, numero: str, correlation_id: str | None) -> dict:
        """RF-CLI-001: CAPTACION ya verificó la identidad; COREDB dice si es cliente activo."""
        return self._servicio("POST", "/coredb/clientes/validaciones/documento", correlation_id, {
            "tipo_documento": tipo, "numero_documento": numero, "identidad_verificada": True,
        })

    def registrar_cliente(self, datos: dict, correlation_id: str | None) -> dict:
        return self._servicio("POST", "/coredb/clientes", correlation_id, datos)

    def registrar_validacion(self, cod_cliente: str, tipo: str, resultado: str, motivo: str | None,
                             correlation_id: str | None) -> dict:
        cuerpo = {"tipo_validacion": tipo, "resultado": resultado}
        if motivo:
            cuerpo["motivo"] = motivo
        return self._servicio("POST", f"/coredb/clientes/{cod_cliente}/validaciones", correlation_id, cuerpo)

    def ver_cliente(self, cod_cliente: str, correlation_id: str | None) -> dict:
        return self._servicio("GET", f"/coredb/clientes/{cod_cliente}", correlation_id)

    def salud(self) -> bool:
        try:
            return self._http.get("/coredb/salud").status_code == 200
        except httpx.HTTPError:
            return False


_cliente: CoreDb | None = None


def coredb() -> CoreDb:
    """Un solo cliente por proceso: conserva el token del usuario de servicio."""
    global _cliente
    if _cliente is None:
        _cliente = CoreDb()
    return _cliente
