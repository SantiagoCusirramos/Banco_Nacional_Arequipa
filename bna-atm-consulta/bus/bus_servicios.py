"""Bus de Servicios para el canal ATM.

Rutas (todas POST, JSON):
  /autenticar              INT-02  ATM -> Tarjetas   valida clave y emite token de sesion
  /consulta-saldo          INT-06  ATM -> Cuentas    cuentas habilitadas y saldo
  /retiro                  INT-04  ATM -> Cuentas    autoriza y debita (idempotente por uuidTransaccion)
  /confirmar-dispensacion  INT-07  ATM -> Cuentas    confirma que el efectivo salio
  /extorno                 INT-05  ATM -> Cuentas    devuelve el debito si no hubo entrega

Cada llamada conserva el X-Correlation-ID. El Bus no guarda estado.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PUERTO = int(os.environ.get("BUS_PUERTO", "8001"))
CUENTAS_URL = os.environ.get("CUENTAS_URL", "http://127.0.0.1:8002/cuentas/habilitadas")
CUENTAS_BASE = os.environ.get("CUENTAS_BASE") or CUENTAS_URL.rsplit("/cuentas/", 1)[0]
TARJETAS_BASE = os.environ.get("TARJETAS_BASE", "http://127.0.0.1:8003")
ESPERA_DESTINO = 3  # segundos; el ATM espera 5 en total
PRUEBAS = os.environ.get("BUS_PRUEBAS") == "1"   # habilita la falla simulada de respuesta perdida

CAMPOS = ("tokenSesion", "idTarjetaTokenizado", "idCajero", "uuidConsulta")

RUTAS = {
    "/autenticar": {"campos": ("idTarjetaTokenizado", "pin", "idCajero", "uuidAutenticacion"),
                    "destino": TARJETAS_BASE + "/tarjetas/autenticar", "modulo": "tarjetas", "sesion": False,
                    "id": "uuidAutenticacion"},
    "/consulta-saldo": {"campos": CAMPOS, "destino": CUENTAS_URL, "modulo": "cuentas", "sesion": True,
                        "reenviar": ("idTarjetaTokenizado", "idCajero", "uuidConsulta"), "id": "uuidConsulta"},
    "/retiro": {"campos": ("tokenSesion", "idTarjetaTokenizado", "idCajero", "idCuenta", "moneda", "monto",
                           "uuidTransaccion"),
                "destino": CUENTAS_BASE + "/cuentas/retiro", "modulo": "cuentas", "sesion": True,
                "reenviar": ("idTarjetaTokenizado", "idCajero", "idCuenta", "moneda", "monto", "uuidTransaccion"),
                "id": "uuidTransaccion"},
    "/confirmar-dispensacion": {"campos": ("idCajero", "uuidTransaccion", "resultado"),
                                "destino": CUENTAS_BASE + "/cuentas/confirmar", "modulo": "cuentas",
                                "sesion": False, "id": "uuidTransaccion"},
    "/extorno": {"campos": ("idCajero", "uuidTransaccion", "motivo"),
                 "destino": CUENTAS_BASE + "/cuentas/extorno", "modulo": "cuentas", "sesion": False,
                 "id": "uuidTransaccion"},
}


def log(corr, texto, nivel="INFO"):
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"{ahora} {nivel:<5} bus      corr={corr[:8]} {texto}", flush=True)


def llamar(url, cuerpo, corr):
    """Devuelve (codigo, json). Lanza OSError si el destino no responde."""
    req = urllib.request.Request(url, data=json.dumps(cuerpo).encode(), method="POST", headers={
        "Content-Type": "application/json", "X-Correlation-ID": corr})
    try:
        with urllib.request.urlopen(req, timeout=ESPERA_DESTINO) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, {}
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        raise OSError(str(e))


class Bus(BaseHTTPRequestHandler):
    corr = "-"
    destino_ms = None

    def cabeceras_comunes(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Correlation-ID, X-Idempotency-Key, X-Prueba")
        self.send_header("Access-Control-Expose-Headers", "X-Correlation-ID, X-Cuentas-Ms")
        self.send_header("Cache-Control", "no-store")

    def responder(self, codigo, datos):
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("X-Correlation-ID", self.corr)
        if self.destino_ms is not None:
            self.send_header("X-Cuentas-Ms", str(self.destino_ms))
        self.cabeceras_comunes()
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *args):
        pass

    def do_OPTIONS(self):
        self.send_response(204)
        self.cabeceras_comunes()
        self.end_headers()

    def do_POST(self):
        inicio = time.perf_counter()
        self.corr = self.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        ruta = self.path
        self.perder = PRUEBAS and self.headers.get("X-Prueba") == "perder-respuesta"

        def fin(codigo, datos, detalle=""):
            ms = round((time.perf_counter() - inicio) * 1000)
            log(self.corr, f"POST {ruta} {codigo} {ms}ms {detalle}".rstrip(), "INFO" if codigo < 400 else "WARN")
            self.responder(codigo, datos)

        cfg = RUTAS.get(ruta)
        if not cfg:
            return fin(404, {"codigo": "RUTA_NO_ENCONTRADA", "mensaje": "Ruta no encontrada"})

        try:
            n = int(self.headers.get("Content-Length", "0"))
            if n < 1 or n > 4096:
                raise ValueError
            datos = json.loads(self.rfile.read(n))
            if not isinstance(datos, dict):
                raise ValueError
        except (ValueError, UnicodeError):
            return fin(400, {"codigo": "SOLICITUD_INVALIDA", "mensaje": "Se esperaba un JSON valido"})

        faltan = [c for c in cfg["campos"] if datos.get(c) is None or (isinstance(datos[c], str) and not datos[c].strip())]
        if faltan:
            return fin(400, {"codigo": "SOLICITUD_INVALIDA", "mensaje": "Faltan campos: " + ", ".join(faltan),
                             cfg["id"]: datos.get(cfg["id"])})
        ident = datos[cfg["id"]]
        modulo = "Tarjetas" if cfg["modulo"] == "tarjetas" else "Cuentas"

        # el token de sesion se valida con Tarjetas antes de operar
        if cfg["sesion"]:
            try:
                est, _ = llamar(TARJETAS_BASE + "/tarjetas/validar-sesion",
                                {"tokenSesion": datos["tokenSesion"], "idTarjetaTokenizado": datos["idTarjetaTokenizado"]},
                                self.corr)
            except OSError:
                return fin(504, {"codigo": "TARJETAS_NO_DISPONIBLE", "mensaje": "Tarjetas no responde",
                                 cfg["id"]: ident}, "tarjetas sin respuesta")
            if est != 200:
                return fin(401, {"codigo": "SESION_INVALIDA", "mensaje": "La sesion no es valida o vencio",
                                 cfg["id"]: ident})

        reenviar = cfg.get("reenviar")
        cuerpo = {k: datos[k] for k in reenviar} if reenviar else {k: v for k, v in datos.items() if k != "idCajero"}
        if cfg["modulo"] == "tarjetas":
            cuerpo = {k: datos[k] for k in ("idTarjetaTokenizado", "pin", "idCajero", "uuidAutenticacion")}
        t0 = time.perf_counter()
        try:
            est, resp = llamar(cfg["destino"], cuerpo, self.corr)
        except OSError:
            return fin(504, {"codigo": modulo.upper() + "_NO_DISPONIBLE", "mensaje": modulo + " no responde",
                             cfg["id"]: ident}, modulo.lower() + " sin respuesta")
        self.destino_ms = round((time.perf_counter() - t0) * 1000)

        if est >= 400:
            codigo = resp.get("codigo", "ERROR")
            if ruta == "/consulta-saldo" and est == 404:
                return fin(404, {"codigo": codigo, "mensaje": "La tarjeta no tiene cuentas habilitadas para cajero",
                                 "uuidConsulta": ident}, "cuentas=0")
            if est in (400, 401, 404, 409, 423):
                salida = dict(resp)
                salida[cfg["id"]] = ident
                salida.setdefault("mensaje", codigo)
                return fin(est, salida, codigo)
            return fin(502, {"codigo": modulo.upper() + "_ERROR", "mensaje": modulo + " devolvio un error",
                             cfg["id"]: ident}, f"{modulo.lower()}={est}")

        if ruta == "/consulta-saldo":
            salida = {"uuidConsulta": ident, "idCajero": datos["idCajero"],
                      "listaCuentas": resp.get("listaCuentas", [])}
            if resp.get("simulado"):
                salida["simulado"] = True
            return fin(200, salida, f"cuentas={len(salida['listaCuentas'])}")

        salida = dict(resp)
        salida[cfg["id"]] = ident
        detalle = resp.get("estado", "") + (" repetido" if resp.get("repetido") else "")
        if ruta == "/retiro" and self.perder:
            # falla simulada: el debito se hizo pero la respuesta no llega al cajero
            log(self.corr, f"POST {ruta} respuesta descartada (prueba) {detalle}", "WARN")
            self.close_connection = True
            return
        fin(200, salida, detalle)


if __name__ == "__main__":
    print(f"Bus de Servicios escuchando en :{PUERTO}  ->  Cuentas {CUENTAS_BASE}  Tarjetas {TARJETAS_BASE}", flush=True)
    try:
        ThreadingHTTPServer(("0.0.0.0", PUERTO), Bus).serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
    except OSError as e:
        print(f"no se pudo abrir el puerto: {e.strerror}", flush=True)
        sys.exit(1)
