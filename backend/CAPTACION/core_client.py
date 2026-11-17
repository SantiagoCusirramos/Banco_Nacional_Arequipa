"""Llamadas de CAPTACION a COREDB. CAPTACION no tiene base propia: el expediente vive en la
base integrada (clientes.*_captacion) y se trabaja por /coredb/captacion.

Dos identidades distintas:
- El token del asesor, que llega en la petición: quién es y qué puede hacer
  (`GET /coredb/auth/me`), y todo lo que hace una persona sobre el expediente, que queda
  a su nombre en la bitácora de la base.
- El usuario de servicio de CAPTACION (rol SERVICIO, módulo CLIENTES) verifica el
  documento, registra al cliente y lo liga al caso, y lee las referencias que consulta
  SOL. COREDB solo acepta un cliente HABILITADO de ese tipo de usuario (punto R-01 de
  CONTRATO_CLIENTES.md), porque es quien verificó la identidad.
"""

import threading
import time

import httpx

from CAPTACION.config import settings
from CAPTACION.errores import CaptacionError

# Códigos de COREDB que son errores de negocio del expediente: (estado, código propio). El
# mensaje de COREDB no lleva valores de entrada y se devuelve tal cual.
NEGOCIO = {
    "DOCUMENTO_INVALIDO": (400, "ERR-CAP-DOCUMENTO-INVALIDO"),
    "SOLICITANTE_NO_ENCONTRADO": (404, "ERR-CAP-SOLICITANTE-NO-ENCONTRADO"),
    "CASO_NO_ENCONTRADO": (404, "ERR-CAP-CASO-NO-ENCONTRADO"),
    "CASO_ABIERTO": (409, "ERR-CAP-CASO-ABIERTO"),
    "CASO_CERRADO": (409, "ERR-CAP-CASO-CERRADO"),
    "ESTADO_INVALIDO": (409, "ERR-CAP-ESTADO-INVALIDO"),
    "CASO_NO_LISTO": (422, "ERR-CAP-CASO-NO-LISTO"),
    "CASO_CON_OTRO_CLIENTE": (409, "ERR-CAP-CASO-CON-OTRO-CLIENTE"),
    "AGENCIA_NO_ENCONTRADA": (422, "ERR-CAP-AGENCIA-NO-ENCONTRADA"),
    "CONSENTIMIENTO_REQUERIDO": (422, "ERR-CAP-CONSENTIMIENTO-REQUERIDO"),
    "OTP_NO_ENCONTRADO": (404, "ERR-CAP-OTP-NO-ENCONTRADO"),
    "SIN_CONSULTA": (422, "ERR-CAP-SIN-CONSULTA"),
    "CLIENTE_NO_ACTIVO": (422, "ERR-CAP-CLIENTE-NO-ACTIVO"),
    "CLIENTE_NO_COINCIDE": (422, "ERR-CAP-CLIENTE-NO-COINCIDE"),
    "DATOS_INVALIDOS": (400, "ERR-CAP-DATOS-INVALIDOS"),
}
# Códigos que se traducen con un mensaje propio: (estado, código, mensaje).
TRADUCCION = {
    "CLIENTE_DUPLICADO": (409, "ERR-CAP-CLIENTE-DUPLICADO", "El documento ya pertenece a un cliente del banco."),
    "CORREO_DUPLICADO": (409, "ERR-CAP-CORREO-DUPLICADO", "El correo ya está registrado para otro cliente."),
    "CELULAR_DUPLICADO": (409, "ERR-CAP-CELULAR-DUPLICADO", "El celular ya está registrado para otro cliente."),
    "CLIENTE_NO_ENCONTRADO": (404, "ERR-CAP-CLIENTE-NO-ENCONTRADO", "COREDB no tiene ese cliente."),
    "HABILITACION_NO_PERMITIDA": (502, "ERR-CAP-CONFIGURACION-COREDB",
                                  "El usuario de servicio de CAPTACION no puede registrar clientes habilitados."),
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
                json: dict | None = None, params: dict | None = None) -> httpx.Response:
        cabeceras = {"Authorization": f"Bearer {token}"}
        if correlation_id:
            cabeceras["X-Correlation-ID"] = correlation_id
        try:
            return self._http.request(metodo, ruta, json=json, params=params, headers=cabeceras)
        except httpx.HTTPError:
            raise CaptacionError("ERR-CAP-COREDB-NO-DISPONIBLE", "COREDB no respondió.", 503) from None

    @staticmethod
    def _error(resp: httpx.Response) -> tuple[str, str]:
        try:
            cuerpo = resp.json()
        except ValueError:
            return "", ""
        if isinstance(cuerpo, dict) and isinstance(cuerpo.get("error"), dict):
            return str(cuerpo["error"].get("code", "")), str(cuerpo["error"].get("message", ""))
        return "", ""

    def _fallo(self, resp: httpx.Response, persona: bool) -> CaptacionError:
        codigo, mensaje = self._error(resp)
        if codigo in NEGOCIO:
            estado, propio = NEGOCIO[codigo]
            return CaptacionError(propio, mensaje or "COREDB rechazó la operación.", estado, {"coredb": codigo})
        if codigo in TRADUCCION:
            estado, propio, texto = TRADUCCION[codigo]
            return CaptacionError(propio, texto, estado, {"coredb": codigo})
        if codigo == "PERMISO_DENEGADO":
            if persona:
                return CaptacionError("ERR-CAP-PERMISO-DENEGADO", "Su rol no tiene permiso para esta operación.", 403)
            return CaptacionError("ERR-CAP-CONFIGURACION-COREDB",
                                  "El usuario de servicio de CAPTACION no tiene permiso en COREDB.", 502)
        if resp.status_code >= 500:
            return CaptacionError("ERR-CAP-COREDB-NO-DISPONIBLE", "COREDB no pudo completar la operación.", 503)
        # 422 de esquema u otro rechazo: es un error de integración, no del usuario.
        return CaptacionError("ERR-CAP-COREDB-RECHAZO", "COREDB rechazó la operación.", 502,
                              {"coredb": codigo or resp.status_code})

    # ── con el token del asesor ───────────────────────────────────────────
    def persona(self, metodo: str, ruta: str, token: str, correlation_id: str | None, *,
                json: dict | None = None, params: dict | None = None, aceptar: tuple[int, ...] = (200, 201)):
        resp = self._enviar(metodo, ruta, token=token, correlation_id=correlation_id, json=json, params=params)
        if resp.status_code == 401:
            raise CaptacionError("ERR-CAP-TOKEN-INVALIDO", "La sesión no es válida o venció.", 401)
        if resp.status_code not in aceptar:
            raise self._fallo(resp, persona=True)
        return resp.json()

    # ── usuario de servicio ───────────────────────────────────────────────
    def _token_servicio(self, correlation_id: str | None, renovar: bool = False) -> str:
        with self._candado:
            if not renovar and self._token and time.monotonic() < self._vence:
                return self._token
            secreto = settings.cap_core_secreto
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

    def servicio(self, metodo: str, ruta: str, correlation_id: str | None, *, json: dict | None = None,
                 params: dict | None = None, aceptar: tuple[int, ...] = (200, 201)):
        resp = self._enviar(metodo, ruta, token=self._token_servicio(correlation_id),
                            correlation_id=correlation_id, json=json, params=params)
        if resp.status_code == 401:  # token vencido o revocado: se inicia sesión otra vez, una sola vez
            resp = self._enviar(metodo, ruta, token=self._token_servicio(correlation_id, renovar=True),
                                correlation_id=correlation_id, json=json, params=params)
        if resp.status_code not in aceptar:
            raise self._fallo(resp, persona=False)
        return resp.json()

    # ── identidad del asesor ──────────────────────────────────────────────
    def perfil(self, token: str, correlation_id: str | None) -> dict:
        ahora = time.monotonic()
        guardado = self._perfiles.get(token)
        if guardado and guardado[0] > ahora:
            return guardado[1]
        perfil = self.persona("GET", "/coredb/auth/me", token, correlation_id)
        if len(self._perfiles) > 500:
            self._perfiles.clear()
        self._perfiles[token] = (ahora + 30, perfil)
        return perfil

    # ── clientes (usuario de servicio) ────────────────────────────────────
    def verificar_documento(self, tipo: str, numero: str, correlation_id: str | None) -> dict:
        """RF-CLI-001: CAPTACION ya verificó la identidad; COREDB dice si es cliente activo."""
        return self.servicio("POST", "/coredb/clientes/validaciones/documento", correlation_id, json={
            "tipo_documento": tipo, "numero_documento": numero, "identidad_verificada": True,
        })

    def registrar_cliente(self, datos: dict, correlation_id: str | None) -> dict:
        return self.servicio("POST", "/coredb/clientes", correlation_id, json=datos)

    def ver_cliente(self, cod_cliente: str, correlation_id: str | None) -> dict:
        return self.servicio("GET", f"/coredb/clientes/{cod_cliente}", correlation_id)

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
