"""Flujo de extremo a extremo del producto integrado.

Corre dentro del contenedor del Bus (`./bna smoke`), así que llega al frontend por su
nombre en la red interna y solo usa la biblioteca estándar.

Pasos: salud de cada servicio, login del administrador, registro de un cliente,
apertura de dos cuentas para él, depósito, transferencia, repetición idempotente,
saldos finales, movimientos de la cuenta, cuentas del cliente y bitácora por
COREDB; después, las mismas cuentas por el módulo CUENTAS, una tarjeta por el
módulo TARJETAS (con un retiro autorizado y extornado, y una retención que el cajero no
confirma y que COREDB libera pasado el plazo), una solicitud de crédito
por EVALUACIÓN (expediente con el formato de SOL → evaluación → decisión, todo en
COREDB), su desembolso por DESEMBOLSO (identidad → orden → validación → confirmación,
que abona una sola vez y crea el crédito), un prospecto captado y habilitado por
CAPTACION (expediente en COREDB, cliente nuevo y referencia CR-INT-01 para SOL), la
billetera Chaski (dos clientes de CAPTACION afiliados por el banco: envío por celular y pago
con QR, cada uno repetido con su llave, que mueven el dinero una sola vez) y todo por los
puentes del frontend, que es el camino que sigue el navegador.

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
BILLETERA = f"{BUS}/bus/billetera/api"
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
    "BILLETERA (Chaski)": (f"{BUS}/bus/billetera/api/salud", {}),
    "Seguridad": (SEGURIDAD + "/seguridad/estado", {"X-Correlation-ID": "flujo-e2e"}),
    "frontend": (FRONTEND + "/login", {}),
}
# Intentos de la primera consulta a cada servicio. En Kubernetes un pod recién listo
# puede tardar un momento en recibir tráfico de su Service (`./bna k8s-smoke` pide 5).
INTENTOS = max(1, int(os.environ.get("E2E_INTENTOS", "1")))
ESPERA = float(os.environ.get("E2E_ESPERA", "2"))
USUARIO = os.environ.get("BNA_ADMIN_USUARIO", "admin")
PASSWORD = os.environ.get("BNA_ADMIN_PASSWORD", "")
TOKEN_SOL_EVALUACION = os.environ.get("EVALUACION_TOKEN_SOL", "")
AGENCIA = "AQP01"
CANAL = "HB"


class Fallo(Exception):
    pass


# P-1: documentos, celulares, PIN, claves y tokens que la corrida envía o recibe. Al terminar se
# escriben en E2E_SENSIBLES y `./bna smoke` comprueba que ninguno quedó en los registros.
SENSIBLES = set()
CLAVES_SENSIBLES = {"numero_documento", "documento", "search", "texto", "celular", "celular_destino",
                    "pin", "password", "clave", "access_token", "token", "token_sesion"}


def anotar_sensibles(datos):
    if isinstance(datos, dict):
        for clave, valor in datos.items():
            if clave in CLAVES_SENSIBLES and isinstance(valor, str) and len(valor) >= 6:
                SENSIBLES.add(valor)
            else:
                anotar_sensibles(valor)
    elif isinstance(datos, list):
        for valor in datos:
            anotar_sensibles(valor)


def pedir(metodo, url, cuerpo=None, token=None, cabeceras=None):
    """Devuelve (estado, cuerpo JSON o texto). No lanza por un 4xx o 5xx."""
    anotar_sensibles(cuerpo)
    if token:
        SENSIBLES.add(token)
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
        datos = json.loads(texto)
    except ValueError:
        return estado, texto
    anotar_sensibles(datos)
    return estado, datos


def pedir_navegador(metodo, ruta, cuerpo=None, origen=FRONTEND, cookie=None, llave=None):
    """Como el navegador ante el proxy de SOL del frontend: Origin y cookie, sin token.
    Devuelve (estado, cuerpo JSON o texto, Set-Cookie)."""
    anotar_sensibles(cuerpo)
    peticion = urllib.request.Request(f"{FRONTEND}/api/solicitud-credito/{ruta}", method=metodo,
                                      data=json.dumps(cuerpo).encode() if cuerpo is not None else None)
    peticion.add_header("Content-Type", "application/json")
    if metodo != "GET":
        peticion.add_header("Origin", origen)
    if cookie:
        peticion.add_header("Cookie", cookie)
    if llave:
        peticion.add_header("X-Idempotency-Key", llave)
    try:
        with urllib.request.urlopen(peticion, timeout=15) as respuesta:
            estado, texto, galleta = respuesta.status, respuesta.read().decode(), respuesta.headers.get("Set-Cookie", "")
    except urllib.error.HTTPError as error:
        estado, texto, galleta = error.code, error.read().decode(), error.headers.get("Set-Cookie", "")
    except (urllib.error.URLError, OSError) as error:
        raise Fallo(f"{metodo} {ruta} por el proxy de SOL: sin respuesta ({error})") from error
    try:
        datos = json.loads(texto)
    except ValueError:
        return estado, texto, galleta
    anotar_sensibles(datos)
    return estado, datos, galleta


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
    estado, respuesta = pedir("GET", f"{base}/{origen}/movimientos", token=token)
    exigir(estado == 200, f"Movimientos por CUENTAS: {estado} {respuesta}")
    movimientos_antes = len(respuesta["data"])

    def operar_cuentas(operacion, cuerpo, llave):
        return pedir("POST", f"{base}/{operacion}", cuerpo, token, cabeceras={
            "X-Idempotency-Key": llave, "X-Channel-ID": "VEN",
            "X-Request-Timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})

    # Cada operación se repite con la misma llave, como un reintento de /cuenta tras un timeout:
    # debe devolver la misma transacción marcada como repetición, y el saldo cambia una sola vez.
    operaciones = [
        ("deposito", {"num_cuenta": origen, "monto": "50.00"}, "uuid_transaccion"),
        ("retiro", {"num_cuenta": origen, "monto": "20.00"}, "uuid_transaccion"),
        ("transferencia", {"num_cuenta_origen": destino, "num_cuenta_destino": origen, "monto": "20.00"}, "uuid_debito"),
    ]
    for operacion, cuerpo, campo in operaciones:
        llave = str(uuid.uuid4())
        estado, primera = operar_cuentas(operacion, cuerpo, llave)
        exigir(estado == 201 and primera["data"]["replay"] is False, f"{operacion} por CUENTAS: {estado} {primera}")
        estado, repetida = operar_cuentas(operacion, cuerpo, llave)
        exigir(estado == 201 and repetida["data"]["replay"] is True
               and repetida["data"][campo] == primera["data"][campo],
               f"Repetir {operacion} por CUENTAS con la misma llave debía devolver la original: {estado} {repetida}")
        estado, otra = operar_cuentas(operacion, {**cuerpo, "monto": "1.00"}, llave)
        exigir(estado == 409, f"La misma llave con otro monto debía dar 409 en {operacion}: {estado} {otra}")
    estado, respuesta = pedir("GET", f"{base}/{origen}/movimientos", token=token)
    exigir(estado == 200 and len(respuesta["data"]) == movimientos_antes + 3,
           f"Cada operación repetida debía dejar un solo movimiento en {origen}: {estado} {respuesta}")
    saldos = {numero: coredb("GET", f"/coredb/cuentas/{numero}", 200, token=token)["saldo_disponible"]
              for numero in cuentas}
    exigir(saldos == {origen: "350.00", destino: "180.00"},
           f"Saldos tras las operaciones repetidas por CUENTAS: {saldos}")
    estado, respuesta = pedir("GET", f"{base}/consolidada/{cliente}", token=token)
    exigir(estado == 200 and sorted(c["num_cuenta"] for c in respuesta["data"]) == sorted(cuentas),
           f"Consolidada por CUENTAS: {estado} {respuesta}")
    paso("CUENTAS: cuenta, depósito, retiro y transferencia repetidos con la misma llave (un solo movimiento "
         "cada uno; otro monto con la misma llave, 409), movimientos y consolidada del cliente")

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
    # Un retiro en el cajero de desarrollo: se autoriza, confirma (dispensa) y debita una vez.
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
    # Confirmar la autorización (el cajero dispensa)
    llave_confirma = str(uuid.uuid4())
    estado, respuesta = pedir("POST", f"{base}/autorizaciones/{autorizacion}/confirmacion",
                              {"id_terminal": "DEV-ATM-01"}, token, cabeceras={"X-Idempotency-Key": llave_confirma})
    exigir(estado == 200 and respuesta["data"]["estado_autorizacion"] == "DISPENSADA"
           and respuesta["data"]["uuid_transaccion"] == autorizacion,
           f"Confirmación por TARJETAS: {estado} {respuesta}")
    # Repetir la confirmación con la misma llave no debita dos veces
    estado, respuesta = pedir("POST", f"{base}/autorizaciones/{autorizacion}/confirmacion",
                              {"id_terminal": "DEV-ATM-01"}, token, cabeceras={"X-Idempotency-Key": llave_confirma})
    exigir(estado == 200 and respuesta["data"]["uuid_autorizacion"] == autorizacion,
           f"Repetir la confirmación con la misma llave debía devolver la misma: {estado} {respuesta}")
    disponible = coredb("GET", f"/coredb/cuentas/{cuenta_tarjeta}", 200, token=token)["saldo_disponible"]
    exigir(float(disponible) == 60.0, f"La confirmación repetida no debía debitar de nuevo: disponible {disponible}")
    # Extornar una confirmada debe fallar (la autorización ya tiene movimiento)
    estado, respuesta = pedir("POST", f"{base}/autorizaciones/{autorizacion}/extorno",
                              {"motivo": "Intento de extorno tras confirmar"}, token)
    exigir(estado == 409 and respuesta["error_code"] == "ERR-TAR-EXTORNO-NO-PERMITIDO",
           f"Extornar una confirmada debía fallar: {estado} {respuesta}")
    disponible = coredb("GET", f"/coredb/cuentas/{cuenta_tarjeta}", 200, token=token)["saldo_disponible"]
    exigir(float(disponible) == 60.0, f"El saldo no debía cambiar tras extorno fallido: disponible {disponible}")
    paso(f"TARJETAS: retiro de 40.00 en el cajero DEV-ATM-01 autorizado (00), confirmado (DISPENSADA) y debitado "
         "una sola vez con la misma llave de confirmación; extorno posterior rechazado")
    # ── ATM: retiro por el cajero (valida PIN → autoriza → confirma) ──────────
    # La tarjeta recién emitida y activada, sobre cuenta_tarjeta (60.00 tras el retiro de TARJETAS).
    atm_base = f"{BUS}/bus/atm/api"
    # La pantalla se sirve por el Bus y ninguna ruta lee fuera de static/ (K-1, S-1).
    estado, pantalla = pedir("GET", f"{BUS}/bus/atm/")
    exigir(estado == 200 and "Inserte su tarjeta" in str(pantalla), f"Pantalla del cajero: {estado}")
    for ruta in ("..%2Fconfig.py", "api/static/..%2Fconfig.py", "..%2F..%2F..%2F..%2Fproc%2Fself%2Fenviron"):
        estado, texto = pedir("GET", f"{BUS}/bus/atm/{ruta}")
        exigir(estado == 404 and "BaseSettings" not in str(texto) and "BUS_TOKEN" not in str(texto),
               f"El cajero no debe servir {ruta}: {estado}")
    estado, _ = pedir("GET", f"{atm_base}/registro")
    exigir(estado == 401, f"El registro del canal del cajero debía exigir al operador: {estado}")
    # El operador abre el cajero con su usuario de COREDB; con ese token lee el registro.
    estado, apertura = pedir("POST", f"{atm_base}/apertura", {"username": USUARIO, "password": PASSWORD})
    exigir(estado == 200 and apertura["data"]["access_token"], f"Apertura del cajero: {estado} {apertura}")
    token_operador = apertura["data"]["access_token"]
    estado, registro = pedir("GET", f"{atm_base}/registro", token=token_operador)
    exigir(estado == 200 and isinstance(registro, list), f"Registro del canal con el operador: {estado} {registro}")
    paso("ATM: la pantalla se sirve por el Bus, ninguna ruta lee fuera de static/; el operador abre el cajero y solo él lee el registro")
    estado, respuesta = pedir("PUT", f"{base}/{tarjeta}/credenciales/PIN_ATM", {"valor": "4821"}, token)
    exigir(estado == 200, f"Registrar el PIN por TARJETAS: {estado} {respuesta}")
    # Primero validar PIN (el ATM llama a TARJETAS por el Bus)
    pin_key = {"X-Idempotency-Key": str(uuid.uuid4())}
    estado, respuesta = pedir("POST", f"{atm_base}/validar-pin",
                              {"id_tarjeta": tarjeta, "pin": "4821", "id_terminal": "DEV-ATM-01"},
                              token, cabeceras=pin_key)
    exigir(estado == 200 and respuesta["success"] is True
           and respuesta["data"]["resultado"] == "EXITOSO" and respuesta["data"]["token_sesion"],
           f"ATM validar PIN: {estado} {respuesta}")
    sesion_atm = {"X-ATM-Sesion": respuesta["data"]["token_sesion"]}
    paso("ATM: PIN validado por TARJETAS a través del Bus; abre la sesión de la tarjeta")

    def saldo_atm():
        estado, respuesta = pedir("GET", f"{atm_base}/saldo?id_tarjeta={tarjeta}", token=token,
                                  cabeceras=sesion_atm)
        exigir(estado == 200 and respuesta["success"] is True, f"ATM consultar saldo: {estado} {respuesta}")
        return [(c["id_cuenta"], c["num_cuenta_enmascarado"], c["saldo_disponible"])
                for c in respuesta["data"]["lista_cuentas"]]

    # La consulta de saldo de la pantalla: TARJETAS (la cuenta de la tarjeta) y CUENTAS /consolidada.
    # El titular tiene otra cuenta, pero el cajero solo muestra la vinculada a la tarjeta.
    mostrado = saldo_atm()
    exigir(mostrado == [(cuenta_tarjeta, "****" + cuenta_tarjeta[-4:], "60.00")],
           f"El cajero debía mostrar solo la cuenta de la tarjeta con 60.00: {mostrado}")
    paso("ATM: consulta de saldo por la pantalla, solo la cuenta de la tarjeta (60.00)")

    # Autorizar retención
    retiro_atm = {"id_tarjeta": tarjeta, "num_cuenta": cuenta_tarjeta, "moneda": "PEN",
                  "monto": "30.00", "id_terminal": "DEV-ATM-01",
                  "uuid_transaccion": str(uuid.uuid4())}
    llave_atm = {"X-Idempotency-Key": str(uuid.uuid4())}
    # K-3: un token del personal sin la sesión del PIN no retira.
    estado, respuesta = pedir("POST", f"{atm_base}/autorizar", retiro_atm, token, cabeceras=llave_atm)
    exigir(estado == 401 and respuesta["error_code"] == "ERR-ATM-SESION-REQUERIDA",
           f"ATM autorizar sin la sesión del PIN debía responder 401: {estado} {respuesta}")
    estado, respuesta = pedir("POST", f"{atm_base}/autorizar", retiro_atm, token, cabeceras={**llave_atm, **sesion_atm})
    exigir(estado == 201 and respuesta["success"] is True
           and respuesta["data"]["aprobada"] is True
           and respuesta["data"]["codigo_respuesta"] == "00",
           f"ATM autorizar retiro: {estado} {respuesta}")
    autorizacion_atm = respuesta["data"]["uuid_autorizacion"]
    # Repetir la autorización con la misma llave devuelve la misma retención (no retiene dos veces).
    estado, repetida = pedir("POST", f"{atm_base}/autorizar", retiro_atm, token, cabeceras={**llave_atm, **sesion_atm})
    exigir(estado in (200, 201) and repetida["data"]["uuid_autorizacion"] == autorizacion_atm,
           f"ATM repetir autorización con la misma llave: {estado} {repetida}")
    paso(f"ATM: retiro de 30.00 autorizado (00) y retenido, uuid_autorizacion={autorizacion_atm[:8]}…")

    # Confirmar dispensación
    confirmar_atm = {"uuid_autorizacion": autorizacion_atm, "id_terminal": "DEV-ATM-01",
                     "resultado": "DISPENSADO"}
    llave_conf = {"X-Idempotency-Key": str(uuid.uuid4())}
    estado, respuesta = pedir("POST", f"{atm_base}/confirmar", confirmar_atm, token, cabeceras={**llave_conf, **sesion_atm})
    exigir(estado == 200 and respuesta["success"] is True
           and respuesta["data"]["estado_autorizacion"] == "DISPENSADA",
           f"ATM confirmar dispensación: {estado} {respuesta}")
    uuid_txn = respuesta["data"].get("uuid_transaccion")
    paso(f"ATM: dispensación confirmada, uuid_transaccion={uuid_txn}")

    # Verificar que el saldo bajó una sola vez
    saldo_despues = coredb("GET", f"/coredb/cuentas/{cuenta_tarjeta}", 200, token=token)["saldo_disponible"]
    # 60.00 tras el retiro de TARJETAS, menos los 30.00 del cajero.
    exigir(float(saldo_despues) == 30.0, f"El saldo debía bajar 30.00 una sola vez: disponible {saldo_despues}")
    mostrado = saldo_atm()
    exigir(mostrado == [(cuenta_tarjeta, "****" + cuenta_tarjeta[-4:], "30.00")],
           f"El cajero debía mostrar 30.00 tras el retiro: {mostrado}")
    paso(f"ATM: retiro de 30.00 en el cajero DEV-ATM-01 confirmado, saldo final {saldo_despues} (también en el cajero)")

    # Repetir confirmación con misma llave → sin segundo débito (idempotencia)
    estado, respuesta = pedir("POST", f"{atm_base}/confirmar", confirmar_atm, token, cabeceras={**llave_conf, **sesion_atm})
    exigir(estado == 200 and respuesta["success"] is True
           and respuesta["data"]["uuid_transaccion"] == uuid_txn,
           f"ATM repetir confirmación: {estado} {respuesta}")
    saldo_otra = coredb("GET", f"/coredb/cuentas/{cuenta_tarjeta}", 200, token=token)["saldo_disponible"]
    exigir(float(saldo_otra) == 30.0, f"Repetir confirmación no debía debitar de nuevo: {saldo_otra}")
    paso("ATM: repetir confirmación con misma llave no debita dos veces (idempotencia)")

    # Un cajero que cae entre autorizar y confirmar: la retención queda sin confirmar y la
    # base la libera pasado el plazo (bd-v1.11). Se comprueba al final del flujo.
    estado, respuesta = pedir("POST", f"{base}/{tarjeta}/autorizaciones", {**retiro, "monto": "10.00"}, token,
                              cabeceras={"X-Idempotency-Key": str(uuid.uuid4())})
    exigir(estado == 201 and respuesta["data"]["aprobada"] is True,
           f"Autorización que el cajero no confirmará: {estado} {respuesta}")
    retencion_huerfana = respuesta["data"]["uuid_autorizacion"]
    retenida_desde = time.monotonic()
    disponible = coredb("GET", f"/coredb/cuentas/{cuenta_tarjeta}", 200, token=token)["saldo_disponible"]
    exigir(float(disponible) == 20.0, f"La retención sin confirmar debía retener 10.00: disponible {disponible}")

    # Bloqueo desde el Home Banking: la misma petición que el botón «Bloquear» de /homebanking/cuentas.html,
    # por el puente del frontend → Bus → TARJETAS.
    estado, respuesta = pedir("POST", f"{FRONTEND}/api/tarjeta/{tarjeta}/bloqueo",
                              {"motivo": "Bloqueo solicitado por el cliente en Home Banking"}, token)
    exigir(estado == 200 and respuesta["data"]["estado_tarjeta"] == "BLOQUEADA",
           f"Bloqueo desde el Home Banking: {estado} {respuesta}")
    # El cajero deja de aceptarla: ni el PIN correcto abre sesión, ni la sesión abierta antes retira.
    estado, respuesta = pedir("POST", f"{atm_base}/validar-pin",
                              {"id_tarjeta": tarjeta, "pin": "4821", "id_terminal": "DEV-ATM-01"}, token)
    exigir(estado != 200 or respuesta["data"].get("resultado") != "EXITOSO",
           f"El cajero no debía aceptar la tarjeta bloqueada: {estado} {respuesta}")
    estado, respuesta = pedir("POST", f"{atm_base}/autorizar", {**retiro_atm, "uuid_transaccion": str(uuid.uuid4())},
                              token, cabeceras={"X-Idempotency-Key": str(uuid.uuid4()), **sesion_atm})
    exigir(not (estado == 201 and respuesta["data"].get("aprobada")),
           f"La sesión abierta antes del bloqueo no debía retirar: {estado} {respuesta}")
    disponible = coredb("GET", f"/coredb/cuentas/{cuenta_tarjeta}", 200, token=token)["saldo_disponible"]
    exigir(float(disponible) == 20.0, f"Con la tarjeta bloqueada no debía retenerse nada: disponible {disponible}")
    paso("Home Banking: «Bloquear» deja la tarjeta BLOQUEADA (puente del frontend → Bus → TARJETAS) y el cajero "
         "ya no la acepta (PIN rechazado; la sesión abierta antes no retira; saldo intacto)")
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

    celular_cap = "9" + "".join(random.choices("0123456789", k=8))
    solicitante = captacion("POST", "/solicitantes", 201, {
        "tipo_documento": "DNI", "numero_documento": dni, "nombres": "Rosa", "apellido_paterno": "Huamán",
        "apellido_materno": "Ccori", "celular": celular_cap,
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
    estado, lista = pedir("POST", f"{CAPTACION}/cap/references/search", {"search": dni, "limit": 50}, token=TOKEN_SOL)
    exigir(estado == 200 and [r["id_cliente"] for r in lista] == [cod_cliente],
           f"CR-INT-01: la búsqueda debía encontrar al cliente: {estado} {lista}")
    paso("CR-INT-01: SOL recibe una referencia vigente y HABILITADA, con su búsqueda; un token de persona no entra")

    # ── BILLETERA (Chaski): envío por celular y pago con QR, por el Bus ──────
    # Punto R-01: Chaski no crea clientes. Los dos son del flujo de Clientes (CAPTACION): el
    # que se acaba de habilitar y otro que pasa por el mismo expediente. El banco les abre una
    # cuenta y los afilia; desde ahí todo va por Chaski, que llega a COREDB por el Bus.
    def captar(nombres, apellido):
        dni_nuevo = "4" + "".join(random.choices("0123456789", k=6)) + "1"
        celular_nuevo = "9" + "".join(random.choices("0123456789", k=8))
        nuevo = captacion("POST", "/solicitantes", 201, {
            "tipo_documento": "DNI", "numero_documento": dni_nuevo, "nombres": nombres,
            "apellido_paterno": apellido, "apellido_materno": None, "celular": celular_nuevo,
            "correo": f"billetera.{dni_nuevo}.{uuid.uuid4().hex[:6]}@example.com"})["solicitante"]
        id_caso = captacion("POST", "/casos", 201, {"id_solicitante": nuevo["id_solicitante"],
                                                    "canal": "AGENCIA", "id_agencia": AGENCIA})["id_caso"]
        captacion("POST", f"/casos/{id_caso}/consentimientos", 201, {"consentimientos": [
            {"tipo": t, "aceptado": True} for t in ("TRATAMIENTO_DATOS", "CONSULTA_BUROS", "TERMINOS")]})
        otp = captacion("POST", f"/casos/{id_caso}/otp", 201, {"canal": "SMS"})["codigo_simulado"]
        captacion("POST", f"/casos/{id_caso}/otp/verificar", 200, {"codigo": otp})
        captacion("POST", f"/casos/{id_caso}/validaciones", 201, {"tipos": ["RENIEC", "LISTAS_NEGRAS", "PEP"]})
        captacion("POST", f"/casos/{id_caso}/consultas-riesgo", 201, {"central": "SBS"})
        captacion("POST", f"/casos/{id_caso}/perfil", 201)
        return captacion("POST", f"/casos/{id_caso}/habilitar", 200)["cod_cliente"], celular_nuevo

    beto, celular_beto = captar("Alberto", "Quispe")
    # Números de cuenta nuevos (más adelante que los del inicio del flujo).
    base_billetera = int(time.time() * 1000) % 10**15 * 10
    billeteras = {}
    for indice, (titular, cel, pin) in enumerate(((cod_cliente, celular_cap, "246810"),
                                                  (beto, celular_beto, "135790"))):
        numero = base_billetera + indice
        cuenta = coredb("POST", "/coredb/cuentas", 201, {
            "num_cuenta": f"CTA-{numero:016d}", "cci": f"{numero:020d}", "moneda": "PEN",
            "regimen": "INDIVIDUAL", "id_agencia": AGENCIA, "titulares": [titular]}, token)["num_cuenta"]
        afiliada = coredb("POST", "/coredb/billetera/afiliaciones", 201,
                          {"cod_cliente": titular, "num_cuenta": cuenta, "pin": pin}, token)
        exigir(afiliada["estado"] == "ACTIVA" and afiliada["nueva"] is True, f"Afiliación inesperada: {afiliada}")
        billeteras[titular] = {"cuenta": cuenta, "celular": cel, "pin": pin}
    rosa, alberto = billeteras[cod_cliente], billeteras[beto]
    coredb("POST", "/coredb/movimientos", 201, {
        "num_cuenta": rosa["cuenta"], "tipo": "DEPOSITO", "monto": "100.00", "glosa": "Fondeo de la billetera",
        "id_canal": "VEN", "idempotency_key": str(uuid.uuid4())}, token)
    paso(f"BILLETERA: el banco afilió a {cod_cliente} y a {beto} (clientes de CAPTACION) con su cuenta y su PIN; "
         f"depósito de 100.00 para {cod_cliente}")

    def chaski(metodo, ruta, esperado, cuerpo=None, sesion=None, cabeceras=None):
        estado, respuesta = pedir(metodo, BILLETERA + ruta, cuerpo, sesion, cabeceras)
        exigir(estado == esperado, f"Chaski {metodo} {ruta}: se esperaba {esperado} y respondió {estado}: {respuesta}")
        return respuesta

    chaski("POST", "/login", 401, {"celular": rosa["celular"], "pin": "000000"})
    estado, _ = pedir("POST", BILLETERA + "/registro", {"celular": "900000001", "pin": "123456"})
    exigir(estado == 403, f"Chaski no debe registrar clientes (R-01): respondió {estado}")
    s_rosa = chaski("POST", "/login", 200, {"celular": rosa["celular"], "pin": rosa["pin"]})["token"]
    s_alberto = chaski("POST", "/login", 200, {"celular": alberto["celular"], "pin": alberto["pin"]})["token"]
    estado, _ = pedir("GET", f"{COREDB}/coredb/catalogos/monedas", token=s_rosa)
    exigir(estado == 401, f"El token de cliente no debe servir como token del personal: respondió {estado}")
    contacto = chaski("POST", "/clientes/buscar", 200, {"celular": alberto["celular"]}, s_rosa)
    exigir(contacto["nombre"] == "Alberto Q.", f"Contacto inesperado: {contacto}")
    paso("BILLETERA: login con celular y PIN (PIN equivocado 401, registro 403 por R-01), el token de cliente "
         "no sirve como token del personal, y el contacto se ve solo con su nombre corto")

    llave_envio = {"Idempotency-Key": str(uuid.uuid4())}
    envio = {"celular_destino": alberto["celular"], "monto": 25, "referencia": "Pasaje"}
    primero = chaski("POST", "/transferencias", 200, envio, s_rosa, llave_envio)
    repetido = chaski("POST", "/transferencias", 200, envio, s_rosa, llave_envio)
    exigir(primero["repetida"] is False and repetido["repetida"] is True
           and repetido["id_transferencia"] == primero["id_transferencia"],
           f"Repetir el envío con la misma llave debía devolver el mismo: {primero} {repetido}")
    paso("BILLETERA: envío de 25.00 por celular; repetido con la misma llave devuelve el mismo envío")

    qr = chaski("POST", "/qr", 200, {"monto": 10}, s_alberto)
    visto = chaski("GET", f"/qr/{qr['id_qr']}", 200, sesion=s_rosa)
    exigir(visto["nombre"] == "Alberto Q." and visto["monto"] == 10 and visto["tipo"] == "dinamico",
           f"QR inesperado: {visto}")
    llave_qr = {"Idempotency-Key": str(uuid.uuid4())}
    pago = chaski("POST", f"/qr/{qr['id_qr']}/pagar", 200, {}, s_rosa, llave_qr)
    pago_repetido = chaski("POST", f"/qr/{qr['id_qr']}/pagar", 200, {}, s_rosa, llave_qr)
    exigir(pago_repetido["repetida"] is True and pago_repetido["id_pago"] == pago["id_pago"],
           f"Repetir el pago con la misma llave debía devolver el mismo: {pago} {pago_repetido}")
    chaski("POST", f"/qr/{qr['id_qr']}/pagar", 410, {}, s_rosa, {"Idempotency-Key": str(uuid.uuid4())})
    paso("BILLETERA: QR dinámico de 10.00 pagado; repetido con la misma llave devuelve el mismo pago y con otra "
         "llave se rechaza (410, ya pagado)")

    saldos = {nombre: coredb("GET", f"/coredb/cuentas/{datos['cuenta']}", 200, token=token)["saldo_disponible"]
              for nombre, datos in (("rosa", rosa), ("alberto", alberto))}
    exigir(saldos == {"rosa": "65.00", "alberto": "35.00"}, f"Saldos inesperados de la billetera: {saldos}")
    movimientos = coredb("GET", f"/coredb/movimientos/cuenta/{rosa['cuenta']}", 200, token=token)
    debitos = [(m["tipo_operacion"], m["monto"], m["id_canal"]) for m in movimientos if m["naturaleza"] == "D"]
    exigir(sorted(debitos) == [("TRANSFERENCIA_ENVIADA", "10.00", "BD"), ("TRANSFERENCIA_ENVIADA", "25.00", "BD")],
           f"Débitos inesperados en la cuenta de la billetera: {debitos}")
    yo = chaski("GET", "/me", 200, sesion=s_rosa)
    exigir(yo["cuenta"]["saldo_actual"] == 65 and yo["disponible_hoy"] == 465,
           f"La billetera debía mostrar 65.00 y 465.00 disponibles hoy: {yo}")
    paso(f"BILLETERA: el dinero se movió una sola vez por el canal BD: {cod_cliente} = {saldos['rosa']}, "
         f"{beto} = {saldos['alberto']}; dos débitos y el tope diario descontado")

    eventos = coredb("GET", "/coredb/auditoria?modulo=BILLETERA&limite=200", 200, token=token)
    acciones = {e["accion"] for e in eventos if e["id_entidad"] in (cod_cliente, beto) or e["actor"] in
                (f"cliente:{cod_cliente}", f"cliente:{beto}")}
    exigir({"AFILIAR", "VALIDAR_ACCESO", "OPERACION_P2P", "OPERACION_QR"} <= acciones,
           f"Faltan eventos de la billetera en la bitácora: {acciones}")
    texto = json.dumps([eventos, movimientos])
    exigir(rosa["celular"] not in texto and alberto["celular"] not in texto,
           "La bitácora o la glosa de los movimientos guardan un celular en claro")
    paso("BILLETERA: la bitácora tiene la afiliación, el acceso y las dos operaciones, sin ningún celular")

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
    # K-5: el Home Banking se sirve desde public/.
    estado, pagina = pedir("GET", f"{FRONTEND}/homebanking/index.html")
    exigir(estado == 200 and "formLogin" in str(pagina), f"Home Banking en /homebanking/index.html: {estado}")
    paso("frontend: sus puentes llegan a COREDB, a CUENTAS, a TARJETAS, a CAPTACION y a COBRANZA con el token del "
         "usuario, y sirve el Home Banking en /homebanking/index.html")

    # ── SOL sin base propia, por el proxy del frontend ──────────────────────
    # La asesora entra con su usuario de COREDB; el borrador queda en COREDB, el expediente va a
    # EVALUACION por el Bus y el resultado vuelve a SOL (CR-INT-03), que lo deja en la bitácora.
    asesora, clave_asesora = "as" + uuid.uuid4().hex[:12], "clave-" + uuid.uuid4().hex
    coredb("POST", "/coredb/usuarios", 201, {"username": asesora, "nombre": "Asesora del flujo",
                                             "password": clave_asesora, "rol": "ASESOR"}, token)
    credenciales = {"username": asesora, "password": clave_asesora}
    estado, respuesta, _ = pedir_navegador("POST", "auth/login", credenciales, origen="http://otro.example")
    exigir(estado == 403, f"El proxy de SOL debía rechazar otro origen: {estado} {respuesta}")
    estado, respuesta, galleta = pedir_navegador("POST", "auth/login", credenciales)
    exigir(estado == 200 and respuesta.get("usuario", {}).get("rol") == "ASESOR" and "token" not in respuesta,
           f"Login de SOL (usuario de COREDB) por el proxy del frontend: {estado} {respuesta}")
    exigir(galleta.startswith("bna_sol_session=") and "httponly" in galleta.lower(),
           "El login de SOL debía dejar la sesión en una cookie HttpOnly")
    sesion = galleta.split(";", 1)[0]
    SENSIBLES.add(sesion.split("=", 1)[1])
    estado, politica, _ = pedir_navegador("GET", "policy", cookie=sesion)
    exigir(estado == 200 and politica.get("integracion") == "REAL",
           f"Política de SOL con la cookie de sesión: {estado} {politica}")
    # P-1: la búsqueda por documento va en el cuerpo de un POST, no en la URL. Las referencias son
    # las de CAPTACION: el cliente que se acaba de habilitar.
    estado, respuesta, _ = pedir_navegador("POST", "clients/search", {"search": dni}, cookie=sesion)
    exigir(estado == 200 and [c["id_cliente"] for c in respuesta] == [cod_cliente],
           f"Búsqueda de clientes de SOL en CAPTACION por documento: {estado} {respuesta}")
    borrador = {"id_cliente": cod_cliente, "monto_solicitado": politica["monto_minimo"], "moneda": "PEN",
                "plazo_meses": politica["plazo_minimo_meses"], "destino_credito": "Capital de trabajo del flujo",
                "fecha_base": time.strftime("%Y-%m-%d", time.gmtime(time.time() + 86400)), "pago_doble": False,
                "garantias": [{"tipo_garantia": "PRENDARIA", "descripcion": "Prenda del flujo",
                               "valor_tasacion": "1500.00"}], "fiadores": []}
    estado, solicitud_sol, _ = pedir_navegador("POST", "applications", borrador, cookie=sesion)
    exigir(estado == 201 and solicitud_sol["estado"] == "REGISTRADA" and solicitud_sol["revision"] == 1,
           f"Borrador de SOL en COREDB: {estado} {solicitud_sol}")
    id_sol = solicitud_sol["id"]
    en_coredb = coredb("GET", f"/coredb/creditos/solicitudes/{id_sol}", 200, token=token)
    exigir(en_coredb["estado"] == "REGISTRADA" and en_coredb["expediente"]["creadoPor"] == asesora
           and [g["tipo"] for g in en_coredb["garantias"]] == ["PRENDARIA"],
           f"El borrador debía estar en COREDB a nombre de la asesora: {en_coredb}")
    borrador["monto_solicitado"] = str(float(politica["monto_minimo"]) + 500)
    estado, editada, _ = pedir_navegador("PUT", f"applications/{id_sol}", {**borrador, "revision": 1}, cookie=sesion)
    exigir(estado == 200 and editada["revision"] == 2, f"Edición del borrador con su revisión: {estado} {editada}")
    # Repetir la misma edición es un reintento (200, la misma revisión); otra edición con la revisión
    # vieja es de otra sesión: 409.
    estado, repetida, _ = pedir_navegador("PUT", f"applications/{id_sol}", {**borrador, "revision": 1}, cookie=sesion)
    exigir(estado == 200 and repetida["revision"] == 2, f"Repetir la edición debía reconocerse: {estado} {repetida}")
    otra_sesion = {**borrador, "monto_solicitado": str(float(politica["monto_minimo"]) + 900), "revision": 1}
    estado, vieja, _ = pedir_navegador("PUT", f"applications/{id_sol}", otra_sesion, cookie=sesion)
    exigir(estado == 409, f"Editar con una revisión vieja debía dar 409: {estado} {vieja}")
    estado, enviada, _ = pedir_navegador("POST", f"applications/{id_sol}/send", {"revision": 2}, cookie=sesion,
                                         llave=str(uuid.uuid4()))
    exigir(estado == 200 and enviada["estado"] == "EN_EVALUACION" and enviada["envios"][0]["ronda"] == 1,
           f"Envío del expediente a EVALUACION por el Bus: {estado} {enviada}")
    estado, otra, _ = pedir_navegador("POST", f"applications/{id_sol}/send", {"revision": 2}, cookie=sesion,
                                      llave=str(uuid.uuid4()))
    exigir(estado == 200 and otra.get("reintento_reconocido") is True, f"Reenviar debía reconocerse: {estado} {otra}")
    situacion = {"versionSolicitud": 1, "ingresoMensual": "20000.00", "deudaMensual": "0.00", "riesgo": "BUENO",
                 "verificada": True}
    estado, evaluada = pedir("POST", f"{EVALUACION}/eva/v1/solicitudes/{id_sol}/evaluaciones", situacion, token)
    exigir(estado == 200 and evaluada["resultado"] == "APROBADO", f"Evaluación del expediente de SOL: {estado} {evaluada}")
    # CR-INT-03: EVALUACION entrega el resultado a SOL por el Bus en su próximo ciclo.
    limite_espera, recibido = time.monotonic() + 45, []
    while not recibido and time.monotonic() < limite_espera:
        recibido = coredb("GET", f"/coredb/auditoria?id_entidad={id_sol}&accion=RECIBIR_CR_INT_03", 200, token=token)
        if not recibido:
            time.sleep(2)
    exigir(len(recibido) == 1 and recibido[0]["modulo"] == "SOLICITUD DE CREDITO"
           and recibido[0]["detalle"]["decision"] == "APROBADO",
           f"El resultado (CR-INT-03) debía llegar a SOL y quedar en la bitácora: {recibido}")
    enviado = coredb("GET", f"/coredb/auditoria?id_entidad={id_sol}&accion=ENVIAR_CR_INT_02", 200, token=token)
    exigir(len(enviado) == 1 and enviado[0]["actor"] == asesora,
           f"El envío debía quedar en la bitácora a nombre de la asesora: {enviado}")
    estado, final, _ = pedir_navegador("GET", f"applications/{id_sol}", cookie=sesion)
    exigir(estado == 200 and final["estado"] == "APROBADA" and final["resultados"][0]["decision"] == "APROBADO",
           f"SOL debía mostrar la solicitud APROBADA desde COREDB: {estado} {final}")
    estado, respuesta, galleta = pedir_navegador("POST", "auth/logout", {}, cookie=sesion)
    exigir(estado == 200 and "bna_sol_session=;" in galleta.replace(" ", ""),
           f"Cierre de sesión de SOL por el proxy (borra la cookie): {estado} {respuesta}")
    paso(f"SOL: la asesora {asesora} (usuario de COREDB) entra por el proxy del frontend (otro origen, 403; cookie "
         "HttpOnly), busca en CAPTACION por el cuerpo, guarda y edita el borrador en COREDB (repetir la edición, 200; revisión vieja, 409), "
         "lo envía a EVALUACION por el Bus (reenvío reconocido); evaluado APROBADO, el resultado vuelve a SOL "
         "(CR-INT-03) y queda en la bitácora con el envío de la asesora")

    # ── Retención vencida: la del cajero que cayó se libera y ya no se confirma ──
    # El plazo de la base es de 15 minutos; el operador libera con 1 para no esperarlo.
    time.sleep(max(0.0, 61 - (time.monotonic() - retenida_desde)))
    liberacion = coredb("POST", "/coredb/autorizaciones/liberaciones", 200, {"minutos": 1}, token)
    exigir(liberacion["liberadas"] >= 1, f"La liberación debía extornar la retención vencida: {liberacion}")
    huerfana = coredb("GET", f"/coredb/autorizaciones/{retencion_huerfana}", 200, token=token)
    exigir(huerfana["estado_autorizacion"] == "EXTORNADA" and huerfana["codigo_respuesta"] == "EXT",
           f"La retención vencida debía quedar EXTORNADA: {huerfana}")
    disponible = coredb("GET", f"/coredb/cuentas/{cuenta_tarjeta}", 200, token=token)["saldo_disponible"]
    exigir(float(disponible) == 30.0, f"La liberación debía devolver los 10.00 retenidos: disponible {disponible}")
    coredb("POST", "/coredb/autorizaciones/liberaciones", 200, {"minutos": 1}, token)
    estado, respuesta = pedir("POST", f"{COREDB}/coredb/autorizaciones/{retencion_huerfana}/confirmacion",
                              {"id_terminal": "DEV-ATM-01"}, token, cabeceras={"X-Idempotency-Key": str(uuid.uuid4())})
    exigir(estado == 422 and respuesta["error"]["code"] == "BNA-CONFIRMACION",
           f"Confirmar una retención liberada debía fallar: {estado} {respuesta}")
    disponible = coredb("GET", f"/coredb/cuentas/{cuenta_tarjeta}", 200, token=token)["saldo_disponible"]
    exigir(float(disponible) == 30.0, f"Liberar dos veces o confirmar tarde no debía mover el saldo: {disponible}")
    paso("COREDB: la retención de 10.00 que el cajero no confirmó se liberó (EXTORNADA) y devolvió el saldo una "
         "vez; liberar de nuevo no cambia nada y confirmarla tarde da 422 BNA-CONFIRMACION")

    # ── SEGURIDAD: sin base propia; guarda en la base integrada por COREDB, a través del Bus ──
    seg = f"{SEGURIDAD}/seguridad"

    def seguridad(metodo, ruta, esperado, cuerpo=None, token_persona=None):
        estado, respuesta = pedir(metodo, seg + ruta, cuerpo, token_persona,
                                  cabeceras={"X-Correlation-ID": str(uuid.uuid4())})
        exigir(estado == esperado, f"Seguridad {metodo} {ruta}: esperaba {esperado}, recibió {estado} {respuesta}")
        return respuesta

    estado_seg = seguridad("GET", "/estado", 200)
    exigir(estado_seg["base_propia"] is False and estado_seg["coredb_disponible"] is True,
           f"Seguridad debía operar sin base propia y alcanzar COREDB: {estado_seg}")
    exigir(seguridad("POST", "/operaciones/evaluar", 401, {"uuid_operacion": str(uuid.uuid4()), "num_cuenta": origen,
                                                          "canal": "ATM", "monto": "1.00"}) ["error"]["code"]
           == "TOKEN_REQUERIDO", "Seguridad debía exigir el token de la persona")
    # El tope y el consumo reales del canal ATM para la cuenta: una evaluación de 1.00 los devuelve.
    base_eval = {"num_cuenta": origen, "canal": "ATM"}
    sonda = seguridad("POST", "/operaciones/evaluar", 200, {**base_eval, "uuid_operacion": str(uuid.uuid4()),
                                                            "monto": "1.00"}, token_op)
    exigir(sonda["decision"] == "AUTORIZADA" and sonda["efecto_financiero"] is False,
           f"Evaluación de 1.00 por ATM: {sonda}")
    tope, consumido = float(sonda["tope"]), float(sonda["consumido"])
    operacion = {**base_eval, "uuid_operacion": str(uuid.uuid4()), "monto": f"{tope * 0.9 - consumido:.2f}"}
    pedido = seguridad("POST", "/operaciones/evaluar", 200, operacion, token_op)
    exigir(pedido["decision"] == "DESAFIO_REQUERIDO" and len(pedido["codigo_demo"]) == 6,
           f"Sobre el 80 % del tope debía pedir un desafío: {pedido}")
    con_codigo = {**operacion, "id_desafio": pedido["id_desafio"], "codigo": pedido["codigo_demo"]}
    otro = "000000" if pedido["codigo_demo"] != "000000" else "111111"
    exigir(seguridad("POST", "/operaciones/evaluar", 200, {**con_codigo, "codigo": otro}, token_op)["decision"]
           == "DESAFIO_RECHAZADO", "Un código equivocado debía dar DESAFIO_RECHAZADO")
    autorizada = seguridad("POST", "/operaciones/evaluar", 200, con_codigo, token_op)
    exigir(autorizada["decision"] == "AUTORIZADA" and autorizada["repetida"] is False,
           f"El código correcto debía autorizar: {autorizada}")
    repetida = seguridad("POST", "/operaciones/evaluar", 200, operacion, token_op)
    exigir(repetida["decision"] == "AUTORIZADA" and repetida["repetida"] is True,
           f"Repetir la operación debía devolver la misma decisión: {repetida}")
    sobre_tope = seguridad("POST", "/operaciones/evaluar", 200,
                           {**base_eval, "uuid_operacion": str(uuid.uuid4()), "monto": f"{tope - consumido + 1:.2f}"},
                           token_op)
    exigir((sobre_tope["decision"], sobre_tope["motivo"]) == ("RECHAZADA", "TOPE"),
           f"Sobre el tope debía rechazar: {sobre_tope}")
    disponible = coredb("GET", f"/coredb/cuentas/{origen}", 200, token=token)["saldo_disponible"]
    exigir(disponible == "350.00", f"Evaluar no debía mover el saldo: {disponible}")
    eventos = coredb("GET", f"/coredb/auditoria?modulo=SEGURIDAD&id_entidad={operacion['uuid_operacion']}", 200,
                     token=token)
    exigir({(e["accion"], e["actor"]) for e in eventos} >= {("CREAR_DESAFIO", operador),
                                                           ("RECHAZAR_DESAFIO", operador),
                                                           ("EVALUAR_OPERACION", operador)},
           f"La bitácora debía tener el desafío y la decisión a nombre de {operador}: {eventos}")
    paso(f"SEGURIDAD: {operador} evalúa contra el tope real de ATM ({tope:.2f}, consumido {consumido:.2f}): sobre el "
         "80 % pide un desafío, el código equivocado se rechaza, el correcto autoriza, repetir devuelve lo mismo, sobre "
         "el tope se rechaza; sin mover dinero y con todo en la bitácora de COREDB")

    incidente = seguridad("POST", "/incidentes", 201, {"prioridad": "P2", "titulo": "Intentos de acceso repetidos"},
                          token_op)
    exigir(incidente["estado"] == "ABIERTO" and incidente["abierto_por"] == operador
           and incidente["sla_atencion_min"] == 30, f"Incidente abierto: {incidente}")
    salto = seguridad("PATCH", f"/incidentes/{incidente['id_incidente']}", 409,
                      {"estado": "RESUELTO", "resolucion": "Sin pasar por EN_PROGRESO"}, token_op)
    exigir(salto["error"]["code"] == "BNA-INCIDENTE-TRANSICION", f"Saltar un estado debía dar 409: {salto}")
    for estado_inc, extra in (("EN_PROGRESO", {}), ("RESUELTO", {"resolucion": "Se bloqueó el origen"}),
                              ("CERRADO", {})):
        incidente = seguridad("PATCH", f"/incidentes/{incidente['id_incidente']}", 200,
                              {"estado": estado_inc, **extra}, token_op)
    exigir(incidente["estado"] == "CERRADO" and incidente["resolucion"] == "Se bloqueó el origen",
           f"El incidente debía quedar CERRADO con su resolución: {incidente}")
    paso(f"SEGURIDAD: {operador} abre un incidente P2 (SLA 30/240 min), no puede saltar de ABIERTO a RESUELTO, y lo "
         "lleva a EN_PROGRESO, RESUELTO con resolución y CERRADO")

    desbloqueo = seguridad("POST", f"/tarjetas/{tarjeta}/desbloqueo", 200,
                           {"motivo": "El cliente confirmó su identidad"}, token_op)
    exigir(desbloqueo["estado_tarjeta"] == "ACTIVA", f"Desbloqueo por Seguridad: {desbloqueo}")
    seguridad("POST", f"/tarjetas/{tarjeta}/desbloqueo", 409, {"motivo": "Otra vez"}, token_op)
    eventos = coredb("GET", f"/coredb/auditoria?accion=DESBLOQUEAR_TARJETA&id_entidad={tarjeta}", 200, token=token)
    exigir([e["actor"] for e in eventos] == [operador],
           f"El desbloqueo debía quedar en la bitácora a nombre de {operador}: {eventos}")
    paso(f"SEGURIDAD: {operador} desbloquea la tarjeta que TARJETAS no puede desbloquear (ACTIVA, origen SEGURIDAD, "
         "actor en la bitácora); desbloquearla otra vez da 409")

    seguridad("POST", "/auditoria/sellos", 200, token_persona=token)
    verificacion = seguridad("GET", "/auditoria/verificar", 200, token_persona=token)
    exigir(verificacion["valida"] is True and verificacion["sellos_verificados"] >= 1,
           f"La bitácora sellada debía verificarse: {verificacion}")
    exigir(seguridad("GET", "/auditoria/verificar", 403, token_persona=token_op)["error"]["code"] == "PERMISO_DENEGADO",
           "Verificar la bitácora exige VER_AUDITORIA")
    paso(f"SEGURIDAD: la bitácora de COREDB queda sellada con HMAC encadenado y se verifica "
         f"({verificacion['sellos_verificados']} sellos, hasta el evento {verificacion['ultimo_evento_sellado']}); "
         "un operador no la verifica")

    # ── Todo pasó por el Bus: el flujo y cada puente del frontend ────────────
    despues = metricas_bus()

    def crecio(consumidor, modulo):
        return despues.get(consumidor, {}).get(modulo, 0) > inicio_bus.get(consumidor, {}).get(modulo, 0)

    # El cajero sirve sus propias pantallas: el frontend no tiene puente al ATM.
    faltan = [m for m in ("COREDB", "CUENTAS", "TARJETAS", "SOL", "EVALUACION", "DESEMBOLSO", "CAPTACION", "COBRANZA")
              if not crecio("FRONTEND", m)]
    exigir(not faltan, f"Estos puentes del frontend no pasaron por el Bus: {faltan}")
    faltan = [m for m in ("COREDB", "CUENTAS", "TARJETAS", "ATM", "SOL", "EVALUACION", "DESEMBOLSO", "CAPTACION",
                          "SEGURIDAD", "BILLETERA") if not crecio("PRUEBAS", m)]
    exigir(not faltan, f"El flujo no llegó por el Bus a: {faltan}")
    # Fase 2: cada módulo llegó a COREDB a través del Bus, con su propia credencial.
    # ATM no llama a COREDB directo; llama a TARJETAS por el Bus con su propia credencial.
    exigir(crecio("ATM", "TARJETAS"), "El ATM no llegó a TARJETAS por el Bus con su credencial")
    faltan = [m for m in ("CUENTAS", "TARJETAS", "CAPTACION", "EVALUACION", "DESEMBOLSO", "COBRANZA", "BILLETERA",
                          "SEGURIDAD") if not crecio(m, "COREDB")]
    exigir(not faltan, f"Estos módulos no llegaron a COREDB por el Bus: {faltan}")
    paso("Bus de Servicios: el flujo y los ocho puentes del frontend llegaron a los módulos por el Bus, "
         "CUENTAS, TARJETAS, CAPTACION, EVALUACION, DESEMBOLSO, COBRANZA, BILLETERA y SEGURIDAD llegaron a COREDB "
         "por él "
         "y el ATM llegó a TARJETAS por él")


if __name__ == "__main__":
    print("Flujo de extremo a extremo:")
    try:
        flujo()
    except Fallo as fallo:
        print(f"  FALLA  {fallo}", file=sys.stderr)
        sys.exit(1)
    print("Flujo completo.")
    destino = os.environ.get("E2E_SENSIBLES")
    if destino:
        SENSIBLES.update(v for v in (TOKEN_BUS, TOKEN_SOL, PASSWORD, TOKEN_SOL_EVALUACION) if v)
        with open(destino, "w", encoding="utf-8") as archivo:
            archivo.write("\n".join(sorted(SENSIBLES)) + "\n")
