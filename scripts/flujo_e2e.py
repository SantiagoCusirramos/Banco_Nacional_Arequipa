"""Flujo de extremo a extremo del producto integrado.

Corre dentro del contenedor del Bus (`./bna smoke`), así que llega al frontend por su
nombre en la red interna y solo usa la biblioteca estándar.

Pasos: salud de cada servicio, login del administrador, registro de un cliente,
apertura de dos cuentas para él, depósito, transferencia, repetición idempotente,
saldos finales, movimientos de la cuenta, cuentas del cliente y bitácora por
COREDB; después, las mismas cuentas por el módulo CUENTAS, una tarjeta por el
módulo TARJETAS (con un retiro autorizado y extornado), una solicitud de crédito
por EVALUACIÓN (expediente con el formato de SOL → evaluación → decisión, todo en
COREDB), su desembolso por DESEMBOLSO (identidad → orden → validación → confirmación,
que abona una sola vez y crea el crédito), un prospecto captado y habilitado por
CAPTACION (expediente en COREDB, cliente nuevo y referencia CR-INT-01 para SOL) y todo
por los puentes del frontend, que es el camino que sigue el navegador.

Todo pasa por el Bus de Servicios: el flujo solo conoce el Bus (E2E_BUS, con su credencial
BUS_TOKEN) y el frontend, y al final comprueba con las métricas del Bus que el flujo y cada
puente del frontend llegaron a los módulos a través de él, y que cada módulo que usa COREDB
(CUENTAS, TARJETAS, CAPTACION, EVALUACION, DESEMBOLSO) llegó a COREDB por el Bus (fase 2).
"""

import datetime
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import date, timedelta
from decimal import Decimal

# Todo pasa por el Bus de Servicios: el flujo solo conoce la dirección del Bus y la del
# frontend (que también llega a los módulos por el Bus). Ningún módulo se llama directo.
BUS = os.environ.get("E2E_BUS", "http://127.0.0.1:8018").rstrip("/")
TOKEN_BUS = os.environ.get("BUS_TOKEN", "")
COREDB = f"{BUS}/bus/coredb"
CUENTAS = f"{BUS}/bus/cuentas"
TARJETAS = f"{BUS}/bus/tarjetas"
SOL = f"{BUS}/bus/sol"
EVALUACION = f"{BUS}/bus/evaluacion"
DESEMBOLSO = f"{BUS}/bus/desembolso"
CAPTACION = f"{BUS}/bus/captacion"
SEGURIDAD = f"{BUS}/bus/seguridad"
FRONTEND = os.environ.get("E2E_FRONTEND", "http://frontend:3000")
TOKEN_SOL = os.environ.get("CAP_SOL_TOKEN", "")
SERVICIOS = {
    "Bus de Servicios": (BUS + "/salud", {}),
    "COREDB": (COREDB + "/coredb/salud", {}),
    "CUENTAS": (CUENTAS + "/health", {}),
    "TARJETAS": (TARJETAS + "/health", {}),
    "ATM": (f"{BUS}/bus/atm/health", {}),
    "SOL": (SOL + "/ready", {}),
    "EVALUACIÓN": (EVALUACION + "/salud", {}),
    "DESEMBOLSO": (DESEMBOLSO + "/salud", {}),
    "CAPTACION": (CAPTACION + "/ready", {}),
    "Seguridad": (SEGURIDAD + "/seguridad/estado", {"X-Correlation-ID": "flujo-e2e"}),
    "frontend": (FRONTEND + "/login", {}),
}
# Intentos de la primera consulta a cada servicio. En Kubernetes un pod recién listo
# puede tardar un momento en recibir tráfico de su Service (`./bna k8s-smoke` pide 5).
INTENTOS = max(1, int(os.environ.get("E2E_INTENTOS", "1")))
ESPERA = float(os.environ.get("E2E_ESPERA", "2"))
USUARIO = os.environ.get("BNA_ADMIN_USUARIO", "admin")
PASSWORD = os.environ.get("BNA_ADMIN_PASSWORD", "")
SOL_USUARIO = "asesor.bna"  # usuario sembrado por SOL (backend/SOL/seed.py)
SOL_PASSWORD = os.environ.get("SOL_INITIAL_PASSWORD", "")
TOKEN_SOL_EVALUACION = os.environ.get("EVALUACION_TOKEN_SOL", "")
AGENCIA = "AQP01"
CANAL = "HB"


class Fallo(Exception):
    pass


def pedir(metodo, url, cuerpo=None, token=None, cabeceras=None):
    """Devuelve (estado, cuerpo JSON o texto). No lanza por un 4xx o 5xx."""
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    peticion = urllib.request.Request(url, data=datos, method=metodo)
    if datos is not None:
        peticion.add_header("Content-Type", "application/json")
    if token:
        peticion.add_header("Authorization", f"Bearer {token}")
    if url.startswith(BUS + "/") and TOKEN_BUS:
        peticion.add_header("X-Bus-Token", TOKEN_BUS)
    for nombre, valor in (cabeceras or {}).items():
        peticion.add_header(nombre, valor)
    try:
        with urllib.request.urlopen(peticion, timeout=15) as respuesta:
            estado, texto = respuesta.status, respuesta.read().decode()
    except urllib.error.HTTPError as error:
        estado, texto = error.code, error.read().decode()
    except (urllib.error.URLError, OSError) as error:
        raise Fallo(f"{metodo} {url}: sin respuesta ({error})") from error
    try:
        return estado, json.loads(texto)
    except ValueError:
        return estado, texto


def pedir_navegador(metodo, ruta, cuerpo=None, origen=FRONTEND, cookie=None):
    """Como el navegador ante el proxy de SOL del frontend: Origin y cookie, sin token.
    Devuelve (estado, cuerpo JSON o texto, Set-Cookie)."""
    peticion = urllib.request.Request(f"{FRONTEND}/api/solicitud-credito/{ruta}", method=metodo,
                                      data=json.dumps(cuerpo).encode() if cuerpo is not None else None)
    peticion.add_header("Content-Type", "application/json")
    if metodo != "GET":
        peticion.add_header("Origin", origen)
    if cookie:
        peticion.add_header("Cookie", cookie)
    try:
        with urllib.request.urlopen(peticion, timeout=15) as respuesta:
            estado, texto, galleta = respuesta.status, respuesta.read().decode(), respuesta.headers.get("Set-Cookie", "")
    except urllib.error.HTTPError as error:
        estado, texto, galleta = error.code, error.read().decode(), error.headers.get("Set-Cookie", "")
    except (urllib.error.URLError, OSError) as error:
        raise Fallo(f"{metodo} {ruta} por el proxy de SOL: sin respuesta ({error})") from error
    try:
        return estado, json.loads(texto), galleta
    except ValueError:
        return estado, texto, galleta


def sano(nombre, url, cabeceras):
    """Exige un 200; reintenta INTENTOS veces si no hay respuesta o no es 200."""
    for intento in range(1, INTENTOS + 1):
        try:
            estado, _ = pedir("GET", url, cabeceras=cabeceras)
            error = None if estado == 200 else f"{nombre} no está sano: {url} respondió {estado}"
        except Fallo as fallo:
            error = str(fallo)
        if error is None:
            return
        if intento < INTENTOS:
            print(f"  ..  {error}; nuevo intento en {ESPERA:g} s", flush=True)
            time.sleep(ESPERA)
    raise Fallo(error)


def exigir(condicion, mensaje):
    if not condicion:
        raise Fallo(mensaje)


def paso(texto):
    print(f"  ok  {texto}", flush=True)


def coredb(metodo, ruta, esperado, cuerpo=None, token=None):
    estado, respuesta = pedir(metodo, COREDB + ruta, cuerpo, token)
    exigir(estado == esperado, f"{metodo} {ruta}: se esperaba {esperado} y respondió {estado}: {respuesta}")
    return respuesta


def sobre_sol(cod_cliente, monto="15000.00", plazo=12):
    """Un expediente CR-INT-02 con la forma que arma SOL: calendario con amortización
    constante y 1 % de interés mensual, cuadrado al céntimo."""
    monto, centimo = Decimal(monto), Decimal("0.01")
    amortizacion = (monto / plazo).quantize(centimo)
    saldo, cuotas, inicio = monto, [], date.today() + timedelta(days=30)
    for n in range(1, plazo + 1):
        capital = saldo if n == plazo else amortizacion
        interes = (saldo * Decimal("0.01")).quantize(centimo)
        cuotas.append({"numero_cuota": n, "fecha_vencimiento": (inicio + timedelta(days=30 * (n - 1))).isoformat(),
                       "saldo_inicial": str(saldo), "amortizacion": str(capital), "interes": str(interes),
                       "cuota_total": str(capital + interes), "saldo_final": str(saldo - capital)})
        saldo -= capital
    total = sum(Decimal(c["cuota_total"]) for c in cuotas)
    return {
        "versionContrato": "CR-INT-02-PROPUESTA-v2", "idSolicitud": str(uuid.uuid4()), "versionSolicitud": 1,
        "idOperacion": str(uuid.uuid4()), "idCorrelacion": str(uuid.uuid4()), "simulado": False,
        "actorEnvio": "flujo-e2e",
        "expediente": {
            "cliente": {"id_cliente": cod_cliente},
            "condiciones": {"id_cliente": cod_cliente, "monto_solicitado": str(monto), "moneda": "PEN",
                            "plazo_meses": plazo, "destino_credito": "Flujo de extremo a extremo", "pago_doble": False},
            "politica": {"tea": "0.1268", "amortizacion": "FRANCES"},
            "calendario": {"cuotas": cuotas, "total_pagar": str(total)},
        },
    }


def metricas_bus():
    estado, respuesta = pedir("GET", BUS + "/metricas")
    exigir(estado == 200, f"Métricas del Bus: {estado} {respuesta}")
    return respuesta["reenvios"]


def flujo():
    exigir(PASSWORD, "Falta BNA_ADMIN_PASSWORD")
    exigir(TOKEN_BUS, "Falta BUS_TOKEN (credencial del flujo ante el Bus)")

    # Las métricas del Bus se acumulan desde que arrancó: se compara con lo de antes del flujo.
    sano("Bus de Servicios", BUS + "/salud", {})
    inicio_bus = metricas_bus()
    for nombre, (url, cabeceras) in SERVICIOS.items():
        sano(nombre, url, cabeceras)
        paso(f"{nombre} responde")

    # ── El Bus: sin su credencial no reenvía; con ella, el error del módulo llega igual ──
    peticion = urllib.request.Request(COREDB + "/coredb/salud")
    try:
        with urllib.request.urlopen(peticion, timeout=15) as respuesta:
            estado, texto = respuesta.status, respuesta.read().decode()
    except urllib.error.HTTPError as error:
        estado, texto = error.code, error.read().decode()
    exigir(estado == 401 and "BUS_CREDENCIAL_INVALIDA" in texto,
           f"El Bus sin credencial debía responder 401: {estado} {texto}")
    paso("Bus de Servicios: sin su credencial responde 401 y no reenvía")

    estado, _ = pedir("GET", COREDB + "/coredb/auth/me")
    exigir(estado == 401, f"COREDB sin token debía responder 401 y respondió {estado}")
    paso("COREDB rechaza una petición sin token (su 401 llega igual por el Bus)")

    sesion = coredb("POST", "/coredb/auth/login", 200, {"username": USUARIO, "password": PASSWORD})
    token = sesion["access_token"]
    perfil = coredb("GET", "/coredb/auth/me", 200, token=token)
    exigir(perfil["rol"] == "ADMINISTRADOR", f"El usuario {USUARIO} no es administrador")
    paso(f"login de {USUARIO} (ADMINISTRADOR)")

    # Datos nuevos en cada corrida, para poder repetirla sobre la misma base. Una persona
    # registra OBSERVADO: HABILITADO es del módulo Clientes, que verifica la identidad.
    base = int(time.time() * 1000) % 10**15 * 10
    sufijo = f"{random.randrange(10**8):08d}"
    registrado = coredb("POST", "/coredb/clientes", 201, {
        "tipo_documento": "DNI", "numero_documento": sufijo,
        "nombres": "Cliente", "apellido_paterno": "De Prueba", "apellido_materno": None,
        "correo": f"flujo-{base}@example.com", "celular": "9" + sufijo,
        "version_contrato": "v1", "estado_habilitante": "OBSERVADO",
    }, token)
    cliente = registrado["cod_cliente"]
    vista = coredb("GET", f"/coredb/clientes/{cliente}", 200, token=token)
    exigir(vista["estado_cliente"] == "OBSERVADO" and vista["permite_operar"] is True,
           f"El cliente registrado no puede operar: {vista}")
    paso(f"cliente {cliente} registrado (OBSERVADO, puede operar)")

    cuentas = []
    for indice in (1, 2):
        numero = base + indice
        cuenta = coredb("POST", "/coredb/cuentas", 201, {
            "num_cuenta": f"CTA-{numero:016d}",
            "cci": f"{numero:020d}",
            "moneda": "PEN",
            "regimen": "INDIVIDUAL",
            "id_agencia": AGENCIA,
            "titulares": [cliente],
        }, token)
        cuentas.append(cuenta["num_cuenta"])
    origen, destino = cuentas
    paso(f"dos cuentas abiertas para {cliente}: {origen} y {destino}")

    coredb("POST", "/coredb/movimientos", 201, {
        "num_cuenta": origen, "tipo": "DEPOSITO", "monto": "500.00",
        "glosa": "Depósito del flujo de extremo a extremo", "id_canal": CANAL,
        "idempotency_key": str(uuid.uuid4()),
    }, token)
    paso(f"depósito de 500.00 en {origen}")

    transferencia = {
        "origen": origen, "destino": destino, "monto": "200.00",
        "glosa": "Transferencia del flujo de extremo a extremo", "id_canal": CANAL,
        "idempotency_key": str(uuid.uuid4()),
    }
    primera = coredb("POST", "/coredb/movimientos/transferencias", 201, transferencia, token)
    exigir(primera["repetido"] is False, "La primera transferencia no debía ser una repetición")
    paso(f"transferencia de 200.00 de {origen} a {destino}")

    estado, segunda = pedir("POST", COREDB + "/coredb/movimientos/transferencias", transferencia, token)
    exigir(estado in (200, 201) and segunda["repetido"] is True
           and segunda["uuid_debito"] == primera["uuid_debito"],
           f"Repetir la transferencia con la misma llave debía devolver la original: {estado} {segunda}")
    paso("la misma llave de idempotencia no mueve el dinero dos veces")

    saldos = {numero: coredb("GET", f"/coredb/cuentas/{numero}", 200, token=token)["saldo_disponible"]
              for numero in cuentas}
    exigir(float(saldos[origen]) == 300.0 and float(saldos[destino]) == 200.0,
           f"Saldos inesperados: {saldos}")
    paso(f"saldos finales: {origen} = {saldos[origen]}, {destino} = {saldos[destino]}")

    movimientos = coredb("GET", f"/coredb/movimientos/cuenta/{origen}", 200, token=token)
    leidos = [(m["tipo_operacion"], m["naturaleza"], m["monto"]) for m in movimientos]
    exigir(leidos == [("TRANSFERENCIA_ENVIADA", "D", "200.00"), ("DEPOSITO", "C", "500.00")],
           f"Movimientos inesperados en {origen}: {leidos}")
    paso(f"movimientos de {origen}: la transferencia enviada y el depósito")

    del_cliente = coredb("GET", f"/coredb/cuentas?cod_cliente={cliente}", 200, token=token)
    exigir(sorted(c["num_cuenta"] for c in del_cliente) == sorted(cuentas),
           f"Cuentas inesperadas de {cliente}: {del_cliente}")
    paso(f"las dos cuentas figuran como cuentas de {cliente}")

    # La bitácora tiene el evento de cada paso, con el usuario que lo hizo.
    esperados = [
        ("cliente", cliente, "REGISTRAR_CLIENTE"),
        ("cuenta_ahorro", origen, "ABRIR_CUENTA"),
        ("movimiento", primera["uuid_debito"], "TRANSFERENCIA"),
    ]
    for entidad, id_entidad, accion in esperados:
        eventos = coredb(
            "GET", f"/coredb/auditoria?entidad={entidad}&id_entidad={id_entidad}&accion={accion}",
            200, token=token,
        )
        exigir(len(eventos) == 1 and eventos[0]["actor"] == USUARIO,
               f"La bitácora no tiene un evento {accion} de {USUARIO} para {id_entidad}: {eventos}")
    paso(f"la bitácora registra el cliente, la cuenta y la transferencia, a nombre de {USUARIO}")

    # ── Por el módulo CUENTAS, que reenvía el token a COREDB ────────────────
    base = CUENTAS + "/api/v1/cuentas"
    estado, _ = pedir("GET", f"{base}/{origen}")
    exigir(estado == 401, f"CUENTAS sin token debía responder 401 y respondió {estado}")
    estado, respuesta = pedir("GET", f"{base}/{origen}", token=token)
    exigir(estado == 200 and respuesta["data"]["saldo_disponible"] == "300.00"
           and respuesta["data"]["titulares"] == [cliente],
           f"CUENTAS no devolvió la cuenta esperada: {estado} {respuesta}")
    estado, respuesta = pedir(
        "POST", f"{base}/deposito", {"num_cuenta": origen, "monto": "50.00"}, token,
        cabeceras={"X-Idempotency-Key": str(uuid.uuid4()), "X-Channel-ID": "VEN",
                   "X-Request-Timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
    )
    exigir(estado == 201 and respuesta["success"] is True, f"Depósito por CUENTAS: {estado} {respuesta}")
    estado, respuesta = pedir("GET", f"{base}/{origen}/movimientos", token=token)
    exigir(estado == 200 and respuesta["data"][0]["tipo_operacion"] == "DEPOSITO"
           and respuesta["data"][0]["monto"] == "50.00",
           f"Movimientos por CUENTAS: {estado} {respuesta}")
    estado, respuesta = pedir("GET", f"{base}/consolidada/{cliente}", token=token)
    exigir(estado == 200 and sorted(c["num_cuenta"] for c in respuesta["data"]) == sorted(cuentas),
           f"Consolidada por CUENTAS: {estado} {respuesta}")
    paso("CUENTAS: cuenta, depósito de 50.00, movimientos y consolidada del cliente")

    # ── Por el módulo TARJETAS, que reenvía el token a COREDB ───────────────
    # Solo se emite a un cliente ACTIVO (ERR-TAR-001) y el registrado arriba está OBSERVADO:
    # la tarjeta es del cliente de desarrollo DEV001, sobre una cuenta nueva suya.
    numero = int(time.time() * 1000) % 10**15 * 10 + 3
    titular = "DEV001"
    cuenta_tarjeta, otra_cuenta = (coredb("POST", "/coredb/cuentas", 201, {
        "num_cuenta": f"CTA-{n:016d}", "cci": f"{n:020d}", "moneda": "PEN",
        "regimen": "INDIVIDUAL", "id_agencia": AGENCIA, "titulares": [titular],
    }, token)["num_cuenta"] for n in (numero, numero + 10))
    base = TARJETAS + "/api/v1/tarjetas"
    estado, _ = pedir("GET", f"{base}/cliente/{titular}")
    exigir(estado == 401, f"TARJETAS sin token debía responder 401 y respondió {estado}")
    estado, respuesta = pedir("POST", f"{base}/emision", {"cod_cliente": cliente, "num_cuenta": origen}, token,
                              cabeceras={"X-Idempotency-Key": str(uuid.uuid4())})
    exigir(estado == 400 and respuesta["error_code"] == "ERR-TAR-001",
           f"TARJETAS debía rechazar la emisión a un cliente OBSERVADO: {estado} {respuesta}")
    estado, respuesta = pedir("GET", f"{base}/cliente/{titular}", token=token)
    exigir(estado == 200, f"Tarjetas del cliente por TARJETAS: {estado} {respuesta}")
    antes = len(respuesta["data"])
    emision = {"cod_cliente": titular, "num_cuenta": cuenta_tarjeta}
    llave = {"X-Idempotency-Key": str(uuid.uuid4())}
    estado, respuesta = pedir("POST", f"{base}/emision", emision, token, cabeceras=llave)
    exigir(estado == 201 and respuesta["data"]["estado_tarjeta"] == "PENDIENTE_ACTIVACION",
           f"Emisión por TARJETAS: {estado} {respuesta}")
    tarjeta = respuesta["data"]["id_tarjeta"]
    estado, respuesta = pedir("POST", f"{base}/emision", emision, token, cabeceras=llave)
    exigir(estado == 201 and respuesta["data"]["id_tarjeta"] == tarjeta,
           f"Repetir la emisión con la misma llave debía devolver la misma tarjeta: {estado} {respuesta}")
    estado, respuesta = pedir("POST", f"{base}/emision", {**emision, "num_cuenta": otra_cuenta}, token,
                              cabeceras=llave)
    exigir(estado == 409 and respuesta["error_code"] == "ERR-TAR-IDEMPOTENCIA",
           f"La misma llave con otra cuenta del cliente debía responder 409: {estado} {respuesta}")
    estado, respuesta = pedir("POST", f"{base}/{tarjeta}/estado", {"estado": "ACTIVA"}, token)
    exigir(estado == 200 and respuesta["data"]["estado_tarjeta"] == "ACTIVA",
           f"Activación por TARJETAS: {estado} {respuesta}")
    # Un retiro en el cajero de desarrollo: se autoriza y retiene el saldo, la misma llave no
    # lo retiene dos veces y el extorno lo libera (RN-ATM-003).
    coredb("POST", "/coredb/movimientos", 201, {
        "num_cuenta": cuenta_tarjeta, "tipo": "DEPOSITO", "monto": "100.00",
        "glosa": "Depósito para el retiro con tarjeta", "id_canal": CANAL,
        "idempotency_key": str(uuid.uuid4()),
    }, token)
    retiro = {"num_cuenta": cuenta_tarjeta, "tipo_operacion": "RETIRO", "monto": "40.00",
              "id_terminal": "DEV-ATM-01"}
    llave_retiro = {"X-Idempotency-Key": str(uuid.uuid4())}
    estado, respuesta = pedir("POST", f"{base}/{tarjeta}/autorizaciones", retiro, token, cabeceras=llave_retiro)
    exigir(estado == 201 and respuesta["data"]["aprobada"] is True
           and respuesta["data"]["codigo_respuesta"] == "00",
           f"Autorización del retiro por TARJETAS: {estado} {respuesta}")
    autorizacion = respuesta["data"]["uuid_autorizacion"]
    estado, respuesta = pedir("POST", f"{base}/{tarjeta}/autorizaciones", retiro, token, cabeceras=llave_retiro)
    exigir(estado == 201 and respuesta["data"]["uuid_autorizacion"] == autorizacion,
           f"Repetir la autorización con la misma llave debía devolver la misma: {estado} {respuesta}")
    disponible = coredb("GET", f"/coredb/cuentas/{cuenta_tarjeta}", 200, token=token)["saldo_disponible"]
    exigir(float(disponible) == 60.0, f"La autorización debía retener 40.00 una sola vez: disponible {disponible}")
    estado, respuesta = pedir("POST", f"{base}/autorizaciones/{autorizacion}/extorno",
                              {"motivo": "Prueba del flujo"}, token)
    exigir(estado == 200 and respuesta["data"]["estado_autorizacion"] == "EXTORNADA"
           and respuesta["data"]["codigo_respuesta"] == "EXT",
           f"Extorno por TARJETAS: {estado} {respuesta}")
    disponible = coredb("GET", f"/coredb/cuentas/{cuenta_tarjeta}", 200, token=token)["saldo_disponible"]
    exigir(float(disponible) == 100.0, f"El extorno debía liberar el saldo retenido: disponible {disponible}")
    paso(f"TARJETAS: retiro de 40.00 en el cajero DEV-ATM-01 autorizado (00) y retenido una sola vez "
         "con la misma llave, y extornado (saldo liberado)")
    estado, respuesta = pedir("POST", f"{base}/{tarjeta}/bloqueo", {"motivo": "Prueba del flujo"}, token)
    exigir(estado == 200 and respuesta["data"]["estado_tarjeta"] == "BLOQUEADA",
           f"Bloqueo por TARJETAS: {estado} {respuesta}")
    estado, respuesta = pedir("POST", f"{base}/{tarjeta}/estado", {"estado": "ACTIVA"}, token)
    exigir(estado == 403 and respuesta["error_code"] == "ERR-TAR-DESBLOQUEO-NO-PERMITIDO",
           f"El desbloqueo por TARJETAS debía responder 403: {estado} {respuesta}")
    estado, respuesta = pedir("GET", f"{base}/cliente/{titular}", token=token)
    exigir(estado == 200 and tarjeta in [t["id_tarjeta"] for t in respuesta["data"]],
           f"Tarjetas del cliente por TARJETAS: {estado} {respuesta}")
    exigir(len(respuesta["data"]) == antes + 1,
           f"Dos envíos con la misma llave debían dejar una sola tarjeta nueva: {antes} -> {len(respuesta['data'])}")
    paso(f"TARJETAS: emisión a {titular} (no a un cliente OBSERVADO), repetición con la misma llave "
         "sin duplicar, 409 con la misma llave y otra cuenta, activación, bloqueo, desbloqueo rechazado y tarjetas del cliente")

    # ── ATM: retiro por el cajero (valida PIN → autoriza → confirma) ──────────
    # Usa la misma tarjeta DEV001 que TARJETAS, sobre la cuenta_tarjeta ya existente.
    atm_base = f"{BUS}/bus/atm/api"
    # Primero validar PIN (el ATM llama a TARJETAS por el Bus)
    pin_key = {"X-Idempotency-Key": str(uuid.uuid4())}
    estado, respuesta = pedir("POST", f"{atm_base}/validar-pin",
                              {"id_tarjeta": tarjeta, "pin": "4821", "id_terminal": "ATM-AQP-001"},
                              token, cabeceras=pin_key)
    exigir(estado == 200 and respuesta["success"] is True
           and respuesta["data"]["resultado"] == "EXITOSO",
           f"ATM validar PIN: {estado} {respuesta}")
    paso("ATM: PIN validado correctamente por TARJETAS a través del Bus")

    # Autorizar retención
    retiro_atm = {"id_tarjeta": tarjeta, "num_cuenta": cuenta_tarjeta, "moneda": "PEN",
                  "monto": "30.00", "id_terminal": "ATM-AQP-001",
                  "uuid_transaccion": str(uuid.uuid4())}
    llave_atm = {"X-Idempotency-Key": str(uuid.uuid4())}
    estado, respuesta = pedir("POST", f"{atm_base}/autorizar", retiro_atm, token, cabeceras=llave_atm)
    exigir(estado == 201 and respuesta["success"] is True
           and respuesta["data"]["aprobada"] is True
           and respuesta["data"]["codigo_respuesta"] == "00",
           f"ATM autorizar retiro: {estado} {respuesta}")
    autorizacion_atm = respuesta["data"]["uuid_autorizacion"]
    paso(f"ATM: retiro de 30.00 autorizado (00) y retenido, uuid_autorizacion={autorizacion_atm[:8]}…")

    # Confirmar dispensación
    confirmar_atm = {"uuid_autorizacion": autorizacion_atm, "id_terminal": "ATM-AQP-001",
                     "resultado": "DISPENSADO"}
    llave_conf = {"X-Idempotency-Key": str(uuid.uuid4())}
    estado, respuesta = pedir("POST", f"{atm_base}/confirmar", confirmar_atm, token, cabeceras=llave_conf)
    exigir(estado == 200 and respuesta["success"] is True
           and respuesta["data"]["estado_autorizacion"] == "DISPENSADA",
           f"ATM confirmar dispensación: {estado} {respuesta}")
    uuid_txn = respuesta["data"].get("uuid_transaccion")
    paso(f"ATM: dispensación confirmada, uuid_transaccion={uuid_txn}")

    # Verificar que el saldo bajó una sola vez
    saldo_despues = coredb("GET", f"/coredb/cuentas/{cuenta_tarjeta}", 200, token=token)["saldo_disponible"]
    # La cuenta tenía 100.00, se autorizó 40.00 (extornado en TARJETAS) = 100.00, luego 30.00 = 70.00
    exigir(float(saldo_despues) == 70.0, f"El saldo debía bajar 30.00 una sola vez: disponible {saldo_despues}")
    paso(f"ATM: retiro de 30.00 en el cajero ATM-AQP-001 confirmado, saldo final {saldo_despues}")

    # Repetir confirmación con misma llave → sin segundo débito (idempotencia)
    estado, respuesta = pedir("POST", f"{atm_base}/confirmar", confirmar_atm, token, cabeceras=llave_conf)
    exigir(estado == 200 and respuesta["success"] is True
           and respuesta["data"]["uuid_transaccion"] == uuid_txn,
           f"ATM repetir confirmación: {estado} {respuesta}")
    saldo_otra = coredb("GET", f"/coredb/cuentas/{cuenta_tarjeta}", 200, token=token)["saldo_disponible"]
    exigir(float(saldo_otra) == 70.0, f"Repetir confirmación no debía debitar de nuevo: {saldo_otra}")
    paso("ATM: repetir confirmación con misma llave no debita dos veces (idempotencia)")

    # ── EVALUACIÓN: expediente de SOL → evaluación → decisión, todo en COREDB ──
    exigir(TOKEN_SOL_EVALUACION, "Falta EVALUACION_TOKEN_SOL para enviar el expediente a Evaluación")
    base = EVALUACION + "/eva"

    def enviar_expediente(sobre):
        return pedir("POST", f"{base}/applications", sobre, TOKEN_SOL_EVALUACION,
                     cabeceras={"X-Idempotency-Key": sobre["idOperacion"], "X-Correlation-ID": sobre["idCorrelacion"]})

    sobre = sobre_sol(cliente)
    estado, _ = pedir("POST", f"{base}/applications", sobre, token,
                      cabeceras={"X-Idempotency-Key": sobre["idOperacion"]})
    exigir(estado == 401, f"Evaluación debía rechazar un expediente sin el token de SOL: {estado}")
    estado, acuse = enviar_expediente(sobre)
    exigir(estado == 201 and acuse["idSolicitud"] == sobre["idSolicitud"] and acuse["ronda"] == 1
           and acuse["acuse"] == f"ACK-{acuse['idEvaluacion']}",
           f"Expediente de SOL por Evaluación: {estado} {acuse}")
    estado, repetido = enviar_expediente(sobre)
    exigir(estado == 200 and repetido == acuse, f"Repetir el expediente debía devolver el mismo acuse: {estado} {repetido}")
    solicitud = sobre["idSolicitud"]
    en_core = coredb("GET", f"/coredb/creditos/solicitudes/{solicitud}", 200, token=token)
    exigir(en_core["estado"] == "EN_EVALUACION" and en_core["codCliente"] == cliente
           and len(en_core["calendario"]["cuotas"]) == 12 and en_core["historial"][-1]["actor"] == "svc-evaluacion",
           f"La solicitud en COREDB no es la esperada: {en_core}")
    situacion = {"versionSolicitud": 1, "ingresoMensual": "5000.00", "deudaMensual": "0.00", "riesgo": "BUENO",
                 "verificada": True}
    estado, resultado = pedir("POST", f"{base}/v1/solicitudes/{solicitud}/evaluaciones", situacion, token)
    exigir(estado == 200 and resultado["resultado"] == "APROBADO" and resultado["estadoSolicitud"] == "APROBADA"
           and resultado["idEvaluacion"] == acuse["idEvaluacion"],
           f"Evaluación por la regla: {estado} {resultado}")
    aprobaciones = coredb("GET", f"/coredb/creditos/aprobaciones?idSolicitud={solicitud}", 200, token=token)
    exigir([a["idEvaluacion"] for a in aprobaciones] == [acuse["idEvaluacion"]],
           f"La aprobación debía quedar disponible para Desembolso: {aprobaciones}")
    detalle = coredb("GET", f"/coredb/creditos/solicitudes/{solicitud}", 200, token=token)
    exigir(detalle["historial"][-1]["actor"] == USUARIO,
           f"El historial debía registrar a {USUARIO}, que evaluó con su token: {detalle['historial']}")
    paso(f"EVALUACIÓN: expediente de SOL registrado en COREDB (acuse {acuse['acuse'][:12]}…, repetición sin "
         f"duplicar), evaluado por {USUARIO} con su token y APROBADO por la regla; la aprobación queda para Desembolso")

    sobre = sobre_sol(cliente)
    enviar_expediente(sobre)
    observada = sobre["idSolicitud"]
    estado, resultado = pedir("POST", f"{base}/v1/solicitudes/{observada}/evaluaciones",
                              {**situacion, "ingresoMensual": "4000.00"}, token)
    exigir(estado == 200 and resultado["resultado"] == "OBSERVADO" and resultado["estadoSolicitud"] == "EN_EVALUACION",
           f"La zona gris de la regla debía quedar OBSERVADO: {estado} {resultado}")
    decision = f"{base}/v1/evaluaciones/{resultado['idEvaluacion']}/decision"
    estado, _ = pedir("POST", decision, {"decision": "OBSERVADO", "comentario": "Precisar el destino declarado."}, token)
    exigir(estado == 422, f"El analista no devuelve la solicitud a SOL (T1): respondió {estado}")
    estado, respuesta = pedir("POST", decision, {"decision": "APROBADO", "comentario": "Sustento revisado."}, token)
    exigir(estado == 422 and respuesta["error"]["code"] == "ANALISTA_REQUERIDO",
           f"Decidir exige un analista registrado (el administrador no tiene empleado): {estado} {respuesta}")
    paso("EVALUACIÓN: un caso OBSERVADO espera al analista; no se devuelve a SOL (T1) y decidir exige un "
         "analista registrado")

    # El administrador da de alta al analista por la API: usuario ANALISTA, empleado ligado a
    # él (POST /coredb/empleados, solo ADMINISTRADOR) y registro como analista de crédito.
    analista = "an" + uuid.uuid4().hex[:12]
    clave_analista = "clave-" + uuid.uuid4().hex
    usuario_analista = coredb("POST", "/coredb/usuarios", 201, {
        "username": analista, "nombre": "Analista del flujo", "password": clave_analista, "rol": "ANALISTA"}, token)
    token_an = coredb("POST", "/coredb/auth/login", 200,
                      {"username": analista, "password": clave_analista})["access_token"]
    alta_empleado = {"codigo_empleado": "EMP-" + uuid.uuid4().hex[:10].upper(), "nombre_completo": "Analista del flujo",
                     "cargo": "ANALISTA", "id_agencia": AGENCIA, "id_usuario": usuario_analista["id_usuario"]}
    coredb("POST", "/coredb/empleados", 403, alta_empleado, token_an)
    empleado = coredb("POST", "/coredb/empleados", 201, alta_empleado, token)
    exigir(empleado["id_usuario"] == usuario_analista["id_usuario"] and "nombre_completo" not in empleado,
           f"El empleado debía quedar ligado al usuario, sin repetir el nombre: {empleado}")
    ligado = coredb("GET", f"/coredb/usuarios/{usuario_analista['id_usuario']}", 200, token=token)
    exigir(ligado["id_empleado"] == empleado["id_empleado"], f"El usuario debía quedar ligado al empleado: {ligado}")
    coredb("POST", "/coredb/empleados", 409, {**alta_empleado, "id_usuario": None}, token)
    id_analista = coredb("POST", "/coredb/creditos/analistas", 201,
                         {"idEmpleado": empleado["id_empleado"]}, token)["idAnalista"]
    estado, decidida = pedir("POST", decision, {"decision": "APROBADO", "comentario": "Sustento revisado y suficiente."},
                             token_an)
    exigir(estado == 200 and decidida["decision"] == "APROBADO" and decidida["estadoSolicitud"] == "APROBADA",
           f"Decisión del analista por Evaluación: {estado} {decidida}")
    detalle = coredb("GET", f"/coredb/creditos/solicitudes/{observada}", 200, token=token)
    ultima = detalle["evaluaciones"][-1]
    exigir(detalle["estado"] == "APROBADA" and ultima["decision"] == "APROBADO" and ultima["idAnalista"] == id_analista
           and detalle["historial"][-1]["actor"] == analista,
           f"La decisión debía quedar en COREDB a nombre del analista: {detalle}")
    paso(f"EVALUACIÓN: el administrador registra al empleado {empleado['codigo_empleado']} ligado a {analista} "
         f"(ANALISTA; él mismo no puede: 403; código repetido: 409) y lo registra como analista {id_analista}; "
         "el analista decide el caso OBSERVADO con su token: APROBADA")

    estado, respuesta = pedir("GET", f"{FRONTEND}/api/evaluacion/solicitudes/{solicitud}", token=token)
    exigir(estado == 200 and respuesta["estado"] == "APROBADA", f"Puente a Evaluación: {estado} {respuesta}")
    paso("frontend: su puente llega a Evaluación con el token del usuario")

    # ── Por el módulo DESEMBOLSO, con el token de un operador ───────────────
    # La verificación del documento solo aprueba a un cliente ACTIVO: el cliente del flujo se
    # registró OBSERVADO (lo habilita el módulo Clientes, que no está), así que lo activa el
    # administrador. El abono va a una cuenta nueva, para no tocar los saldos de arriba.
    coredb("POST", f"/coredb/clientes/{cliente}/estado", 200,
           {"estado": "ACTIVO", "motivo": "Identidad confirmada en ventanilla (flujo de extremo a extremo)."}, token)
    operador = "op" + uuid.uuid4().hex[:12]
    clave_operador = "clave-" + uuid.uuid4().hex
    coredb("POST", "/coredb/usuarios", 201, {"username": operador, "nombre": "Operador del flujo",
                                             "password": clave_operador, "rol": "OPERADOR"}, token)
    token_op = coredb("POST", "/coredb/auth/login", 200,
                      {"username": operador, "password": clave_operador})["access_token"]
    n = int(time.time() * 1000) % 10**15 * 10 + 5
    abono = coredb("POST", "/coredb/cuentas", 201, {
        "num_cuenta": f"CTA-{n:016d}", "cci": f"{n:020d}", "moneda": "PEN", "regimen": "INDIVIDUAL",
        "id_agencia": AGENCIA, "titulares": [cliente]}, token)["num_cuenta"]
    des = DESEMBOLSO + "/api/v1"

    estado, verificacion = pedir("POST", f"{des}/identidad", {"tipoDocumento": "DNI", "numeroDocumento": sufijo,
                                                              "identidadVerificada": True}, token_op)
    exigir(estado == 201 and verificacion["resultado"] == "APROBADO" and verificacion["codCliente"] == cliente,
           f"Verificación del documento por Desembolso: {estado} {verificacion}")
    estado, aprobaciones = pedir("GET", f"{des}/aprobaciones?codCliente={cliente}", token=token_op)
    exigir(estado == 200 and {a["idEvaluacion"] for a in aprobaciones} == {acuse["idEvaluacion"], ultima["idEvaluacion"]},
           f"Desembolso debía leer de COREDB las dos aprobaciones (regla y analista): {estado} {aprobaciones}")
    estado, cuentas_abono = pedir("GET", f"{des}/clientes/{cliente}/cuentas?moneda=PEN", token=token_op)
    exigir(estado == 200 and {c["numCuenta"] for c in cuentas_abono if c["elegible"]} >= {abono},
           f"La cuenta nueva debía admitir el abono: {estado} {cuentas_abono}")
    llave = {"X-Idempotency-Key": str(uuid.uuid4())}
    pedido = {"idEvaluacion": acuse["idEvaluacion"], "numCuenta": abono}
    estado, orden = pedir("POST", f"{des}/ordenes", pedido, token_op, cabeceras=llave)
    exigir(estado == 201 and orden["estado"] == "PREPARADA" and orden["importe"] == "15000.00"
           and orden["usuarioPreparacion"] == operador, f"Orden de desembolso: {estado} {orden}")
    estado, repetida = pedir("POST", f"{des}/ordenes", pedido, token_op, cabeceras=llave)
    exigir(estado == 200 and repetida["idOrden"] == orden["idOrden"],
           f"La misma llave debía devolver la misma orden: {estado} {repetida}")
    id_orden = orden["idOrden"]
    estado, validada = pedir("POST", f"{des}/ordenes/{id_orden}/validaciones", {
        "tipo": "IDENTIDAD", "resultado": "APROBADA", "referenciaEvidencia": str(verificacion["idValidacion"])},
        token_op)
    exigir(estado == 201 and validada["estado"] == "VALIDADA", f"Identidad de la orden: {estado} {validada}")
    estado, confirmada = pedir("POST", f"{des}/ordenes/{id_orden}/confirmacion", token=token_op)
    exigir(estado == 201 and confirmada["estado"] == "CONFIRMADA" and confirmada["codCredito"].startswith("CRE-"),
           f"Confirmación del desembolso: {estado} {confirmada}")
    estado, otra = pedir("POST", f"{des}/ordenes/{id_orden}/confirmacion", token=token_op)
    exigir(estado == 200 and otra["codCredito"] == confirmada["codCredito"]
           and otra["uuidTransaccionAbono"] == confirmada["uuidTransaccionAbono"],
           f"Confirmar otra vez debía devolver lo mismo: {estado} {otra}")
    saldo_abono = coredb("GET", f"/coredb/cuentas/{abono}", 200, token=token)["saldo_disponible"]
    abonos = coredb("GET", f"/coredb/movimientos/cuenta/{abono}", 200, token=token)
    exigir(saldo_abono == "15000.00" and len(abonos) == 1,
           f"El abono debía hacerse una sola vez: saldo {saldo_abono}, movimientos {abonos}")
    credito = coredb("GET", f"/coredb/creditos/{confirmada['codCredito']}", 200, token=token)
    exigir(credito["estado"] == "AL_DIA" and credito["codCliente"] == cliente and len(credito["cuotas"]) == 12,
           f"El crédito debía nacer AL_DIA con sus 12 cuotas: {credito}")
    desembolsada = coredb("GET", f"/coredb/creditos/solicitudes/{solicitud}", 200, token=token)
    exigir(desembolsada["estado"] == "DESEMBOLSADA" and desembolsada["calendario"]["tipo"] == "OFICIAL",
           f"La solicitud debía quedar DESEMBOLSADA con su calendario OFICIAL: {desembolsada['estado']}")
    estado, sin_aprobaciones = pedir("GET", f"{des}/aprobaciones?codCliente={cliente}", token=token_op)
    exigir(estado == 200 and [a["idEvaluacion"] for a in sin_aprobaciones] == [ultima["idEvaluacion"]],
           f"Solo debía quedar la aprobación del analista: {sin_aprobaciones}")
    paso(f"DESEMBOLSO: {operador} (OPERADOR) verifica el documento, prepara la orden {orden['codigoOrden']} "
         f"(repetición sin duplicar), la valida y la confirma: abono único de 15000.00, crédito "
         f"{confirmada['codCredito']} AL_DIA con calendario OFICIAL y solicitud DESEMBOLSADA; confirmar otra vez "
         "no abona de nuevo")

    estado, respuesta = pedir("GET", f"{FRONTEND}/api/desembolso/ordenes/{id_orden}", token=token_op)
    exigir(estado == 200 and respuesta["estado"] == "CONFIRMADA", f"Puente a Desembolso: {estado} {respuesta}")
    paso("frontend: su puente llega a Desembolso con el token del operador")

    # ── COBRANZA: cobrar una cuota del crédito recién creado ────────────────
    cobranza = f"{BUS}/bus/cobranza"
    saldo_antes = coredb("GET", f"/coredb/cuentas/{abono}", 200, token=token)["saldo_disponible"]
    referencia_pago = f"PAGO-E2E-{uuid.uuid4().hex[:8]}"
    # La primera cuota del crédito de 15000.00 a 12 meses: amortización constante 1250.00, interés 150.00 = 1400.00
    monto_cuota = "1400.00"

    def cobranza_pago(token_pago, referencia, monto=monto_cuota):
        estado, respuesta = pedir("POST", f"{cobranza}/api/v1/creditos/{confirmada['codCredito']}/pagos",
                                  {"numCuenta": abono, "monto": monto, "referencia": referencia, "canal": "VEN"},
                                  token_pago)
        return estado, respuesta

    # Primer pago con el token del operador
    estado, pago = cobranza_pago(token_op, referencia_pago)
    exigir(estado == 201, f"COBRANZA primer pago: {estado} {pago}")
    exigir(pago["estado"] == "CONFIRMADO" and pago["referencia"] == referencia_pago
           and pago["monto"] == monto_cuota and pago["numCuenta"] == abono
           and len(pago["aplicaciones"]) == 1 and pago["aplicaciones"][0]["montoAplicado"] == monto_cuota,
           f"Pago no tiene la forma esperada: {pago}")
    # El saldo de la cuenta debe haber bajado exactamente una vez
    saldo_despues = coredb("GET", f"/coredb/cuentas/{abono}", 200, token=token)["saldo_disponible"]
    exigir(float(saldo_despues) == float(saldo_antes) - float(monto_cuota),
           f"El saldo debía bajar {monto_cuota}: {saldo_antes} -> {saldo_despues}")
    paso(f"COBRANZA: {operador} cobró la cuota 1 ({monto_cuota}) del crédito {confirmada['codCredito']}, "
         f"saldo de {abono}: {saldo_antes} -> {saldo_despues}")

    # Repetir con la misma referencia y el mismo cuerpo → 200, saldo no cambia
    estado, repetido = cobranza_pago(token_op, referencia_pago)
    exigir(estado == 200 and repetido["idPago"] == pago["idPago"],
           f"Repetir con la misma referencia debía devolver el mismo pago: {estado} {repetido}")
    saldo_otra_vez = coredb("GET", f"/coredb/cuentas/{abono}", 200, token=token)["saldo_disponible"]
    exigir(saldo_otra_vez == saldo_despues,
           f"El saldo no debía cambiar al repetir el pago: {saldo_despues} -> {saldo_otra_vez}")
    paso("COBRANZA: la misma referencia con el mismo cuerpo no cobra dos veces (idempotencia)")

    # Comprobar el pago por referencia
    estado, comprobante = pedir("GET", f"{cobranza}/api/v1/pagos/{referencia_pago}", token=token_op)
    exigir(estado == 200 and comprobante["idPago"] == pago["idPago"],
           f"Consulta por referencia: {estado} {comprobante}")
    paso("COBRANZA: el comprobante del pago se recupera por referencia")

    # Verificar que el crédito en COREDB refleja el pago
    credito = coredb("GET", f"/coredb/creditos/{confirmada['codCredito']}", 200, token=token)
    exigir(credito["cuotas"][0]["estado"] == "PAGADA" and credito["cuotasPagadas"] == 1,
           f"El crédito debía tener la cuota 1 PAGADA: {credito}")
    paso(f"COREDB: el crédito {confirmada['codCredito']} tiene la cuota 1 PAGADA y cuotasPagadas = 1")

    # ── CAPTACION: un prospecto, de la solicitud a cliente habilitado ──────
    exigir(TOKEN_SOL, "Falta CAP_SOL_TOKEN")
    cap = CAPTACION + "/api/v1/captacion"
    dni = "4" + "".join(random.choices("0123456789", k=6)) + "1"  # termina en 1: central NORMAL

    def captacion(metodo, ruta, esperado, cuerpo=None):
        estado, respuesta = pedir(metodo, cap + ruta, cuerpo, token)
        exigir(estado == esperado, f"CAPTACION {metodo} {ruta}: se esperaba {esperado} y respondió {estado}: {respuesta}")
        return respuesta["data"]

    solicitante = captacion("POST", "/solicitantes", 201, {
        "tipo_documento": "DNI", "numero_documento": dni, "nombres": "Rosa", "apellido_paterno": "Huamán",
        "apellido_materno": "Ccori", "celular": "9" + "".join(random.choices("0123456789", k=8)),
        "correo": f"captacion.{dni}.{uuid.uuid4().hex[:6]}@example.com"})["solicitante"]
    caso = captacion("POST", "/casos", 201, {"id_solicitante": solicitante["id_solicitante"],
                                             "canal": "AGENCIA", "id_agencia": AGENCIA})["id_caso"]
    estado, respuesta = pedir("POST", f"{cap}/casos/{caso}/habilitar", token=token)
    exigir(estado == 400 and respuesta.get("error_code") == "ERR-CAP-CASO-NO-LISTO",
           f"Habilitar sin requisitos debía responder 400 ERR-CAP-CASO-NO-LISTO: {estado} {respuesta}")
    captacion("POST", f"/casos/{caso}/consentimientos", 201, {"consentimientos": [
        {"tipo": t, "aceptado": True} for t in ("TRATAMIENTO_DATOS", "CONSULTA_BUROS", "TERMINOS")]})
    codigo = captacion("POST", f"/casos/{caso}/otp", 201, {"canal": "SMS"})["codigo_simulado"]
    exigir(captacion("POST", f"/casos/{caso}/otp/verificar", 200, {"codigo": codigo})["verificado"],
           "CAPTACION no aceptó el código OTP que acaba de generar")
    captacion("POST", f"/casos/{caso}/validaciones", 201, {"tipos": ["RENIEC", "LISTAS_NEGRAS", "PEP"]})
    captacion("POST", f"/casos/{caso}/consultas-riesgo", 201, {"central": "SBS"})
    captacion("POST", f"/casos/{caso}/perfil", 201)
    expediente = captacion("GET", f"/casos/{caso}", 200)
    exigir(expediente["estado"] == "APROBADO", f"El caso debía quedar APROBADO: {expediente}")
    habilitado = captacion("POST", f"/casos/{caso}/habilitar", 200)
    cod_cliente = habilitado["cod_cliente"]
    exigir(habilitado["estado"] == "HABILITADO" and habilitado["cliente_nuevo"],
           f"El caso debía quedar HABILITADO con un cliente nuevo: {habilitado}")
    exigir(captacion("POST", f"/casos/{caso}/habilitar", 200)["cod_cliente"] == cod_cliente,
           "Repetir la habilitación debía devolver el mismo cliente")
    paso("CAPTACION: solicitante, caso, consentimientos, OTP, RENIEC/listas/PEP, central, perfil y "
         "habilitación; habilitar sin requisitos se rechaza y repetirla no duplica")

    cliente_cap = coredb("GET", f"/coredb/clientes/{cod_cliente}", 200, token=token)
    exigir(cliente_cap["numero_documento"] == dni and cliente_cap["estado_cliente"] == "ACTIVO"
           and cliente_cap["estado_habilitante"] == "HABILITADO",
           f"COREDB debía tener al cliente ACTIVO y HABILITADO: {cliente_cap}")
    paso(f"COREDB: CAPTACION registró al cliente {cod_cliente}, ACTIVO y HABILITADO")

    # Lo que consulta SOL (CR-INT-01), con las reglas de backend/SOL/integrations.py.
    estado, referencia = pedir("GET", f"{CAPTACION}/cap/references/{cod_cliente}", token=TOKEN_SOL)
    exigir(estado == 200, f"CR-INT-01: la referencia respondió {estado}: {referencia}")
    requeridos = ["id_cliente", "numero_documento", "nombres", "apellido_paterno", "apellido_materno",
                  "estado_cliente", "id_caso", "id_verificacion", "fecha_verificacion", "vigente_hasta",
                  "estado_habilitante", "version_contrato"]
    vacios = [k for k in requeridos if not isinstance(referencia.get(k), str) or not referencia[k].strip()]
    exigir(not vacios, f"CR-INT-01: campos vacíos en la referencia: {vacios}")
    hoy_lima = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=5)).date()
    exigir(referencia["id_cliente"] == cod_cliente and referencia["id_caso"] == caso
           and referencia["estado_cliente"] == "ACTIVO" and referencia["estado_habilitante"] == "HABILITADO"
           and referencia["id_verificacion"] == cliente_cap["id_verificacion_captacion"]
           and datetime.date.fromisoformat(referencia["fecha_verificacion"]) <= hoy_lima
           <= datetime.date.fromisoformat(referencia["vigente_hasta"]),
           f"CR-INT-01: la referencia no habilita según las reglas de SOL: {referencia}")
    exigir("celular" not in referencia and "correo" not in referencia,
           "CR-INT-01: la referencia no debe llevar datos de contacto")
    estado, _ = pedir("GET", f"{CAPTACION}/cap/references/{cod_cliente}", token=token)
    exigir(estado == 401, f"CR-INT-01 con un token de persona debía responder 401 y respondió {estado}")
    estado, lista = pedir("GET", f"{CAPTACION}/cap/references?search={dni}&limit=50", token=TOKEN_SOL)
    exigir(estado == 200 and [r["id_cliente"] for r in lista] == [cod_cliente],
           f"CR-INT-01: la búsqueda debía encontrar al cliente: {estado} {lista}")
    paso("CR-INT-01: SOL recibe una referencia vigente y HABILITADA, con su búsqueda; un token de persona no entra")

    # ── Por los puentes del frontend, como lo hace el navegador ─────────────
    estado, respuesta = pedir("GET", f"{FRONTEND}/api/core/coredb/auth/me", token=token)
    exigir(estado == 200 and respuesta["username"] == USUARIO, f"Puente a COREDB: {estado} {respuesta}")
    estado, respuesta = pedir("GET", f"{FRONTEND}/api/cuenta/{origen}", token=token)
    exigir(estado == 200 and respuesta["data"]["saldo_disponible"] == "350.00",
           f"Puente a CUENTAS: {estado} {respuesta}")
    estado, respuesta = pedir("GET", f"{FRONTEND}/api/tarjeta/{tarjeta}", token=token)
    exigir(estado == 200 and respuesta["data"]["estado_tarjeta"] == "BLOQUEADA",
           f"Puente a TARJETAS: {estado} {respuesta}")
    estado, respuesta = pedir("GET", f"{FRONTEND}/api/captacion/casos/{caso}", token=token)
    exigir(estado == 200 and respuesta["data"]["cod_cliente"] == cod_cliente,
           f"Puente a CAPTACION: {estado} {respuesta}")
    estado, respuesta = pedir("GET", f"{FRONTEND}/api/cobranza/api/v1/creditos/{confirmada['codCredito']}", token=token)
    exigir(estado == 200 and respuesta["codCredito"] == confirmada['codCredito'],
           f"Puente a COBRANZA: {estado} {respuesta}")
    estado, _ = pedir("GET", f"{FRONTEND}/api/core/otra/ruta", token=token)
    exigir(estado == 404, f"El puente a COREDB solo debe reenviar /coredb: respondió {estado}")
    paso("frontend: sus puentes llegan a COREDB, a CUENTAS, a TARJETAS, a CAPTACION y a COBRANZA con el token del usuario")

    # ── SOL por el proxy del frontend: escribir exige el Origin del propio frontend ──
    exigir(SOL_PASSWORD, "Falta SOL_INITIAL_PASSWORD para entrar a SOL por el frontend")
    credenciales = {"username": SOL_USUARIO, "password": SOL_PASSWORD}
    estado, respuesta, _ = pedir_navegador("POST", "auth/login", credenciales, origen="http://otro.example")
    exigir(estado == 403, f"El proxy de SOL debía rechazar otro origen: {estado} {respuesta}")
    estado, respuesta, galleta = pedir_navegador("POST", "auth/login", credenciales)
    exigir(estado == 200 and respuesta.get("usuario", {}).get("rol") == "ASESOR" and "token" not in respuesta,
           f"Login de SOL por el proxy del frontend: {estado} {respuesta}")
    exigir(galleta.startswith("bna_sol_session=") and "httponly" in galleta.lower(),
           "El login de SOL debía dejar la sesión en una cookie HttpOnly")
    sesion = galleta.split(";", 1)[0]
    estado, respuesta, _ = pedir_navegador("GET", "policy", cookie=sesion)
    exigir(estado == 200 and respuesta.get("integracion") == "SIMULADO",
           f"Política de SOL con la cookie de sesión: {estado} {respuesta}")
    estado, respuesta, _ = pedir_navegador("POST", "auth/logout", {}, cookie=sesion)
    exigir(estado == 200, f"Cierre de sesión de SOL por el proxy: {estado} {respuesta}")
    estado, _, _ = pedir_navegador("GET", "policy", cookie=sesion)
    exigir(estado == 401, f"La sesión de SOL debía quedar revocada tras cerrar: respondió {estado}")
    paso("frontend: SOL por su proxy, con login desde el origen del frontend (otro origen, 403), "
         "sesión en cookie HttpOnly, consulta y cierre de sesión")

    # ── Todo pasó por el Bus: el flujo y cada puente del frontend ────────────
    despues = metricas_bus()

    def crecio(consumidor, modulo):
        return despues.get(consumidor, {}).get(modulo, 0) > inicio_bus.get(consumidor, {}).get(modulo, 0)

    faltan = [m for m in ("COREDB", "CUENTAS", "TARJETAS", "ATM", "SOL", "EVALUACION", "DESEMBOLSO", "CAPTACION", "COBRANZA")
              if not crecio("FRONTEND", m)]
    exigir(not faltan, f"Estos puentes del frontend no pasaron por el Bus: {faltan}")
    faltan = [m for m in ("COREDB", "CUENTAS", "TARJETAS", "ATM", "SOL", "EVALUACION", "DESEMBOLSO", "CAPTACION",
                          "SEGURIDAD") if not crecio("PRUEBAS", m)]
    exigir(not faltan, f"El flujo no llegó por el Bus a: {faltan}")
    # Fase 2: cada módulo llegó a COREDB a través del Bus, con su propia credencial.
    # ATM no llama a COREDB directo; llama a TARJETAS y CUENTAS por el Bus.
    faltan = [m for m in ("CUENTAS", "TARJETAS", "CAPTACION", "EVALUACION", "DESEMBOLSO", "COBRANZA")
              if not crecio(m, "COREDB")]
    exigir(not faltan, f"Estos módulos no llegaron a COREDB por el Bus: {faltan}")
    paso("Bus de Servicios: el flujo y los ocho puentes del frontend llegaron a los módulos por el Bus, "
         "y CUENTAS, TARJETAS, CAPTACION, EVALUACION, DESEMBOLSO y COBRANZA llegaron a COREDB por él")


if __name__ == "__main__":
    print("Flujo de extremo a extremo:")
    try:
        flujo()
    except Fallo as fallo:
        print(f"  FALLA  {fallo}", file=sys.stderr)
        sys.exit(1)
    print("Flujo completo.")
