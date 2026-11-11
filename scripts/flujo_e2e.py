"""Flujo de extremo a extremo del producto integrado.

Corre dentro del contenedor de COREDB (`./bna smoke`), así que llega a los demás
servicios por su nombre en la red interna y solo usa la biblioteca estándar.

Pasos: salud de cada servicio, login del administrador, registro de un cliente,
apertura de dos cuentas para él, depósito, transferencia, repetición idempotente y
saldos finales.
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
SERVICIOS = {
    "COREDB": (COREDB + "/coredb/salud", {}),
    "CUENTAS": (os.environ.get("E2E_CUENTAS", "http://cuentas:8001") + "/health", {}),
    "SOL": (os.environ.get("E2E_SOL", "http://sol:8011") + "/ready", {}),
    "Seguridad": (os.environ.get("E2E_SEGURIDAD", "http://seguridad:8013") + "/seguridad/estado",
                  {"X-Correlation-ID": "flujo-e2e"}),
    "frontend": (os.environ.get("E2E_FRONTEND", "http://frontend:3000") + "/", {}),
    "CORE legado": (os.environ.get("E2E_CORE_LEGADO", "http://core-legado:8000") + "/health", {}),
}
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


if __name__ == "__main__":
    print("Flujo de extremo a extremo:")
    try:
        flujo()
    except Fallo as fallo:
        print(f"  FALLA  {fallo}", file=sys.stderr)
        sys.exit(1)
    print("Flujo completo.")
