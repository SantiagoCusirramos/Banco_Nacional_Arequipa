"""Cajero ATM: pantalla, bandejas de billetes, dispensador simulado, retiro con
extorno automatico y registro de operaciones.

La pantalla autentica y consulta cuentas directo contra el Bus. El retiro lo orquesta este
servidor (RF-ATM-02, 04, 06, 07): valida el monto, comprueba que las bandejas puedan formar
el importe, pide la autorizacion al Bus (INT-04), dispensa y confirma (INT-07). Si el
dispensador falla, pide el extorno (INT-05).
"""
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PUERTO = int(os.environ.get("ATM_PUERTO", "8000"))
BUS_BASE = os.environ.get("BUS_BASE", "http://127.0.0.1:8001")
TARJETAS_BASE = os.environ.get("TARJETAS_BASE", "http://127.0.0.1:8003")
ID_CAJERO = os.environ.get("ATM_ID", "ATM-AQP-001")
ESPERA = float(os.environ.get("ATM_ESPERA", "5"))          # RNF-02: 5 s por llamada
REINTENTOS = 2                                              # maximo 2, espera exponencial
PRUEBAS = os.environ.get("ATM_PRUEBAS") == "1"
QUIEN = Path(__file__).resolve().parent
REGISTRO = Path(os.environ.get("ATM_REGISTRO", str(QUIEN / "registro_operaciones.jsonl")))

BANDEJAS_INICIAL = {"PEN": {200: 20, 100: 40, 50: 60, 20: 80, 10: 80},
                    "USD": {100: 20, 50: 40, 20: 60, 10: 60}}
candado = threading.RLock()
bandejas = {}
operaciones = {}         # uuidTransaccion -> (http, cuerpo) final; idempotencia en el canal
pendientes = []          # extornos o confirmaciones que no llegaron al Bus
pruebas = {"dispensador": "normal", "perderRespuestaBus": False}


def reiniciar_bandejas():
    bandejas.clear()
    bandejas.update({m: dict(d) for m, d in BANDEJAS_INICIAL.items()})


reiniciar_bandejas()


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def log(corr, texto, nivel="INFO"):
    print(f"{ahora()} {nivel:<5} atm      corr={corr[:8]} {texto}", flush=True)


def registrar(corr, uuid_t, tipo, estado, **extra):
    """RF-ATM-07: una linea por evento. Nunca guarda clave, token ni numero de tarjeta completo."""
    fila = {"ts": ahora(), "terminal": ID_CAJERO, "correlationId": corr, "uuidTransaccion": uuid_t,
            "tipo": tipo, "estado": estado}
    fila.update({k: v for k, v in extra.items() if v is not None})
    with candado:
        with open(REGISTRO, "a", encoding="utf-8") as f:
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")
    log(corr, f"{tipo} {estado} " + " ".join(f"{k}={v}" for k, v in extra.items() if v is not None))


def componer(monto, moneda):
    """Forma el importe con los billetes disponibles (voraz). Devuelve {denominacion: cantidad} o None."""
    resto, plan = int(monto), {}
    for den in sorted(bandejas[moneda], reverse=True):
        cant = min(bandejas[moneda][den], resto // den)
        if cant:
            plan[den] = cant
            resto -= cant * den
    return plan if resto == 0 else None


def llamar_bus(ruta, cuerpo, corr, clave=None, perder=False, base=None):
    """Una llamada al Bus: espera de 5 s y hasta 2 reintentos con la misma clave de idempotencia.
    Devuelve (codigoHttp o None, json, reintentosUsados)."""
    ultimo = (None, {})
    for intento in range(REINTENTOS + 1):
        cab = {"Content-Type": "application/json", "X-Correlation-ID": corr}
        if clave:
            cab["X-Idempotency-Key"] = clave
        if perder and intento == 0:
            cab["X-Prueba"] = "perder-respuesta"
        req = urllib.request.Request((base or BUS_BASE) + ruta, data=json.dumps(cuerpo).encode(), method="POST", headers=cab)
        try:
            with urllib.request.urlopen(req, timeout=ESPERA) as r:
                return r.status, json.loads(r.read()), intento
        except urllib.error.HTTPError as e:
            try:
                datos = json.loads(e.read())
            except ValueError:
                datos = {}
            if e.code != 504:
                return e.code, datos, intento
            ultimo = (e.code, datos)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            ultimo = (None, {})
        if intento < REINTENTOS:
            time.sleep(0.2 * (2 ** intento))
    return ultimo[0], ultimo[1], REINTENTOS


def extornar(corr, uuid_t, motivo, base=None):
    est, resp, _ = llamar_bus("/extorno", {"idCajero": ID_CAJERO, "uuidTransaccion": uuid_t, "motivo": motivo},
                              corr, uuid_t, base=base)
    return est, resp


def retirar(d, corr):
    """Devuelve (codigoHttp, cuerpo)."""
    campos = ("tokenSesion", "idTarjetaTokenizado", "idCuenta", "moneda", "monto", "uuidTransaccion")
    if any(d.get(c) in (None, "") for c in campos):
        return 400, {"codigo": "SOLICITUD_INVALIDA", "mensaje": "Faltan campos del retiro"}
    uuid_t, moneda, tarjeta = str(d["uuidTransaccion"]), d["moneda"], str(d["idTarjetaTokenizado"])
    base = d.get("busBase") if isinstance(d.get("busBase"), str) and d["busBase"].startswith("http") else None
    with candado:
        previo = operaciones.get(uuid_t)
    if previo:
        log(corr, f"retiro repetido uuid={uuid_t[:8]}: se devuelve el resultado anterior")
        return previo[0], dict(previo[1], repetido=True)
    t0 = time.perf_counter()
    mascara = "****" + tarjeta[-4:]

    def cerrar(http, cuerpo, estado, **extra):
        ms = round((time.perf_counter() - t0) * 1000)
        cuerpo = dict(cuerpo, uuidTransaccion=uuid_t, estado=estado, correlationId=corr)
        registrar(corr, uuid_t, "RETIRO", estado, tarjeta=mascara, cuenta=d["idCuenta"], moneda=moneda,
                  monto=d["monto"], ms=ms, **extra)
        with candado:
            operaciones[uuid_t] = (http, cuerpo)
        return http, cuerpo

    try:
        monto = float(d["monto"])
    except (TypeError, ValueError):
        monto = 0
    if moneda not in bandejas or monto <= 0 or monto != int(monto) or int(monto) % 10 != 0:
        return cerrar(400, {"codigo": "MONTO_INVALIDO", "mensaje": "El monto debe ser multiplo de 10"},
                      "RECHAZADA", codigo="MONTO_INVALIDO")
    monto = int(monto)
    registrar(corr, uuid_t, "RETIRO", "INICIADA", tarjeta=mascara, cuenta=d["idCuenta"], moneda=moneda, monto=monto)
    with candado:
        plan = componer(monto, moneda)
    if plan is None:                       # RN-ATM-002: no autorizar lo que el cajero no puede dispensar
        return cerrar(409, {"codigo": "BILLETES_INSUFICIENTES", "mensaje": "El cajero no puede formar ese monto"},
                      "RECHAZADA", codigo="BILLETES_INSUFICIENTES")

    est, resp, reint = llamar_bus("/retiro", {
        "tokenSesion": d["tokenSesion"], "idTarjetaTokenizado": tarjeta, "idCajero": ID_CAJERO,
        "idCuenta": d["idCuenta"], "moneda": moneda, "monto": monto, "uuidTransaccion": uuid_t},
        corr, uuid_t, perder=PRUEBAS and pruebas["perderRespuestaBus"], base=base)
    if est is None or est == 504:          # no se sabe si se debito: se pide extorno con la misma clave
        e2, r2 = extornar(corr, uuid_t, "SIN_CONFIRMACION", base)
        if e2 == 200:
            estado_final = "EXTORNADA" if r2.get("estado") == "EXTORNADA" else "RECHAZADA"
            return cerrar(504, {"codigo": "RETIRO_NO_CONFIRMADO", "mensaje": "No se confirmo el retiro",
                                "saldoDisponible": r2.get("saldoDisponible")}, estado_final,
                          codigo="RETIRO_NO_CONFIRMADO", intentos=reint + 1)
        with candado:
            pendientes.append({"tipo": "EXTORNO", "uuidTransaccion": uuid_t, "motivo": "SIN_CONFIRMACION",
                               "correlationId": corr, "base": base})
        return cerrar(504, {"codigo": "RETIRO_NO_CONFIRMADO", "mensaje": "Operacion en verificacion"},
                      "PENDIENTE_REVERSION", codigo="RETIRO_NO_CONFIRMADO", intentos=reint + 1)
    if est != 200:
        return cerrar(est, {"codigo": resp.get("codigo", "ERROR"), "mensaje": resp.get("mensaje", "")},
                      "RECHAZADA", codigo=resp.get("codigo"))
    registrar(corr, uuid_t, "RETIRO", "AUTORIZADA", tarjeta=mascara, cuenta=d["idCuenta"], moneda=moneda, monto=monto,
              intentos=reint + 1, repetido=True if resp.get("repetido") else None)

    modo = pruebas["dispensador"] if PRUEBAS else "normal"
    if modo == "normal":
        with candado:
            for den, cant in plan.items():
                bandejas[moneda][den] -= cant
        billetes = [{"denominacion": den, "cantidad": cant} for den, cant in sorted(plan.items(), reverse=True)]
        ce, _, _ = llamar_bus("/confirmar-dispensacion", {"idCajero": ID_CAJERO, "uuidTransaccion": uuid_t,
                                                          "resultado": "DISPENSADO"}, corr, uuid_t, base=base)
        if ce != 200:
            with candado:
                pendientes.append({"tipo": "CONFIRMACION", "uuidTransaccion": uuid_t, "correlationId": corr, "base": base})
        return cerrar(200, {"idOperacion": resp["idOperacion"], "monto": monto, "billetes": billetes,
                            "saldoDisponible": resp["saldoDisponible"], "confirmado": ce == 200},
                      "DISPENSADA", billetes=",".join(f"{b['cantidad']}x{b['denominacion']}" for b in billetes))
    causa = "ATASCO" if modo == "atasco" else "TIMEOUT_DISPENSADOR"
    e2, r2 = extornar(corr, uuid_t, causa, base)
    if e2 == 200 and r2.get("estado") == "EXTORNADA":
        return cerrar(502, {"codigo": "FALLA_DISPENSADOR", "mensaje": "No se entrego el efectivo; el debito fue extornado",
                            "idContraAsiento": r2.get("idContraAsiento"), "saldoDisponible": r2.get("saldoDisponible")},
                      "EXTORNADA", codigo=causa, contraAsiento=r2.get("idContraAsiento"))
    with candado:
        pendientes.append({"tipo": "EXTORNO", "uuidTransaccion": uuid_t, "motivo": causa, "correlationId": corr, "base": base})
    return cerrar(502, {"codigo": "FALLA_DISPENSADOR", "mensaje": "Operacion pendiente de reversion"},
                  "PENDIENTE_REVERSION", codigo=causa)


def conciliar():
    """Reintenta los extornos y confirmaciones que no llegaron."""
    resultado = []
    with candado:
        lista = list(pendientes)
    for p in lista:
        corr = p["correlationId"]
        if p["tipo"] == "EXTORNO":
            est, resp = extornar(corr, p["uuidTransaccion"], p["motivo"], p.get("base"))
            ok = est == 200
            if ok:
                registrar(corr, p["uuidTransaccion"], "CONCILIACION", "EXTORNADA",
                          contraAsiento=resp.get("idContraAsiento"))
                with candado:
                    if p["uuidTransaccion"] in operaciones:
                        h, c = operaciones[p["uuidTransaccion"]]
                        operaciones[p["uuidTransaccion"]] = (h, dict(c, estado="EXTORNADA", mensaje="Extorno completado"))
        else:
            est, _, _ = llamar_bus("/confirmar-dispensacion", {"idCajero": ID_CAJERO, "uuidTransaccion": p["uuidTransaccion"],
                                                               "resultado": "DISPENSADO"}, corr, p["uuidTransaccion"], base=p.get("base"))
            ok = est == 200
            if ok:
                registrar(corr, p["uuidTransaccion"], "CONCILIACION", "DISPENSADA")
        if ok:
            with candado:
                pendientes.remove(p)
        resultado.append({"tipo": p["tipo"], "uuidTransaccion": p["uuidTransaccion"], "resuelto": ok})
    return {"procesados": len(resultado), "detalle": resultado, "pendientes": len(pendientes)}


def estado():
    with candado:
        return {"terminal": ID_CAJERO, "bandejas": {m: {str(k): v for k, v in d.items()} for m, d in bandejas.items()},
                "pendientes": list(pendientes), "pruebas": dict(pruebas) if PRUEBAS else None}


def leer_registro(n):
    try:
        lineas = REGISTRO.read_text(encoding="utf-8").splitlines()[-n:]
    except OSError:
        return []
    return [json.loads(x) for x in lineas]


class Pantalla(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def json(self, codigo, datos):
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        ruta = self.path.split("?")[0]
        if ruta == "/api/config":
            return self.json(200, {"pruebas": PRUEBAS, "idCajero": ID_CAJERO})
        if ruta == "/api/estado":
            return self.json(200, estado())
        if ruta == "/api/registro":
            n = 30
            if "n=" in self.path:
                try:
                    n = max(1, min(500, int(self.path.split("n=")[1].split("&")[0])))
                except ValueError:
                    pass
            return self.json(200, leer_registro(n))
        super().do_GET()

    def do_POST(self):
        ruta = self.path.split("?")[0]
        corr = self.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        try:
            n = int(self.headers.get("Content-Length", "0"))
            datos = json.loads(self.rfile.read(n)) if n else {}
            if not isinstance(datos, dict):
                raise ValueError
        except (ValueError, UnicodeError):
            return self.json(400, {"codigo": "SOLICITUD_INVALIDA"})
        if ruta == "/api/retiro":
            h, c = retirar(datos, corr)
            return self.json(h, c)
        if ruta == "/api/registrar":      # eventos de la pantalla (clave y consulta), sin datos sensibles
            cod = datos.get("codigo")
            registrar(str(datos.get("correlationId", corr)), str(datos.get("uuidTransaccion", "-")),
                      str(datos.get("tipo", "EVENTO"))[:20], str(datos.get("estado", "-"))[:30],
                      tarjeta="****" + str(datos.get("tarjeta", ""))[-4:],
                      codigo=str(cod)[:40] if cod else None,
                      ms=datos.get("ms") if isinstance(datos.get("ms"), int) else None)
            return self.json(200, {"ok": True})
        if ruta == "/api/conciliar":
            return self.json(200, conciliar())
        if ruta == "/api/reponer":
            with candado:
                reiniciar_bandejas()
            registrar(corr, "-", "REPOSICION", "COMPLETADA")
            return self.json(200, estado())
        if ruta == "/api/desbloquear":      # solo demostracion: limpia bloqueos e intentos en Tarjetas
            if not PRUEBAS:
                return self.json(403, {"codigo": "MODO_PRUEBA_DESACTIVADO"})
            try:
                req = urllib.request.Request(TARJETAS_BASE + "/tarjetas/simulacion/reiniciar", data=b"{}", method="POST",
                                             headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=ESPERA).read()
            except (urllib.error.URLError, OSError):
                return self.json(502, {"codigo": "TARJETAS_NO_DISPONIBLE"})
            registrar(corr, "-", "DESBLOQUEO", "COMPLETADO")
            return self.json(200, {"estado": "DESBLOQUEADAS"})
        if ruta == "/api/pruebas":
            if not PRUEBAS:
                return self.json(403, {"codigo": "MODO_PRUEBA_DESACTIVADO"})
            if datos.get("reiniciar") is True:
                with candado:
                    reiniciar_bandejas(); operaciones.clear(); pendientes.clear()
                    pruebas.update(dispensador="normal", perderRespuestaBus=False)
            if isinstance(datos.get("bandejas"), dict):          # fija los contadores (para probar billetes agotados)
                with candado:
                    for m, d in datos["bandejas"].items():
                        if m in bandejas and isinstance(d, dict):
                            for den, cant in d.items():
                                if int(den) in bandejas[m] and isinstance(cant, int) and cant >= 0:
                                    bandejas[m][int(den)] = cant
            if datos.get("dispensador") in ("normal", "atasco", "sin_respuesta"):
                pruebas["dispensador"] = datos["dispensador"]
            if isinstance(datos.get("perderRespuestaBus"), bool):
                pruebas["perderRespuestaBus"] = datos["perderRespuestaBus"]
            return self.json(200, estado())
        self.json(404, {"codigo": "RUTA_NO_ENCONTRADA"})


if __name__ == "__main__":
    print(f"{ahora()} INFO  atm      pantalla en http://localhost:{PUERTO}  bus={BUS_BASE}"
          + ("  MODO PRUEBA" if PRUEBAS else ""), flush=True)
    try:
        ThreadingHTTPServer(("0.0.0.0", PUERTO), partial(Pantalla, directory=str(QUIEN))).serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
    except OSError as e:
        print(f"no se pudo abrir el puerto: {e.strerror}", flush=True)
        sys.exit(1)
