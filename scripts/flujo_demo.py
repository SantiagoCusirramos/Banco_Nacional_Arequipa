#!/usr/bin/env python3
"""Flujo de demostración del producto integrado, de punta a punta, con un cliente nuevo.

Cliente, cuenta y tarjeta → crédito de 1000.00 → desembolso → consulta en el cajero →
depósito de 1000.00 en ventanilla → pago de 500.00 con la billetera → bloqueo de la tarjeta.

Corre en la máquina que levantó el producto (`./bna up`), con Python 3.9+ y solo la
biblioteca estándar: `python3 scripts/flujo_demo.py`. Hace las mismas peticiones que las
pantallas (por los puentes del frontend, http://localhost:3000/api/...) y, donde no hay
pantalla, va al Bus de Servicios (http://127.0.0.1:8018/bus/...) con la credencial del flujo.
Las claves salen de `.env` (la genera `./bna up`); ninguna se imprime. Contra el clúster de
Infraestructura (scripts/k8s-infra.sh flujo), con BNA_K8S_NAMESPACE, las lee de los pods con
`kubectl exec`. Cada corrida crea datos
nuevos (documentos, celulares y RUC al azar), así que se puede repetir sobre la misma base.

Al final comprueba en COREDB los saldos, el crédito y su calendario, el estado de la tarjeta y
la bitácora. Sale con 0 («Flujo de demostración completo.») o con 1 y el paso que falló.
Documentación: Documents/flujo-demo.md.
"""

import argparse
import json
import os
import random
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
AGENCIA = "AQP01"
CAJERO = "DEV-ATM-01"
MONTO_CREDITO = Decimal("1000.00")
PLAZO_MESES = 6
DEPOSITO = Decimal("1000.00")
PAGO_BILLETERA = Decimal("500.00")


class Fallo(Exception):
    pass


def leer_env(ruta):
    valores = {}
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            if "=" in linea and not linea.lstrip().startswith("#"):
                clave, valor = linea.split("=", 1)
                valores[clave.strip()] = valor.strip()
    return valores


def leer_env_k8s(namespace):
    """Las claves del flujo, de los pods del clúster (k8s/overlays/infraestructura).

    Allí no hay .env local ni Secrets: cada pod tiene en /secretos solo las claves que usa. Se
    leen con `kubectl exec` (KUBECONFIG y KUBECTL del entorno): BUS_TOKEN_PRUEBAS del Bus y el
    administrador de COREDB del archivo de su contenedor de inicio primer-administrador.
    """
    kubectl = os.environ.get("KUBECTL", "kubectl")
    prefijo = os.environ.get("BNA_K8S_PREFIJO", "bna-")

    def archivo(despliegue, contenedor, nombre):
        orden = [kubectl, "-n", namespace, "exec", f"deployment/{prefijo}{despliegue}", "-c", contenedor,
                 "--", "cat", f"/secretos/{nombre}"]
        resultado = subprocess.run(orden, capture_output=True, text=True, timeout=60)
        if resultado.returncode != 0:
            sys.exit(f"No se pudieron leer las claves de {prefijo}{despliegue} con kubectl exec: "
                     f"{resultado.stderr.strip()[:300]}")
        valores = {}
        for linea in resultado.stdout.splitlines():
            if "=" in linea:
                clave, valor = linea.split("=", 1)
                palabras = shlex.split(valor)
                valores[clave] = palabras[0] if palabras else ""
        return valores

    bus = archivo("bus", "bus", "env")
    admin = archivo("coredb", "coredb", "primer-administrador")
    return {
        "BUS_TOKEN_PRUEBAS": bus.get("BUS_TOKEN_PRUEBAS", ""),
        "BNA_ADMIN_USUARIO": admin.get("BNA_ADMIN_USUARIO", ""),
        "BNA_ADMIN_PASSWORD": admin.get("CORE_DB_ADMIN_INICIAL_PASSWORD", ""),
    }


K8S_NAMESPACE = os.environ.get("BNA_K8S_NAMESPACE", "")
ENV = leer_env_k8s(K8S_NAMESPACE) if K8S_NAMESPACE else leer_env(RAIZ / ".env")


def config(nombre, defecto=""):
    return os.environ.get(nombre) or ENV.get(nombre) or defecto


FRONTEND = config("BNA_FRONTEND", f"http://localhost:{config('BNA_PUERTO_FRONTEND', '3000')}").rstrip("/")
BUS = config("BNA_BUS", f"http://127.0.0.1:{config('BNA_PUERTO_BUS', '8018')}").rstrip("/")
TOKEN_BUS = config("BUS_TOKEN_PRUEBAS")
ADMIN = config("BNA_ADMIN_USUARIO", "admin")
CLAVE_ADMIN = config("BNA_ADMIN_PASSWORD")
VERBOSO = False


# ── HTTP ────────────────────────────────────────────────────────────────────

def pedir(metodo, url, cuerpo=None, token=None, cabeceras=None):
    """Devuelve (estado, cuerpo JSON o texto, cabeceras). No lanza por un 4xx o 5xx."""
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    peticion = urllib.request.Request(url, data=datos, method=metodo)
    peticion.add_header("Content-Type", "application/json")
    peticion.add_header("X-Correlation-ID", str(uuid.uuid4()))
    if token:
        peticion.add_header("Authorization", f"Bearer {token}")
    if url.startswith(BUS + "/bus/"):
        peticion.add_header("X-Bus-Token", TOKEN_BUS)
    for nombre, valor in (cabeceras or {}).items():
        peticion.add_header(nombre, valor)
    try:
        with urllib.request.urlopen(peticion, timeout=30) as respuesta:
            estado, texto, hdrs = respuesta.status, respuesta.read().decode(), respuesta.headers
    except urllib.error.HTTPError as error:
        estado, texto, hdrs = error.code, error.read().decode(), error.headers
    except (urllib.error.URLError, OSError) as error:
        raise Fallo(f"{metodo} {url}: sin respuesta ({error}). ¿Está levantado el producto (./bna up)?") from error
    try:
        datos = json.loads(texto) if texto else None
    except ValueError:
        datos = texto
    if VERBOSO:
        print(f"      {metodo} {url} -> {estado}", flush=True)
    return estado, datos, hdrs


def exigir(condicion, mensaje):
    if not condicion:
        raise Fallo(mensaje)


def llamar(metodo, url, esperado, cuerpo=None, token=None, cabeceras=None):
    estado, datos, _ = pedir(metodo, url, cuerpo, token, cabeceras)
    esperados = esperado if isinstance(esperado, tuple) else (esperado,)
    exigir(estado in esperados, f"{metodo} {url}: se esperaba {esperado} y respondió {estado}: {datos}")
    return datos


def datos_de(sobre):
    """CUENTAS, TARJETAS, CAPTACION y el cajero responden {success, data}; COREDB, el dato."""
    return sobre["data"] if isinstance(sobre, dict) and "data" in sobre and "success" in sobre else sobre


def llave():
    return str(uuid.uuid4())


# Puentes del frontend (lo que llama cada pantalla desde el navegador).
def api(ruta):
    return f"{FRONTEND}/api/{ruta}"


def coredb(ruta):
    """COREDB por el Bus, para lo que no tiene pantalla y para comprobar."""
    return f"{BUS}/bus/coredb/coredb/{ruta}"


def operacion_ventanilla(clave):
    # Las mismas cabeceras que pone la pantalla /cuenta (frontend/lib/api.ts): canal VEN.
    return {"X-Idempotency-Key": clave, "X-Channel-ID": "VEN",
            "X-Request-Timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def digitos(n):
    return "".join(random.choices("0123456789", k=n))


def saldo(numero, token):
    return Decimal(llamar("GET", coredb(f"cuentas/{numero}"), 200, token=token)["saldo_disponible"])


# ── Registro de pasos ───────────────────────────────────────────────────────

PASOS = []


def paso(numero, titulo, donde, usuario, resultado, despues=""):
    PASOS.append({"paso": numero, "titulo": titulo, "donde": donde, "usuario": usuario,
                  "resultado": resultado, "despues": despues})
    print(f"\n[{numero}] {titulo}", flush=True)
    print(f"    dónde:     {donde}")
    print(f"    usuario:   {usuario}")
    print(f"    resultado: {resultado}")
    if despues:
        print(f"    después:   {despues}")


def captar(token, nombres, apellido_paterno, apellido_materno):
    """Pantalla /captacion: solicitante → caso → consentimientos → OTP → validaciones →
    central de riesgo → perfil → habilitar. Devuelve el cliente que crea en COREDB."""
    cap = api("captacion")
    # Documento al azar que termina en 1: la central simulada de CAPTACION lo califica NORMAL.
    dni = "4" + digitos(6) + "1"
    celular = "9" + digitos(8)
    solicitante = datos_de(llamar("POST", f"{cap}/solicitantes", 201, {
        "tipo_documento": "DNI", "numero_documento": dni, "nombres": nombres,
        "apellido_paterno": apellido_paterno, "apellido_materno": apellido_materno,
        "celular": celular, "correo": f"demo.{dni}.{digitos(4)}@example.com"}, token))["solicitante"]
    caso = datos_de(llamar("POST", f"{cap}/casos", 201, {
        "id_solicitante": solicitante["id_solicitante"], "canal": "AGENCIA", "id_agencia": AGENCIA,
        "producto_interes": None}, token))["id_caso"]
    llamar("POST", f"{cap}/casos/{caso}/consentimientos", 201, {"consentimientos": [
        {"tipo": t, "aceptado": True, "medio": "FISICO"}
        for t in ("TRATAMIENTO_DATOS", "CONSULTA_BUROS", "TERMINOS")]}, token)
    otp = datos_de(llamar("POST", f"{cap}/casos/{caso}/otp", 201, {"canal": "SMS"}, token))
    llamar("POST", f"{cap}/casos/{caso}/otp/verificar", 200, {"canal": "SMS", "codigo": otp["codigo_simulado"]}, token)
    llamar("POST", f"{cap}/casos/{caso}/validaciones", 201, {"tipos": ["RENIEC", "LISTAS_NEGRAS", "PEP"]}, token)
    llamar("POST", f"{cap}/casos/{caso}/consultas-riesgo", 201, {"central": "SBS"}, token)
    llamar("POST", f"{cap}/casos/{caso}/perfil", 201, None, token)
    habilitado = datos_de(llamar("POST", f"{cap}/casos/{caso}/habilitar", 200, None, token))
    exigir(habilitado["estado"] == "HABILITADO", f"El caso no quedó HABILITADO: {habilitado}")
    return {"cod_cliente": habilitado["cod_cliente"], "dni": dni, "celular": celular, "caso": caso,
            "nombre": f"{nombres} {apellido_paterno}"}


def abrir_cuenta(token, cod_cliente):
    """Pantalla /cuenta, «Abrir cuenta»: CUENTAS /apertura (la pantalla genera número y CCI)."""
    return datos_de(llamar("POST", api("cuenta/apertura"), 201, {
        "num_cuenta": digitos(14), "cci": digitos(20), "moneda": "PEN", "regimen": "INDIVIDUAL",
        "id_agencia": AGENCIA, "titulares": [{"id_cliente": cod_cliente}]}, token))["num_cuenta"]


def crear_usuario(token, prefijo, rol, nombre):
    """Pantalla /login, «Crear usuario interno» (POST /coredb/usuarios, solo ADMINISTRADOR)."""
    usuario = prefijo + uuid.uuid4().hex[:8]
    clave = "demo-" + uuid.uuid4().hex
    llamar("POST", api("core/coredb/usuarios"), 201,
           {"username": usuario, "nombre": nombre, "password": clave, "rol": rol}, token)
    sesion = llamar("POST", api("core/coredb/auth/login"), 200, {"username": usuario, "password": clave})
    return usuario, clave, sesion["access_token"]


def sol(metodo, ruta, cuerpo=None, cookie=None, clave=None):
    """Proxy de la pantalla /solicitud-credito: Origin del frontend y cookie de sesión, sin token."""
    cabeceras = {"Origin": FRONTEND}
    if cookie:
        cabeceras["Cookie"] = cookie
    if clave:
        cabeceras["X-Idempotency-Key"] = clave
    return pedir(metodo, api(f"solicitud-credito/{ruta}"), cuerpo, None, cabeceras)


def bitacora(token, id_entidad):
    eventos = llamar("GET", coredb(f"auditoria?id_entidad={id_entidad}&limite=200"), 200, token=token)
    return [(e["modulo"], e["accion"], e["actor"]) for e in eventos]


# ── El flujo ────────────────────────────────────────────────────────────────

def flujo():
    exigir(CLAVE_ADMIN, "Falta BNA_ADMIN_PASSWORD (en .env, la crea ./bna up)")
    exigir(TOKEN_BUS, "Falta BUS_TOKEN_PRUEBAS (en .env, la crea ./bna up)")
    print(f"Frontend {FRONTEND} · Bus {BUS}")

    # 0. Sesión del administrador (pantalla /login).
    token = llamar("POST", api("core/coredb/auth/login"), 200,
                   {"username": ADMIN, "password": CLAVE_ADMIN})["access_token"]
    perfil = llamar("GET", api("core/coredb/auth/me"), 200, token=token)
    exigir(perfil["rol"] == "ADMINISTRADOR", f"{ADMIN} no es ADMINISTRADOR: {perfil}")
    paso(0, "Login del administrador", "Pantalla /login → POST /api/core/coredb/auth/login (COREDB por el Bus)",
         ADMIN, "token de COREDB, rol ADMINISTRADOR")

    # 1. Cliente por Captación.
    cliente = captar(token, "Lucía", "Mamani", "Torres")
    en_core = llamar("GET", coredb(f"clientes/{cliente['cod_cliente']}"), 200, token=token)
    exigir(en_core["estado_cliente"] == "ACTIVO" and en_core["estado_habilitante"] == "HABILITADO",
           f"El cliente debía quedar ACTIVO y HABILITADO en COREDB: {en_core}")
    paso("1a", "Crear el cliente (Captación)",
         "Pantalla /captacion → /api/captacion/solicitantes, /casos, consentimientos, OTP, validaciones, "
         "consultas-riesgo, perfil, habilitar (CAPTACION por el Bus)", ADMIN,
         f"cliente {cliente['cod_cliente']} {cliente['nombre']}, ACTIVO y HABILITADO (caso {cliente['caso'][:8]}…)")

    # 1b. Cuenta de ahorros.
    cuenta = abrir_cuenta(token, cliente["cod_cliente"])
    exigir(saldo(cuenta, token) == 0, "La cuenta nueva debía tener saldo 0.00")
    paso("1b", "Abrir la cuenta de ahorros", "Pantalla /cuenta → POST /api/cuenta/apertura (CUENTAS → COREDB)",
         ADMIN, f"cuenta {cuenta} (PEN, INDIVIDUAL, agencia {AGENCIA})", "saldo 0.00")

    # 1c. Tarjeta de débito: emisión, activación y PIN del cajero.
    clave_emision = llave()
    tarjeta = datos_de(llamar("POST", api("tarjeta/emision"), 201,
                              {"cod_cliente": cliente["cod_cliente"], "num_cuenta": cuenta}, token,
                              {"X-Idempotency-Key": clave_emision}))
    id_tarjeta = tarjeta["id_tarjeta"]
    exigir(tarjeta["estado_tarjeta"] == "PENDIENTE_ACTIVACION", f"Emisión inesperada: {tarjeta}")
    activa = datos_de(llamar("POST", api(f"tarjeta/{id_tarjeta}/estado"), 200, {"estado": "ACTIVA"}, token))
    exigir(activa["estado_tarjeta"] == "ACTIVA", f"Activación inesperada: {activa}")
    pin = digitos(4)
    llamar("PUT", api(f"tarjeta/{id_tarjeta}/credenciales/PIN_ATM"), 200, {"valor": pin}, token)
    paso("1c", "Emitir y activar la tarjeta; asignar el PIN del cajero",
         "Pantalla /tarjetas → /api/tarjeta/emision, /{id}/estado (ACTIVA), PUT /{id}/credenciales/PIN_ATM "
         "(TARJETAS → COREDB)", ADMIN,
         f"tarjeta {id_tarjeta} ({tarjeta.get('numero_enmascarado', '')}) ACTIVA, PIN de 4 dígitos registrado",
         "tarjeta ACTIVA")

    # 2. Crédito de 1000.00 por SOL (asesora) y Evaluación.
    asesora, clave_asesora, _ = crear_usuario(token, "asesora", "ASESOR", "Asesora de la demo")
    estado, respuesta, hdrs = sol("POST", "auth/login", {"username": asesora, "password": clave_asesora})
    exigir(estado == 200, f"Login de SOL: {estado} {respuesta}")
    cookie = (hdrs.get("Set-Cookie") or "").split(";", 1)[0]
    exigir(cookie.startswith("bna_sol_session="), "SOL no dejó la cookie de sesión")
    estado, politica, _ = sol("GET", "policy", cookie=cookie)
    exigir(estado == 200 and politica.get("integracion") == "REAL", f"Política de SOL: {estado} {politica}")
    exigir(Decimal(politica["monto_minimo"]) <= MONTO_CREDITO <= Decimal(politica["monto_maximo"]),
           f"1000.00 está fuera de la política de SOL: {politica}")
    estado, encontrados, _ = sol("POST", "clients/search", {"search": cliente["dni"]}, cookie=cookie)
    exigir(estado == 200 and [c["id_cliente"] for c in encontrados] == [cliente["cod_cliente"]],
           f"SOL no encontró al cliente en CAPTACION: {estado} {encontrados}")
    borrador = {"id_cliente": cliente["cod_cliente"], "monto_solicitado": str(MONTO_CREDITO), "moneda": "PEN",
                "plazo_meses": PLAZO_MESES, "destino_credito": "Capital de trabajo (demo)",
                "fecha_base": time.strftime("%Y-%m-%d", time.gmtime(time.time() + 86400)), "pago_doble": False,
                "garantias": [], "fiadores": []}
    estado, solicitud, _ = sol("POST", "applications", borrador, cookie=cookie)
    exigir(estado == 201 and solicitud["estado"] == "REGISTRADA", f"Borrador de SOL: {estado} {solicitud}")
    id_solicitud = solicitud["id"]
    estado, enviada, _ = sol("POST", f"applications/{id_solicitud}/send", {"revision": solicitud["revision"]},
                             cookie=cookie, clave=llave())
    exigir(estado == 200 and enviada["estado"] == "EN_EVALUACION", f"Envío a Evaluación: {estado} {enviada}")
    paso("2a", "Pedir el crédito de 1000.00 a 6 meses",
         "Pantalla /solicitud-credito → /api/solicitud-credito/auth/login, clients/search, applications, "
         "applications/{id}/send (SOL → CAPTACION CR-INT-01 y EVALUACION CR-INT-02, por el Bus)",
         f"{asesora} (ASESOR, creado en /login)",
         f"solicitud {id_solicitud} EN_EVALUACION (calendario PRELIMINAR en COREDB)")

    evaluada = llamar("POST", api(f"evaluacion/solicitudes/{id_solicitud}/evaluaciones"), 200, {
        "versionSolicitud": 1, "ingresoMensual": "3500.00", "deudaMensual": "0.00", "riesgo": "BUENO",
        "verificada": True}, token)
    exigir(evaluada["resultado"] == "APROBADO" and evaluada["estadoSolicitud"] == "APROBADA",
           f"La evaluación debía aprobar: {evaluada}")
    paso("2b", "Evaluar la solicitud",
         "Pantalla /evaluacion → POST /api/evaluacion/solicitudes/{id}/evaluaciones (EVALUACION → COREDB)",
         ADMIN, f"APROBADO por la regla (evaluación {evaluada['idEvaluacion']})", "solicitud APROBADA")

    # 3. Desembolso por un operador.
    operador, clave_operador, token_op = crear_usuario(token, "operador", "OPERADOR", "Operador de la demo")
    des = api("desembolso")
    verificacion = llamar("POST", f"{des}/identidad", 201, {"tipoDocumento": "DNI", "numeroDocumento": cliente["dni"],
                                                           "identidadVerificada": True}, token_op)
    exigir(verificacion["resultado"] == "APROBADO" and verificacion["codCliente"] == cliente["cod_cliente"],
           f"Verificación de identidad: {verificacion}")
    aprobaciones = llamar("GET", f"{des}/aprobaciones?codCliente={cliente['cod_cliente']}", 200, token=token_op)
    exigir([a["idEvaluacion"] for a in aprobaciones] == [evaluada["idEvaluacion"]],
           f"Desembolso debía ver la aprobación: {aprobaciones}")
    elegibles = llamar("GET", f"{des}/clientes/{cliente['cod_cliente']}/cuentas?moneda=PEN", 200, token=token_op)
    exigir(cuenta in {c["numCuenta"] for c in elegibles if c["elegible"]}, f"La cuenta no admite el abono: {elegibles}")
    orden = llamar("POST", f"{des}/ordenes", 201, {"idEvaluacion": evaluada["idEvaluacion"], "numCuenta": cuenta},
                   token_op, {"X-Idempotency-Key": llave()})
    exigir(orden["estado"] == "PREPARADA" and Decimal(orden["importe"]) == MONTO_CREDITO, f"Orden: {orden}")
    llamar("POST", f"{des}/ordenes/{orden['idOrden']}/validaciones", 201, {
        "tipo": "IDENTIDAD", "resultado": "APROBADA", "referenciaEvidencia": str(verificacion["idValidacion"])},
        token_op)
    confirmada = llamar("POST", f"{des}/ordenes/{orden['idOrden']}/confirmacion", 201, token=token_op)
    cod_credito = confirmada["codCredito"]
    exigir(confirmada["estado"] == "CONFIRMADA", f"Confirmación: {confirmada}")
    exigir(saldo(cuenta, token) == MONTO_CREDITO, "El abono del desembolso debía dejar 1000.00")
    paso(3, "Desembolsar el crédito",
         "Pantalla /desembolso → /api/desembolso/identidad, aprobaciones, clientes/{cod}/cuentas, ordenes, "
         "ordenes/{id}/validaciones, ordenes/{id}/confirmacion (DESEMBOLSO → COREDB)",
         f"{operador} (OPERADOR, creado en /login)",
         f"orden {orden['codigoOrden']} CONFIRMADA, crédito {cod_credito}", f"saldo {saldo(cuenta, token)}")

    # 4. Consulta en el cajero: apertura del operador, PIN y saldo.
    atm = f"{BUS}/bus/atm/api"
    apertura = datos_de(llamar("POST", f"{atm}/apertura", 200, {"username": operador, "password": clave_operador}))
    token_cajero = apertura["access_token"]
    validacion = datos_de(llamar("POST", f"{atm}/validar-pin", 200,
                                 {"id_tarjeta": id_tarjeta, "pin": pin, "id_terminal": CAJERO}, token_cajero))
    exigir(validacion["resultado"] == "EXITOSO" and validacion["token_sesion"], f"PIN en el cajero: {validacion}")
    sesion_atm = {"X-ATM-Sesion": validacion["token_sesion"]}
    consulta = datos_de(llamar("GET", f"{atm}/saldo?id_tarjeta={id_tarjeta}", 200, token=token_cajero,
                               cabeceras=sesion_atm))
    mostradas = [(c["id_cuenta"], Decimal(c["saldo_disponible"])) for c in consulta["lista_cuentas"]]
    exigir(mostradas == [(cuenta, MONTO_CREDITO)], f"El cajero debía mostrar la cuenta {cuenta} con 1000.00: {consulta}")
    paso(4, "Consultar el saldo en el cajero",
         f"Pantalla del cajero (http://127.0.0.1:8019) → /api/apertura, /api/validar-pin, /api/saldo "
         f"(ATM → TARJETAS y CUENTAS por el Bus), terminal {CAJERO}",
         f"{operador} abre el cajero; el cliente usa su tarjeta y PIN",
         f"saldo mostrado {mostradas[0][1]:.2f} ({consulta['lista_cuentas'][0]['num_cuenta_enmascarado']})",
         "sin cambios: 1000.00")
    llamar("POST", f"{atm}/cerrar-sesion", 200, {}, token_cajero, sesion_atm)

    # 5. Depósito de 1000.00 en ventanilla.
    clave_deposito = llave()
    deposito = datos_de(llamar("POST", api("cuenta/deposito"), 201, {"num_cuenta": cuenta, "monto": str(DEPOSITO)},
                               token, operacion_ventanilla(clave_deposito)))
    repetido = datos_de(llamar("POST", api("cuenta/deposito"), 201, {"num_cuenta": cuenta, "monto": str(DEPOSITO)},
                               token, operacion_ventanilla(clave_deposito)))
    exigir(repetido["replay"] is True and repetido["uuid_transaccion"] == deposito["uuid_transaccion"],
           f"Repetir el depósito con la misma llave no debía moverlo otra vez: {repetido}")
    esperado = MONTO_CREDITO + DEPOSITO
    exigir(saldo(cuenta, token) == esperado, f"Tras el depósito el saldo debía ser {esperado}")
    paso(5, "Depositar 1000.00 en ventanilla",
         "Pantalla /cuenta, «Depositar» → POST /api/cuenta/deposito con X-Channel-ID VEN (CUENTAS → COREDB)",
         ADMIN, f"depósito {deposito['uuid_transaccion']} (la repetición con la misma llave no lo duplica)",
         f"saldo {saldo(cuenta, token)}")

    # 6. Pago de 500.00 con la billetera Chaski en un comercio.
    pin_billetera = digitos(6)
    afiliada = llamar("POST", coredb("billetera/afiliaciones"), 201,
                      {"cod_cliente": cliente["cod_cliente"], "num_cuenta": cuenta, "pin": pin_billetera}, token)
    exigir(afiliada["estado"] == "ACTIVA", f"Afiliación: {afiliada}")
    comercio_cliente = captar(token, "Marco", "Condori", "Apaza")
    cuenta_comercio = abrir_cuenta(token, comercio_cliente["cod_cliente"])
    ruc = "20" + digitos(9)
    comercio = llamar("POST", coredb("billetera/comercios"), 201,
                      {"ruc": ruc, "razon_social": f"Bodega Demo {ruc[-4:]}", "num_cuenta": cuenta_comercio}, token)
    paso("6a", "Afiliar la billetera y registrar el comercio",
         "Sin pantalla: curl al Bus → POST /bus/coredb/coredb/billetera/afiliaciones y /billetera/comercios; "
         "el dueño del comercio pasa por /captacion y /cuenta como el cliente", ADMIN,
         f"billetera de {cliente['cod_cliente']} ACTIVA sobre {cuenta}; comercio {comercio['razon_social']} "
         f"(cuenta {cuenta_comercio}, QR estático)")

    chaski = f"{BUS}/bus/billetera/api"
    sesion_cliente = llamar("POST", f"{chaski}/login", 200, {"celular": cliente["celular"], "pin": pin_billetera})["token"]
    comercios = llamar("GET", f"{chaski}/comercios", 200, token=sesion_cliente)
    id_qr = next((c["id_qr"] for c in comercios if c["id_comercio"] == comercio["id_comercio"]), None)
    exigir(id_qr, f"El comercio no aparece en la billetera: {comercios}")
    clave_pago = {"Idempotency-Key": llave()}
    pago = llamar("POST", f"{chaski}/qr/{id_qr}/pagar", 200, {"monto": float(PAGO_BILLETERA)}, sesion_cliente, clave_pago)
    otra_vez = llamar("POST", f"{chaski}/qr/{id_qr}/pagar", 200, {"monto": float(PAGO_BILLETERA)}, sesion_cliente,
                      clave_pago)
    exigir(otra_vez.get("repetida") is True and otra_vez["id_pago"] == pago["id_pago"],
           f"Repetir el pago con la misma llave no debía cobrar otra vez: {otra_vez}")
    esperado -= PAGO_BILLETERA
    exigir(saldo(cuenta, token) == esperado, f"Tras el pago el saldo debía ser {esperado}")
    exigir(saldo(cuenta_comercio, token) == PAGO_BILLETERA, "El comercio debía recibir 500.00")
    paso("6b", "Pagar 500.00 con la billetera en el comercio",
         "App Chaski (sin compilar): curl al Bus → /bus/billetera/api/login, /comercios, /qr/{id}/pagar "
         "(BILLETERA → COREDB, canal BD)", f"el cliente, con su celular y PIN de billetera",
         f"pago {pago['id_pago']} (la repetición con la misma llave no lo duplica)",
         f"saldo {saldo(cuenta, token)}; comercio {saldo(cuenta_comercio, token)}")

    # 7. Bloqueo de la tarjeta desde el Home Banking: la petición del botón «Bloquear» de cuentas.html.
    bloqueada = datos_de(llamar("POST", api(f"tarjeta/{id_tarjeta}/bloqueo"), 200,
                                {"motivo": "Bloqueo solicitado por el cliente en Home Banking"}, token))
    exigir(bloqueada["estado_tarjeta"] == "BLOQUEADA", f"Bloqueo: {bloqueada}")
    estado, respuesta, _ = pedir("POST", f"{atm}/validar-pin",
                                 {"id_tarjeta": id_tarjeta, "pin": pin, "id_terminal": CAJERO}, token_cajero)
    rechazada = estado != 200 or datos_de(respuesta).get("resultado") != "EXITOSO"
    exigir(rechazada, f"El cajero no debía aceptar la tarjeta bloqueada: {estado} {respuesta}")
    paso(7, "Bloquear la tarjeta",
         "Home Banking /homebanking/cuentas.html, «Mis tarjetas» → «Bloquear» y confirmar → "
         "POST /api/tarjeta/{id}/bloqueo (TARJETAS por el Bus → COREDB)",
         f"{ADMIN} (usuario del banco que atiende al cliente en el Home Banking)",
         f"tarjeta BLOQUEADA; el cajero ya no la acepta ({estado})", "tarjeta BLOQUEADA")

    # 8. Comprobación en COREDB.
    final = saldo(cuenta, token)
    exigir(final == Decimal("1500.00"), f"Saldo final {final}, se esperaba 1500.00")
    movimientos = llamar("GET", coredb(f"movimientos/cuenta/{cuenta}"), 200, token=token)
    leidos = sorted((m["tipo_operacion"], m["naturaleza"], m["monto"], m["id_canal"]) for m in movimientos)
    exigir(leidos == [("DEPOSITO", "C", "1000.00", "VEN"), ("DESEMBOLSO", "C", "1000.00", "VEN"),
                      ("TRANSFERENCIA_ENVIADA", "D", "500.00", "BD")],
           f"Movimientos inesperados en {cuenta}: {leidos}")
    credito = llamar("GET", coredb(f"creditos/{cod_credito}"), 200, token=token)
    cuotas = credito["cuotas"]
    capital = sum(Decimal(c["capital"]) for c in cuotas)
    exigir(credito["estado"] == "AL_DIA" and credito["codCliente"] == cliente["cod_cliente"]
           and Decimal(credito["montoDesembolsado"]) == MONTO_CREDITO and len(cuotas) == PLAZO_MESES
           and capital == MONTO_CREDITO and all(c["estado"] == "PENDIENTE" for c in cuotas)
           and [e["accion"] for e in credito["eventos"]] == ["CREAR_CREDITO"],
           f"El crédito debía estar AL_DIA con {PLAZO_MESES} cuotas PENDIENTES que suman 1000.00 de capital: {credito}")
    detalle = llamar("GET", coredb(f"creditos/solicitudes/{id_solicitud}"), 200, token=token)
    exigir(detalle["estado"] == "DESEMBOLSADA" and detalle["calendario"]["tipo"] == "OFICIAL",
           f"La solicitud debía quedar DESEMBOLSADA con calendario OFICIAL: {detalle['estado']}")
    tarjeta_core = datos_de(llamar("GET", api(f"tarjeta/{id_tarjeta}"), 200, token=token))
    exigir(tarjeta_core["estado_tarjeta"] == "BLOQUEADA", f"La tarjeta debía seguir BLOQUEADA: {tarjeta_core}")

    # La bitácora: cada paso deja su evento con el usuario que lo hizo. El resultado de la
    # evaluación vuelve a SOL (CR-INT-03) en el siguiente ciclo de EVALUACION: se espera hasta 60 s.
    esperados = [
        (cliente["cod_cliente"], "REGISTRAR_CLIENTE", "svc-captacion"),
        (cuenta, "ABRIR_CUENTA", ADMIN),
        (id_tarjeta, "EMITIR_TARJETA", ADMIN),
        (id_tarjeta, "CAMBIAR_ESTADO_TARJETA", ADMIN),
        (id_solicitud, "CREAR_BORRADOR", asesora),
        (id_solicitud, "ENVIAR_CR_INT_02", asesora),
        (id_solicitud, "REGISTRAR_SOLICITUD", "svc-evaluacion"),
        (evaluada["idEvaluacion"], "EVALUAR_SOLICITUD", ADMIN),
        (deposito["uuid_transaccion"], "DEPOSITO", ADMIN),
        (cliente["cod_cliente"], "AFILIAR", ADMIN),
        (pago["id_pago"], "OPERACION_QR", f"cliente:{cliente['cod_cliente']}"),
        (id_solicitud, "RECIBIR_CR_INT_03", "servicio:EVALUACION"),
    ]
    limite = time.monotonic() + 60
    faltan = esperados
    while True:
        faltan = [(i, a, u) for i, a, u in esperados if (a, u) not in {(x[1], x[2]) for x in bitacora(token, i)}]
        if not faltan or time.monotonic() > limite:
            break
        time.sleep(3)
    exigir(not faltan, f"Faltan eventos en la bitácora: {faltan}")
    abono = [m for m in movimientos if m["tipo_operacion"] == "DESEMBOLSO"][0]
    exigir(("DESEMBOLSO", operador) in {(x[1], x[2]) for x in bitacora(token, abono["uuid_transaccion"])},
           "La bitácora debía tener el abono del desembolso a nombre del operador")

    print("\n[8] Comprobación en COREDB")
    print(f"    movimientos de {cuenta}:")
    for tipo, naturaleza, monto, canal in leidos:
        print(f"      {tipo:<24} {naturaleza} {monto:>10} canal {canal}")
    print(f"    crédito {cod_credito}: {credito['estado']}, desembolsado {credito['montoDesembolsado']}, "
          f"{len(cuotas)} cuotas, capital {capital}, saldo pendiente {credito['saldoPendiente']}")
    for c in cuotas:
        print(f"      cuota {c['numeroCuota']}: vence {c['fechaVencimiento']}  capital {c['capital']:>7}  "
              f"interés {c['interes']:>6}  total {c['cuotaTotal']:>7}  {c['estado']}")
    print(f"    solicitud {id_solicitud}: {detalle['estado']}, calendario {detalle['calendario']['tipo']}")
    print(f"    tarjeta {id_tarjeta}: {tarjeta_core['estado_tarjeta']}")
    print("    bitácora: " + ", ".join(sorted({a for _, a, _ in esperados} | {"DESEMBOLSO"})))
    print(f"\nSaldo final de {cuenta}: {final} (1000.00 del crédito + 1000.00 de ventanilla - 500.00 de la billetera)")
    return {"cliente": cliente["cod_cliente"], "cuenta": cuenta, "tarjeta": id_tarjeta, "solicitud": id_solicitud,
            "credito": cod_credito, "saldo_final": str(final), "pasos": PASOS}


def main():
    global VERBOSO
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-v", "--verboso", action="store_true", help="muestra cada petición y su estado")
    parser.add_argument("--json", metavar="ARCHIVO", help="guarda el resultado de cada paso en un JSON")
    args = parser.parse_args()
    VERBOSO = args.verboso
    try:
        resultado = flujo()
    except Fallo as fallo:
        print(f"\nFALLÓ después del paso {PASOS[-1]['paso'] if PASOS else 'inicial'}: {fallo}", file=sys.stderr)
        return 1
    if args.json:
        Path(args.json).write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nFlujo de demostración completo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
