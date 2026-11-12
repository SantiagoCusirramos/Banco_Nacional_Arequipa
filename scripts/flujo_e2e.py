"""Flujo de extremo a extremo del producto integrado.

Corre dentro del contenedor de COREDB (`./bna smoke`), así que llega a los demás
servicios por su nombre en la red interna y solo usa la biblioteca estándar.

Pasos: salud de cada servicio, login del administrador, registro de un cliente,
apertura de dos cuentas para él, depósito, transferencia, repetición idempotente,
saldos finales, movimientos de la cuenta, cuentas del cliente y bitácora por
COREDB; después, las mismas cuentas por el módulo CUENTAS, una tarjeta por el
módulo TARJETAS y todo por los puentes del frontend, que es el camino que sigue el
navegador.
"""

import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
import uuid

COREDB = os.environ.get("E2E_COREDB", "http://127.0.0.1:8012")
CUENTAS = os.environ.get("E2E_CUENTAS", "http://cuentas:8001")
TARJETAS = os.environ.get("E2E_TARJETAS", "http://tarjetas:8002")
FRONTEND = os.environ.get("E2E_FRONTEND", "http://frontend:3000")
SERVICIOS = {
    "COREDB": (COREDB + "/coredb/salud", {}),
    "CUENTAS": (CUENTAS + "/health", {}),
    "TARJETAS": (TARJETAS + "/health", {}),
    "SOL": (os.environ.get("E2E_SOL", "http://sol:8011") + "/ready", {}),
    "Seguridad": (os.environ.get("E2E_SEGURIDAD", "http://seguridad:8013") + "/seguridad/estado",
                  {"X-Correlation-ID": "flujo-e2e"}),
    "frontend": (FRONTEND + "/login", {}),
}
# Solo si se levantó con el perfil `legado`.
if os.environ.get("E2E_CORE_LEGADO"):
    SERVICIOS["CORE legado"] = (os.environ["E2E_CORE_LEGADO"] + "/health", {})
USUARIO = os.environ.get("BNA_ADMIN_USUARIO", "admin")
PASSWORD = os.environ.get("BNA_ADMIN_PASSWORD", "")
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


def exigir(condicion, mensaje):
    if not condicion:
        raise Fallo(mensaje)


def paso(texto):
    print(f"  ok  {texto}", flush=True)


def coredb(metodo, ruta, esperado, cuerpo=None, token=None):
    estado, respuesta = pedir(metodo, COREDB + ruta, cuerpo, token)
    exigir(estado == esperado, f"{metodo} {ruta}: se esperaba {esperado} y respondió {estado}: {respuesta}")
    return respuesta


def flujo():
    exigir(PASSWORD, "Falta BNA_ADMIN_PASSWORD")

    for nombre, (url, cabeceras) in SERVICIOS.items():
        estado, _ = pedir("GET", url, cabeceras=cabeceras)
        exigir(estado == 200, f"{nombre} no está sano: {url} respondió {estado}")
        paso(f"{nombre} responde")

    estado, _ = pedir("GET", COREDB + "/coredb/auth/me")
    exigir(estado == 401, f"COREDB sin token debía responder 401 y respondió {estado}")
    paso("COREDB rechaza una petición sin token")

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
    cuenta_tarjeta = coredb("POST", "/coredb/cuentas", 201, {
        "num_cuenta": f"CTA-{numero:016d}", "cci": f"{numero:020d}", "moneda": "PEN",
        "regimen": "INDIVIDUAL", "id_agencia": AGENCIA, "titulares": [titular],
    }, token)["num_cuenta"]
    base = TARJETAS + "/api/v1/tarjetas"
    estado, _ = pedir("GET", f"{base}/cliente/{titular}")
    exigir(estado == 401, f"TARJETAS sin token debía responder 401 y respondió {estado}")
    estado, respuesta = pedir("POST", f"{base}/emision", {"cod_cliente": cliente, "num_cuenta": origen}, token)
    exigir(estado == 400 and respuesta["error_code"] == "ERR-TAR-001",
           f"TARJETAS debía rechazar la emisión a un cliente OBSERVADO: {estado} {respuesta}")
    estado, respuesta = pedir("POST", f"{base}/emision", {"cod_cliente": titular, "num_cuenta": cuenta_tarjeta}, token)
    exigir(estado == 201 and respuesta["data"]["estado_tarjeta"] == "PENDIENTE_ACTIVACION",
           f"Emisión por TARJETAS: {estado} {respuesta}")
    tarjeta = respuesta["data"]["id_tarjeta"]
    estado, respuesta = pedir("POST", f"{base}/{tarjeta}/estado", {"estado": "ACTIVA"}, token)
    exigir(estado == 200 and respuesta["data"]["estado_tarjeta"] == "ACTIVA",
           f"Activación por TARJETAS: {estado} {respuesta}")
    estado, respuesta = pedir("POST", f"{base}/{tarjeta}/bloqueo", {"motivo": "Prueba del flujo"}, token)
    exigir(estado == 200 and respuesta["data"]["estado_tarjeta"] == "BLOQUEADA",
           f"Bloqueo por TARJETAS: {estado} {respuesta}")
    estado, respuesta = pedir("POST", f"{base}/{tarjeta}/estado", {"estado": "ACTIVA"}, token)
    exigir(estado == 403 and respuesta["error_code"] == "ERR-TAR-DESBLOQUEO-NO-PERMITIDO",
           f"El desbloqueo por TARJETAS debía responder 403: {estado} {respuesta}")
    estado, respuesta = pedir("GET", f"{base}/cliente/{titular}", token=token)
    exigir(estado == 200 and tarjeta in [t["id_tarjeta"] for t in respuesta["data"]],
           f"Tarjetas del cliente por TARJETAS: {estado} {respuesta}")
    paso(f"TARJETAS: emisión a {titular} (no a un cliente OBSERVADO), activación, bloqueo, "
         "desbloqueo rechazado y tarjetas del cliente")

    # ── Por los puentes del frontend, como lo hace el navegador ─────────────
    estado, respuesta = pedir("GET", f"{FRONTEND}/api/core/coredb/auth/me", token=token)
    exigir(estado == 200 and respuesta["username"] == USUARIO, f"Puente a COREDB: {estado} {respuesta}")
    estado, respuesta = pedir("GET", f"{FRONTEND}/api/cuenta/{origen}", token=token)
    exigir(estado == 200 and respuesta["data"]["saldo_disponible"] == "350.00",
           f"Puente a CUENTAS: {estado} {respuesta}")
    estado, respuesta = pedir("GET", f"{FRONTEND}/api/tarjeta/{tarjeta}", token=token)
    exigir(estado == 200 and respuesta["data"]["estado_tarjeta"] == "BLOQUEADA",
           f"Puente a TARJETAS: {estado} {respuesta}")
    estado, _ = pedir("GET", f"{FRONTEND}/api/core/otra/ruta", token=token)
    exigir(estado == 404, f"El puente a COREDB solo debe reenviar /coredb: respondió {estado}")
    paso("frontend: sus puentes llegan a COREDB, a CUENTAS y a TARJETAS con el token del usuario")


if __name__ == "__main__":
    print("Flujo de extremo a extremo:")
    try:
        flujo()
    except Fallo as fallo:
        print(f"  FALLA  {fallo}", file=sys.stderr)
        sys.exit(1)
    print("Flujo completo.")
