"""Prueba de integración de Cobranza con el producto levantado: cobra cuotas por CUENTAS real.

Se ejecuta dentro del contenedor de Cobranza, con el producto arriba (./bna up):

    docker compose exec -T -e BNA_ADMIN_PASSWORD="$(grep '^BNA_ADMIN_PASSWORD=' .env | cut -d= -f2-)" \\
        cobranza python -m COBRANZA.scripts.prueba_integracion

Pasos (datos nuevos en cada corrida):
  1. Como administrador de COREDB: registra un cliente, le abre dos cuentas y deposita 500.00 en una.
  2. Desembolso (CR-INT-06): activa en Cobranza un crédito de 3 cuotas de 150.00.
  3. Home Banking (CR-INT-08): paga la cuota 1 desde la cuenta con saldo. Cobranza la debita por
     CUENTAS (CR-INT-07) y el saldo baja a 350.00.
  4. Repite el mismo pago: no se cobra dos veces (idempotencia, RN-INT-CR-006).
  5. Paga la cuota 2 desde la cuenta vacía: CUENTAS rechaza y la cuota no cambia (RN-COB-009).
  6. Lee la cuota y la conciliación del día en Cobranza.
"""

import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import date, datetime, timedelta

COREDB = os.environ.get("COREDB_URL", "http://coredb:8012").rstrip("/")
COBRANZA = os.environ.get("COBRANZA_URL", "http://127.0.0.1:8014").rstrip("/")
ADMIN = os.environ.get("BNA_ADMIN_USUARIO", "admin")
ADMIN_PASSWORD = os.environ.get("BNA_ADMIN_PASSWORD", "")
CLAVE_BUS = os.environ.get("API_KEY_INTEGRACION_BUS", "")
CLAVE_LEER = os.environ.get("API_KEY_COBRANZA_LEER", "")


class Fallo(Exception):
    pass


def pedir(metodo, url, cuerpo=None, cabeceras=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    peticion = urllib.request.Request(url, data=datos, method=metodo)
    if datos is not None:
        peticion.add_header("Content-Type", "application/json")
    for nombre, valor in (cabeceras or {}).items():
        peticion.add_header(nombre, valor)
    try:
        with urllib.request.urlopen(peticion, timeout=20) as respuesta:
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
    cabeceras = {"Authorization": f"Bearer {token}"} if token else {}
    estado, respuesta = pedir(metodo, COREDB + ruta, cuerpo, cabeceras)
    exigir(estado == esperado, f"COREDB {metodo} {ruta}: se esperaba {esperado} y respondió {estado}: {respuesta}")
    return respuesta


def saldo(token, cuenta):
    return coredb("GET", f"/coredb/cuentas/{cuenta}", 200, token=token)["saldo_disponible"]


def pagar(credito, cliente, cuenta, referencia):
    return pedir("POST", COBRANZA + "/cr-int-08/pagos", {
        "codCliente": cliente, "codCredito": credito, "montoPago": "150.00",
        "cuentaOrigen": cuenta, "referenciaTransaccion": referencia, "idCanal": "HB",
    }, {"X-API-Key": CLAVE_BUS, "X-Token-Seguridad": "TOKEN-PRUEBA-INTEGRACION"})


def flujo():
    exigir(ADMIN_PASSWORD, "Falta BNA_ADMIN_PASSWORD")
    exigir(CLAVE_BUS and CLAVE_LEER, "Faltan las claves X-API-Key de Cobranza (¿se ejecuta dentro del contenedor?)")
    estado, _ = pedir("GET", COBRANZA + "/salud")
    exigir(estado == 200, f"Cobranza no responde ({estado})")
    paso("Cobranza responde")

    token = coredb("POST", "/coredb/auth/login", 200, {"username": ADMIN, "password": ADMIN_PASSWORD})["access_token"]
    base = int(time.time() * 1000) % 10**15 * 10
    sufijo = f"{random.randrange(10**8):08d}"
    cliente = coredb("POST", "/coredb/clientes", 201, {
        "tipo_documento": "DNI", "numero_documento": sufijo,
        "nombres": "Cliente", "apellido_paterno": "De Cobranza", "apellido_materno": None,
        "correo": f"cobranza-{base}@example.com", "celular": "9" + sufijo,
        "version_contrato": "v1", "estado_habilitante": "OBSERVADO",
    }, token)["cod_cliente"]
    cuentas = []
    for indice in (1, 2):
        numero = base + indice
        cuentas.append(coredb("POST", "/coredb/cuentas", 201, {
            "num_cuenta": f"CTA-{numero:016d}", "cci": f"{numero:020d}", "moneda": "PEN",
            "regimen": "INDIVIDUAL", "id_agencia": "AQP01", "titulares": [cliente],
        }, token)["num_cuenta"])
    con_saldo, sin_saldo = cuentas
    coredb("POST", "/coredb/movimientos", 201, {
        "num_cuenta": con_saldo, "tipo": "DEPOSITO", "monto": "500.00",
        "glosa": "Depósito para la prueba de Cobranza", "id_canal": "HB",
        "idempotency_key": str(uuid.uuid4()),
    }, token)
    paso(f"cliente {cliente} con {con_saldo} (500.00) y {sin_saldo} (0.00)")

    credito = f"CR-{base % 10**12:012d}"
    hoy = date.today()
    estado, obligacion = pedir("POST", COBRANZA + "/cr-int-06/obligaciones", {
        "codCredito": credito, "idCliente": cliente, "idSolicitud": f"SOL-{base % 10**12:012d}",
        "montoAprobado": "450.00", "moneda": "PEN", "fechaDesembolso": datetime.now().isoformat(timespec="seconds"),
        "calendarioPagos": [
            {"numeroCuota": n, "fechaVencimiento": (hoy + timedelta(days=30 * n)).isoformat(), "montoCuota": "150.00"}
            for n in (1, 2, 3)],
    }, {"X-API-Key": CLAVE_BUS})
    exigir(estado == 201, f"CR-INT-06 debía responder 201 y respondió {estado}: {obligacion}")
    paso(f"Desembolso activa el crédito {credito} (3 cuotas de 150.00)")

    referencia = f"OP-{base % 10**12:012d}"
    estado, pago = pagar(credito, cliente, con_saldo, referencia)
    exigir(estado == 200 and pago.get("estado") == "CONFIRMADO", f"El pago debía quedar CONFIRMADO: {estado} {pago}")
    exigir(float(saldo(token, con_saldo)) == 350.0, "El saldo debía bajar a 350.00")
    paso(f"Home Banking paga la cuota 1: CUENTAS debita {con_saldo} y queda en 350.00")

    estado, repetido = pagar(credito, cliente, con_saldo, referencia)
    exigir(estado == 200 and repetido.get("idempotente") is True, f"El pago repetido debía ser idempotente: {repetido}")
    exigir(float(saldo(token, con_saldo)) == 350.0, "Repetir el pago no debía cobrar otra vez")
    paso("repetir el pago no cobra dos veces")

    estado, rechazado = pagar(credito, cliente, sin_saldo, referencia + "-B")
    exigir(estado == 200 and rechazado.get("estado") == "RECHAZADO", f"El pago sin fondos debía quedar RECHAZADO: {rechazado}")
    paso(f"pago desde la cuenta sin saldo: RECHAZADO ({rechazado.get('motivo')})")

    estado, cuotas = pedir("GET", COBRANZA + f"/creditos/{credito}/cuotas", cabeceras={"X-API-Key": CLAVE_LEER})
    exigir(estado == 200, f"No se pudieron leer las cuotas: {estado} {cuotas}")
    resumen = [(c["numeroCuota"], c["estadoCuota"]) for c in cuotas]
    exigir(resumen[:2] == [(1, "PAGADA"), (2, "PENDIENTE")], f"Estados de cuota inesperados: {resumen}")
    paso(f"cuotas en Cobranza: {resumen}")

    estado, conciliacion = pedir("GET", COBRANZA + "/conciliacion", cabeceras={"X-API-Key": CLAVE_LEER})
    exigir(estado == 200, f"No se pudo leer la conciliación: {estado} {conciliacion}")
    paso("conciliación del día disponible")


def main():
    print("Cobranza: integración con CUENTAS y COREDB")
    try:
        flujo()
    except Fallo as error:
        print(f"  FALLA  {error}", file=sys.stderr)
        return 1
    print("Integración de Cobranza correcta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
