"""Cliente del modulo Cuentas (CR-INT-07). Tres variantes: simulado en memoria (por defecto, para pruebas),
HTTP contra el simulador propio (CUENTAS_URL) y CUENTAS real del producto BNA (CUENTAS_MODO=BNA)."""
import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal


class CuentasSimulado:
    """Simula la respuesta de Cuentas. Se controla con el valor de cuentaOrigen para poder demostrar casos."""

    def cargar(self, codCredito, cuentaOrigen, monto, moneda, referencia):
        if cuentaOrigen == "SIN-FONDOS":
            return "RECHAZADO", "Fondos insuficientes (Cuentas simulado)"
        if cuentaOrigen == "SIN-RESPUESTA":
            return "SIN_RESPUESTA", "Cuentas no respondio (simulado)"
        return "CONFIRMADO", "Cargo confirmado (Cuentas simulado)"

    def consultar(self, referencia, pago=None):
        """RF-COB-011 / INC-01: consulta posterior del estado de una operacion por su idOperacion
        (referenciaTransaccion), para resolver un pago que quedo PENDIENTE sin repetir el cargo
        (RN-COB-009). Simulado: por defecto ya hay respuesta (CONFIRMADO), para poder demostrar que un
        pago que quedo "SIN-RESPUESTA" se resuelve al consultarlo de nuevo. La referencia admite sufijos
        para demostrar los otros desenlaces."""
        if referencia.endswith("-RECHAZA"):
            return "RECHAZADO", "Fondos insuficientes al consultar (Cuentas simulado)"
        if referencia.endswith("-SIGUESIN"):
            return "SIN_RESPUESTA", "Cuentas aun no responde (simulado)"
        return "CONFIRMADO", "Cargo confirmado al consultar (Cuentas simulado)"


class CuentasHTTP:
    """Llama al modulo Cuentas real si se define CUENTAS_URL. Usa los campos de CR-INT-07.
    El formato de la respuesta debe acordarse con el equipo de Cuentas."""

    def __init__(self, url, timeout=5):
        self.url = url
        self.timeout = timeout

    def cargar(self, codCredito, cuentaOrigen, monto, moneda, referencia):
        import httpx
        try:
            r = httpx.post(
                self.url,
                json={"codCredito": codCredito, "numCuentaAhorro": cuentaOrigen,
                      "montoCuota": float(monto), "moneda": moneda, "idOperacion": referencia},
                timeout=self.timeout,
            )
        except Exception:
            return "SIN_RESPUESTA", "Cuentas no respondio"
        if r.status_code >= 500:
            return "SIN_RESPUESTA", "Cuentas devolvio un error del servidor"
        try:
            data = r.json()
        except Exception:
            return "SIN_RESPUESTA", "Respuesta de Cuentas no valida"
        ok = data.get("confirmado") is True or str(data.get("estado", "")).upper() in ("CONFIRMADO", "OK", "EXITOSO")
        return ("CONFIRMADO" if ok else "RECHAZADO"), str(data.get("mensaje") or data.get("detalle") or "")

    def consultar(self, referencia, pago=None):
        """RF-COB-011 / INC-01. Formato de la consulta por acordar con el equipo de Cuentas; aqui se
        asume un GET por idOperacion."""
        import httpx
        try:
            r = httpx.get(f"{self.url}/{referencia}", timeout=self.timeout)
        except Exception:
            return "SIN_RESPUESTA", "Cuentas no respondio"
        if r.status_code >= 500:
            return "SIN_RESPUESTA", "Cuentas devolvio un error del servidor"
        try:
            data = r.json()
        except Exception:
            return "SIN_RESPUESTA", "Respuesta de Cuentas no valida"
        estado = str(data.get("estado", "")).upper()
        if data.get("confirmado") is True or estado in ("CONFIRMADO", "OK", "EXITOSO"):
            return "CONFIRMADO", str(data.get("mensaje") or data.get("detalle") or "")
        if estado in ("RECHAZADO", "FALLIDO"):
            return "RECHAZADO", str(data.get("mensaje") or data.get("detalle") or "")
        return "SIN_RESPUESTA", "Cuentas aun no tiene una respuesta definitiva"


class CredencialServicio:
    """Usuario de servicio de Cobranza en COREDB (rol SERVICIO, modulo COBRANZA).

    Se lee de COBRANZA_SVC_USUARIO y COBRANZA_SVC_SECRETO o, si faltan, del archivo JSON
    COBRANZA_SVC_ARCHIVO ({"username": ..., "secreto": ...}) que deja `cobranza-init`.
    Se vuelve a leer en cada login, porque el archivo cambia cuando se renueva el secreto."""

    def __init__(self, usuario=None, secreto=None, archivo=None):
        self._usuario = usuario
        self._secreto = secreto
        self._archivo = archivo

    def leer(self):
        if self._usuario and self._secreto:
            return self._usuario, self._secreto
        if self._archivo and os.path.exists(self._archivo):
            with open(self._archivo, encoding="utf-8") as f:
                datos = json.load(f)
            return datos.get("username"), datos.get("secreto")
        return None, None


def idempotency_key_de(referencia):
    """CUENTAS exige un UUIDv4 en X-Idempotency-Key. Se deriva de la referencia del pago, siempre
    igual para la misma referencia: asi un reintento no cobra dos veces (RN-INT-CR-006) y la
    consulta posterior (RF-COB-011) encuentra el mismo movimiento sin guardar nada extra."""
    base = uuid.uuid5(uuid.NAMESPACE_URL, f"bna:cobranza:{referencia}")
    return str(uuid.UUID(bytes=base.bytes, version=4))


class CuentasBNA:
    """CR-INT-07 contra el modulo CUENTAS real del producto BNA (backend/CUENTAS).

    Cobra la cuota con POST {CUENTAS_URL}/retiro, con las cabeceras de ITIL-01 y el token de
    COREDB del usuario de servicio de Cobranza. CUENTAS no tiene base propia: reenvia a COREDB.
    Consulta un cobro anterior entre los movimientos de la cuenta, sin volver a cobrar. Los montos van como texto
    decimal ("150.00"), igual que en el resto del producto."""

    # COREDB devuelve como maximo 50 movimientos por consulta si no se pide otro limite
    LIMITE_CONSULTA = 50

    def __init__(self, cuentas_url, coredb_url, credencial, canal="WEB", timeout=5, transporte=None):
        self.cuentas_url = cuentas_url.rstrip("/")
        self.coredb_url = coredb_url.rstrip("/")
        self.credencial = credencial
        self.canal = canal
        self.timeout = timeout
        self.transporte = transporte  # solo para pruebas (httpx.MockTransport)
        self._token = None

    def _cliente(self):
        import httpx
        return httpx.Client(timeout=self.timeout, transport=self.transporte)

    def _login(self, http):
        usuario, secreto = self.credencial.leer()
        if not usuario or not secreto:
            raise ErrorCredencial("Cobranza no tiene usuario de servicio de COREDB configurado")
        r = http.post(f"{self.coredb_url}/coredb/auth/login",
                      json={"username": usuario, "password": secreto},
                      headers={"X-Correlation-ID": str(uuid.uuid4())})
        if r.status_code != 200:
            raise ErrorCredencial(f"COREDB rechazo el login del usuario de servicio ({r.status_code})")
        self._token = r.json()["access_token"]

    def _con_token(self, http, enviar):
        """Envia con el token vigente; ante un 401 (token vencido) inicia sesion una vez y reintenta.
        Reintentar es seguro: la llave de idempotencia es la misma."""
        if self._token is None:
            self._login(http)
        r = enviar(self._token)
        if r.status_code == 401:
            self._login(http)
            r = enviar(self._token)
        return r

    @staticmethod
    def _mensaje(r):
        try:
            data = r.json()
        except Exception:
            return f"HTTP {r.status_code}"
        codigo = data.get("error_code")
        texto = data.get("message") or ""
        return f"{codigo}: {texto}" if codigo else (texto or f"HTTP {r.status_code}")

    def cargar(self, codCredito, cuentaOrigen, monto, moneda, referencia):
        import httpx
        llave = idempotency_key_de(referencia)
        cuerpo = {
            "num_cuenta": cuentaOrigen,
            "monto": format(Decimal(str(monto)), ".2f"),
            "moneda": moneda,
            "glosa": f"Pago de cuota del credito {codCredito} (ref. {referencia})"[:200],
        }

        def enviar(token):
            return http.post(f"{self.cuentas_url}/retiro", json=cuerpo, headers={
                "Authorization": f"Bearer {token}",
                "X-Idempotency-Key": llave,
                "X-Channel-ID": self.canal,
                "X-Request-Timestamp": datetime.now(timezone.utc).isoformat(),
                "X-Correlation-ID": llave,
            })

        try:
            with self._cliente() as http:
                r = self._con_token(http, enviar)
        except ErrorCredencial as exc:
            return "RECHAZADO", str(exc)
        except httpx.HTTPError:
            return "SIN_RESPUESTA", "CUENTAS no respondio"
        if r.status_code in (200, 201):
            data = (r.json() or {}).get("data") or {}
            return "CONFIRMADO", f"Cargo aplicado en CUENTAS (uuid_transaccion {data.get('uuid_transaccion', llave)})"
        if r.status_code >= 500:
            # 503 COREDB apagado, 504 operacion no confirmada: no se sabe si cobro -> PENDIENTE (INC-01)
            return "SIN_RESPUESTA", self._mensaje(r)
        return "RECHAZADO", self._mensaje(r)

    def consultar(self, referencia, pago=None):
        """RF-COB-011 / INC-01, sin volver a cobrar (RN-COB-009): busca el cargo entre los movimientos
        de la cuenta debitada (GET {CUENTAS_URL}/{num_cuenta}/movimientos) por la referencia del pago,
        que va en la glosa. COREDB registra el movimiento en la misma transaccion que el debito:
        si no aparece, no se cobro."""
        import httpx
        cuenta = (pago or {}).get("cuentaOrigen")
        if not cuenta:
            return "SIN_RESPUESTA", "El pago no guarda la cuenta debitada; revisar en CUENTAS a mano"
        marca = f"(ref. {referencia})"

        def enviar(token):
            return http.get(f"{self.cuentas_url}/{cuenta}/movimientos", headers={
                "Authorization": f"Bearer {token}", "X-Correlation-ID": str(uuid.uuid4())})

        try:
            with self._cliente() as http:
                r = self._con_token(http, enviar)
        except ErrorCredencial as exc:
            return "SIN_RESPUESTA", str(exc)
        except httpx.HTTPError:
            return "SIN_RESPUESTA", "CUENTAS no respondio"
        if r.status_code != 200:
            return "SIN_RESPUESTA", self._mensaje(r)
        movimientos = (r.json() or {}).get("data") or []
        for m in movimientos:
            if marca in str(m.get("glosa", "")):
                estado = str(m.get("estado_transaccion", "")).upper()
                if estado == "EXTORNADO":
                    return "RECHAZADO", "CUENTAS extorno el cargo"
                return "CONFIRMADO", f"CUENTAS registra el cargo {m.get('uuid_transaccion', '')}".strip()
        if len(movimientos) >= self.LIMITE_CONSULTA:
            return "SIN_RESPUESTA", "El cargo no esta entre los ultimos movimientos; revisar en CUENTAS"
        return "RECHAZADO", "CUENTAS no tiene el cargo: no se cobro"


class ErrorCredencial(Exception):
    pass


def crear_cliente_cuentas():
    """CUENTAS_MODO=BNA: CUENTAS real del producto (con COREDB_URL y usuario de servicio).
    Sin modo y con CUENTAS_URL: el cliente HTTP del simulador propio. Sin nada: simulado en memoria."""
    url = os.environ.get("CUENTAS_URL", "").strip()
    modo = os.environ.get("CUENTAS_MODO", "").strip().upper()
    if modo == "BNA":
        credencial = CredencialServicio(
            usuario=os.environ.get("COBRANZA_SVC_USUARIO", "").strip() or None,
            secreto=os.environ.get("COBRANZA_SVC_SECRETO", "").strip() or None,
            archivo=os.environ.get("COBRANZA_SVC_ARCHIVO", "").strip() or None,
        )
        return CuentasBNA(url, os.environ.get("COREDB_URL", "").strip(), credencial,
                          canal=os.environ.get("COBRANZA_CANAL_CUENTAS", "WEB").strip() or "WEB")
    return CuentasHTTP(url) if url else CuentasSimulado()
