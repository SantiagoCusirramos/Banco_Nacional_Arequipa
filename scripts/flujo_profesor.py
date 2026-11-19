"""Flujo de la demo pedido por el profesor, de punta a punta, contra el producto levantado.

1. Captación registra a un cliente nuevo y lo deja HABILITADO.
2. CUENTAS le abre una cuenta de ahorros y por ventanilla (canal VEN) se le depositan S/ 500.
3. TARJETAS le emite una tarjeta de débito sobre esa cuenta, la activa y registra su PIN de cajero.
4. En el ATM: el operador abre el cajero, el cliente valida su PIN, consulta el saldo y retira S/ 100.
5. Por ventanilla se le depositan S/ 1000 más.
6. Se le afilia a Chaski y desde la billetera hace un pago: un envío por celular y un pago con QR.
7. TARJETAS bloquea la tarjeta y el ATM ya no la acepta.

Deja los datos en la base compartida e imprime con qué se entra a cada pantalla, para repetir la
demo a mano. Se corre con `./bna demo` (dentro del contenedor del Bus, como `./bna smoke`).
"""

import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
import uuid

BUS = os.environ.get("E2E_BUS", "http://127.0.0.1:8018").rstrip("/")
TOKEN_BUS = os.environ["BUS_TOKEN"]
USUARIO = os.environ.get("BNA_ADMIN_USUARIO", "admin")
PASSWORD = os.environ["BNA_ADMIN_PASSWORD"]
COREDB = f"{BUS}/bus/coredb/coredb"
CAP = f"{BUS}/bus/captacion/api/v1/captacion"
CTA = f"{BUS}/bus/cuentas/api/v1/cuentas"
TARJ = f"{BUS}/bus/tarjetas/api/v1/tarjetas"
ATM = f"{BUS}/bus/atm/api"
CHASKI = f"{BUS}/bus/billetera/api"
TERMINAL = "DEV-ATM-01"
PIN_ATM = "1234"
PIN_CHASKI = "246810"


class Fallo(Exception):
    pass


def pedir(metodo, url, cuerpo=None, token=None, cab=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    r = urllib.request.Request(url, data=datos, method=metodo)
    r.add_header("X-Bus-Token", TOKEN_BUS)
    if datos is not None:
        r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    for k, v in (cab or {}).items():
        r.add_header(k, v)
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            estado, texto = resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        estado, texto = e.code, e.read().decode()
    except (urllib.error.URLError, OSError) as e:
        raise Fallo(f"{metodo} {url}: sin respuesta ({e})") from e
    try:
        return estado, json.loads(texto) if texto else None
    except ValueError:
        return estado, texto


def exigir(estado, respuesta, esperado, que):
    if estado not in esperado:
        raise Fallo(f"{que}: respondió {estado}: {respuesta}")
    return respuesta


def paso(n, texto):
    print(f"  OK  {n}. {texto}", flush=True)


def ventanilla(token, operacion, cuerpo):
    """Depósito o retiro por CUENTAS con el canal de ventanilla, como la pantalla /cuenta."""
    estado, r = pedir("POST", f"{CTA}/{operacion}", cuerpo, token, {
        "X-Idempotency-Key": str(uuid.uuid4()), "X-Channel-ID": "VEN",
        "X-Request-Timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    return exigir(estado, r, (201,), f"{operacion} por ventanilla")["data"]


def saldo(token, cuenta):
    estado, r = pedir("GET", f"{CTA}/{cuenta}", token=token)
    return exigir(estado, r, (200,), "consulta de la cuenta")["data"]["saldo_disponible"]


def captar(token, nombres, paterno, materno):
    dni = "4" + "".join(random.choices("0123456789", k=6)) + "1"  # termina en 1: central NORMAL
    cel = "9" + "".join(random.choices("0123456789", k=8))

    def cap(metodo, ruta, cuerpo=None):
        estado, r = pedir(metodo, CAP + ruta, cuerpo, token)
        return exigir(estado, r, (200, 201), f"Captación {ruta}")["data"]

    sol = cap("POST", "/solicitantes", {"tipo_documento": "DNI", "numero_documento": dni, "nombres": nombres,
              "apellido_paterno": paterno, "apellido_materno": materno, "celular": cel,
              "correo": f"{nombres.lower()}.{dni}@example.com"})["solicitante"]
    caso = cap("POST", "/casos", {"id_solicitante": sol["id_solicitante"], "canal": "AGENCIA",
               "id_agencia": "AQP01"})["id_caso"]
    cap("POST", f"/casos/{caso}/consentimientos", {"consentimientos": [
        {"tipo": t, "aceptado": True} for t in ("TRATAMIENTO_DATOS", "CONSULTA_BUROS", "TERMINOS")]})
    otp = cap("POST", f"/casos/{caso}/otp", {"canal": "SMS"})["codigo_simulado"]
    cap("POST", f"/casos/{caso}/otp/verificar", {"codigo": otp})
    cap("POST", f"/casos/{caso}/validaciones", {"tipos": ["RENIEC", "LISTAS_NEGRAS", "PEP"]})
    cap("POST", f"/casos/{caso}/consultas-riesgo", {"central": "SBS"})
    cap("POST", f"/casos/{caso}/perfil")
    hab = cap("POST", f"/casos/{caso}/habilitar")
    return {"cod_cliente": hab["cod_cliente"], "estado": hab["estado"], "dni": dni, "celular": cel,
            "nombre": f"{nombres} {paterno}"}


def abrir_cuenta(token, cod_cliente):
    n = int(time.time() * 1000) % 10**15 * 10 + random.randrange(10)
    # La misma apertura que la pantalla /cuenta (frontend/lib/cuentas.ts, abrirCuenta).
    estado, r = pedir("POST", f"{CTA}/apertura", {"num_cuenta": f"CTA-{n:016d}", "cci": f"{n:020d}", "moneda": "PEN",
                      "regimen": "INDIVIDUAL", "id_agencia": "AQP01",
                      "titulares": [{"id_cliente": cod_cliente}]}, token)
    time.sleep(0.01)
    return exigir(estado, r, (201,), "apertura de cuenta")["data"]["num_cuenta"]


def flujo():
    estado, r = pedir("POST", f"{COREDB}/auth/login", {"username": USUARIO, "password": PASSWORD})
    token = exigir(estado, r, (200,), "login del administrador")["access_token"]

    # 1. Cliente nuevo, habilitado por Captación
    cli = captar(token, "Carmen", "Mamani", "Apaza")
    if cli["estado"] != "HABILITADO":
        raise Fallo(f"El cliente debía quedar HABILITADO: {cli}")
    paso(1, f"Captación registró a {cli['nombre']} ({cli['cod_cliente']}) y quedó HABILITADO")

    # 2. Cuenta de ahorros y depósito por ventanilla
    cuenta = abrir_cuenta(token, cli["cod_cliente"])
    ventanilla(token, "deposito", {"num_cuenta": cuenta, "monto": "500.00"})
    paso(2, f"cuenta de ahorros {cuenta} abierta; depósito por ventanilla de S/ 500.00 (saldo {saldo(token, cuenta)})")

    # 3. Tarjeta de débito asociada a la cuenta, activa y con PIN de cajero
    estado, r = pedir("POST", f"{TARJ}/emision", {"cod_cliente": cli["cod_cliente"], "num_cuenta": cuenta},
                      token, {"X-Idempotency-Key": str(uuid.uuid4())})
    tarjeta = exigir(estado, r, (201,), "emisión de la tarjeta")["data"]
    id_tarjeta = tarjeta["id_tarjeta"]
    estado, r = pedir("POST", f"{TARJ}/{id_tarjeta}/estado", {"estado": "ACTIVA"}, token)
    exigir(estado, r, (200,), "activación de la tarjeta")
    estado, r = pedir("PUT", f"{TARJ}/{id_tarjeta}/credenciales/PIN_ATM", {"valor": PIN_ATM}, token)
    exigir(estado, r, (200,), "registro del PIN de cajero")
    paso(3, f"tarjeta {tarjeta['numero_enmascarado']} emitida sobre {cuenta}, ACTIVA y con PIN de cajero")

    # 4. ATM: apertura, PIN, saldo y retiro
    estado, r = pedir("POST", f"{ATM}/apertura", {"username": USUARIO, "password": PASSWORD})
    operador = exigir(estado, r, (200,), "apertura del cajero")["data"]["access_token"]
    estado, r = pedir("POST", f"{ATM}/validar-pin", {"id_tarjeta": id_tarjeta, "pin": PIN_ATM, "id_terminal": TERMINAL},
                      operador, {"X-Idempotency-Key": str(uuid.uuid4())})
    sesion = {"X-ATM-Sesion": exigir(estado, r, (200,), "validación del PIN en el ATM")["data"]["token_sesion"]}
    estado, r = pedir("GET", f"{ATM}/saldo?id_tarjeta={id_tarjeta}", token=operador, cab=sesion)
    cuentas = exigir(estado, r, (200,), "consulta de saldo en el ATM")["data"]["lista_cuentas"]
    visto = next(c["saldo_disponible"] for c in cuentas if c["id_cuenta"] == cuenta)
    if visto != "500.00":
        raise Fallo(f"El ATM debía mostrar 500.00 y mostró {visto}")
    estado, r = pedir("POST", f"{ATM}/autorizar", {"id_tarjeta": id_tarjeta, "num_cuenta": cuenta, "moneda": "PEN",
                      "monto": "100.00", "id_terminal": TERMINAL, "uuid_transaccion": str(uuid.uuid4())},
                      operador, {"X-Idempotency-Key": str(uuid.uuid4()), **sesion})
    aut = exigir(estado, r, (200, 201), "autorización del retiro en el ATM")["data"]
    if not aut.get("aprobada"):
        raise Fallo(f"El retiro debía aprobarse: {aut}")
    estado, r = pedir("POST", f"{ATM}/confirmar", {"uuid_autorizacion": aut["uuid_autorizacion"], "id_terminal": TERMINAL,
                      "resultado": "DISPENSADO"}, operador, {"X-Idempotency-Key": str(uuid.uuid4()), **sesion})
    exigir(estado, r, (200,), "confirmación del retiro en el ATM")
    pedir("POST", f"{ATM}/cerrar-sesion", token=operador, cab=sesion)
    despues = saldo(token, cuenta)
    if despues != "400.00":
        raise Fallo(f"Tras retirar 100.00 el saldo debía ser 400.00 y es {despues}")
    paso(4, f"ATM: PIN correcto, saldo S/ {visto}, retiro de S/ 100.00 dispensado (saldo {despues})")

    # 5. Otro depósito por ventanilla
    ventanilla(token, "deposito", {"num_cuenta": cuenta, "monto": "1000.00"})
    despues = saldo(token, cuenta)
    if despues != "1400.00":
        raise Fallo(f"Tras depositar 1000.00 el saldo debía ser 1400.00 y es {despues}")
    paso(5, f"depósito por ventanilla de S/ 1000.00 (saldo {despues})")

    # 6. Chaski: afiliación y pagos. Hace falta a quién pagar: otro cliente afiliado y un comercio.
    destino = captar(token, "Jorge", "Condori", None)
    cuenta_destino = abrir_cuenta(token, destino["cod_cliente"])
    for c, cta in ((cli, cuenta), (destino, cuenta_destino)):
        estado, r = pedir("POST", f"{COREDB}/billetera/afiliaciones",
                          {"cod_cliente": c["cod_cliente"], "num_cuenta": cta, "pin": PIN_CHASKI}, token)
        exigir(estado, r, (201,), f"afiliación de {c['cod_cliente']} a Chaski")
    ruc = "20" + "".join(random.choices("0123456789", k=9))
    estado, r = pedir("POST", f"{COREDB}/billetera/comercios",
                      {"ruc": ruc, "razon_social": "Bodega de la demo", "num_cuenta": cuenta_destino}, token)
    comercio = exigir(estado, r, (201,), "registro del comercio")

    estado, r = pedir("POST", f"{CHASKI}/login", {"celular": cli["celular"], "pin": PIN_CHASKI})
    s_cli = exigir(estado, r, (200,), "login en Chaski")["token"]
    estado, r = pedir("POST", f"{CHASKI}/transferencias", {"celular_destino": destino["celular"], "monto": 50,
                      "referencia": "Pago de la demo"}, s_cli, {"Idempotency-Key": str(uuid.uuid4())})
    exigir(estado, r, (200,), "envío por celular en Chaski")
    estado, r = pedir("POST", f"{CHASKI}/qr/{comercio['id_qr']}/pagar", {"monto": 20}, s_cli,
                      {"Idempotency-Key": str(uuid.uuid4())})
    exigir(estado, r, (200,), "pago con QR al comercio en Chaski")
    estado, r = pedir("GET", f"{CHASKI}/me", token=s_cli)
    en_app = exigir(estado, r, (200,), "saldo en Chaski")["cuenta"]["saldo_actual"]
    if float(en_app) != 1330.0:
        raise Fallo(f"Tras pagar 50 + 20 el saldo en Chaski debía ser 1330.00 y es {en_app}")
    paso(6, f"afiliado a Chaski; envío de S/ 50.00 a {destino['nombre']} y pago con QR de S/ 20.00 "
            f"(saldo en la app {float(en_app):.2f})")

    # 7. Bloqueo de la tarjeta: el ATM ya no la acepta
    estado, r = pedir("POST", f"{TARJ}/{id_tarjeta}/bloqueo", {"motivo": "Bloqueo de la demo"}, token)
    if exigir(estado, r, (200,), "bloqueo de la tarjeta")["data"]["estado_tarjeta"] != "BLOQUEADA":
        raise Fallo(f"La tarjeta debía quedar BLOQUEADA: {r}")
    estado, r = pedir("POST", f"{ATM}/validar-pin", {"id_tarjeta": id_tarjeta, "pin": PIN_ATM, "id_terminal": TERMINAL},
                      operador, {"X-Idempotency-Key": str(uuid.uuid4())})
    aceptada = estado == 200 and isinstance(r, dict) and (r.get("data") or {}).get("resultado") == "EXITOSO"
    if aceptada:
        raise Fallo(f"El ATM no debía aceptar la tarjeta bloqueada: {estado} {r}")
    motivo = r.get("error_code") or (r.get("data") or {}).get("resultado") if isinstance(r, dict) else r
    paso(7, f"tarjeta BLOQUEADA; el ATM la rechaza ({estado} {motivo})")

    print()
    print("  Datos de la demo (quedan en la base compartida):")
    print(f"    Cliente        {cli['nombre']}  {cli['cod_cliente']}  DNI {cli['dni']}")
    print(f"    Cuenta         {cuenta}  saldo S/ {saldo(token, cuenta)}")
    print(f"    Tarjeta (ATM)  {id_tarjeta}  PIN {PIN_ATM}  (BLOQUEADA)")
    print(f"    Chaski         celular {cli['celular']}  PIN {PIN_CHASKI}")
    print(f"    Destinatario   {destino['nombre']}  celular {destino['celular']}  PIN {PIN_CHASKI}")
    print(f"    Comercio QR    Bodega de la demo  código {comercio['id_qr']}")


if __name__ == "__main__":
    print("Flujo de la demo (profesor):")
    try:
        flujo()
    except Fallo as error:
        print(f"  FALLA  {error}", file=sys.stderr)
        sys.exit(1)
