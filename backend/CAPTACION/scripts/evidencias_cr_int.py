"""Evidencias de las integraciones de CAPTACION (guía del Comité de Créditos, 22/11/2026).

Ejecuta, contra el producto levantado y solo a través del Bus de Servicios, los casos que la guía
exige antes de decir «integrado» para las interfaces de Captación:

  CR-INT-09  CAPTACION ↔ Clientes (COREDB): alta y validación del identificador maestro del cliente.
  CR-INT-01  CAPTACION → SOL: SOL obtiene un cliente habilitado (consulta, no envío).
  CR-INT-10  Seguridad: autenticación, autorización por rol y bitácora (parte de Captación).

Cada caso guarda la petición, el código HTTP, la respuesta y el resultado (PASA / FALLA), con un
X-Correlation-ID propio. Los documentos, celulares y correos salen enmascarados y ningún token ni
clave se escribe. Imprime el JSON de evidencias por la salida estándar y el avance por la de error.

Uso (lo hace scripts/evidencias_cr_int.sh, dentro del contenedor del Bus):
  E2E_BUS=http://127.0.0.1:8018 BUS_TOKEN=<BUS_TOKEN_PRUEBAS> BNA_ADMIN_PASSWORD=... \
  CAP_SOL_TOKEN=... python evidencias_cr_int.py > evidencias.json

Solo usa la biblioteca estándar. Cada corrida crea clientes ficticios nuevos.
"""

import datetime
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
import uuid

BUS = os.environ.get("E2E_BUS", "http://127.0.0.1:8018").rstrip("/")
TOKEN_BUS = os.environ.get("BUS_TOKEN", "")
TOKEN_SOL = os.environ.get("CAP_SOL_TOKEN", "")
USUARIO = os.environ.get("BNA_ADMIN_USUARIO", "admin")
PASSWORD = os.environ.get("BNA_ADMIN_PASSWORD", "")
COREDB = f"{BUS}/bus/coredb"
CAPTACION = f"{BUS}/bus/captacion"
CAP = f"{CAPTACION}/api/v1/captacion"
SOL = f"{BUS}/bus/sol/sol"
AGENCIA = "AQP01"

SECRETOS = set()
CLAVES_DOCUMENTO = {"numero_documento", "documento", "search"}
CLAVES_CONTACTO = {"celular", "correo", "celular_destino"}
CLAVES_SECRETAS = {"password", "clave", "access_token", "token", "codigo", "codigo_simulado", "token_sesion"}


def si_no(valor):
    return "sí" if valor is True else "no" if valor is False else str(valor)


def ahora():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def enmascarar(valor):
    """Documento o celular: solo los dos últimos dígitos. Correo: la primera letra y el dominio."""
    if not isinstance(valor, str):
        return valor
    if "@" in valor:
        local, _, dominio = valor.partition("@")
        return f"{local[:1]}***@{dominio}"
    return "*" * max(0, len(valor) - 2) + valor[-2:]


def limpiar(datos):
    """Copia sin secretos: enmascara documentos y contactos y borra tokens, claves y códigos OTP."""
    if isinstance(datos, dict):
        salida = {}
        for clave, valor in datos.items():
            if clave in CLAVES_SECRETAS:
                salida[clave] = "[oculto]"
            elif clave in CLAVES_DOCUMENTO | CLAVES_CONTACTO:
                salida[clave] = enmascarar(valor)
            else:
                salida[clave] = limpiar(valor)
        return salida
    if isinstance(datos, list):
        return [limpiar(v) for v in datos]
    if isinstance(datos, str):
        for secreto in SECRETOS:
            if secreto and secreto in datos:
                datos = datos.replace(secreto, "[oculto]")
        return datos
    return datos


def ruta_publica(url):
    """La ruta sin el host del Bus y con los documentos de la URL enmascarados."""
    ruta = url[len(BUS):] if url.startswith(BUS) else url
    return re.sub(r"\d{6,}", lambda m: enmascarar(m.group(0)), ruta)


def pedir(metodo, url, cuerpo=None, token=None, cabeceras=None, bus=True):
    """(estado, cuerpo JSON o texto, id de correlación). No lanza por un 4xx o 5xx."""
    correlacion = str(uuid.uuid4())
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    peticion = urllib.request.Request(url, data=datos, method=metodo)
    peticion.add_header("X-Correlation-ID", correlacion)
    if datos is not None:
        peticion.add_header("Content-Type", "application/json")
    if token:
        SECRETOS.add(token)
        peticion.add_header("Authorization", f"Bearer {token}")
    if bus and TOKEN_BUS:
        peticion.add_header("X-Bus-Token", TOKEN_BUS)
    for nombre, valor in (cabeceras or {}).items():
        peticion.add_header(nombre, valor)
    try:
        with urllib.request.urlopen(peticion, timeout=20) as respuesta:
            estado, texto = respuesta.status, respuesta.read().decode()
    except urllib.error.HTTPError as error:
        estado, texto = error.code, error.read().decode()
    try:
        return estado, json.loads(texto), correlacion
    except ValueError:
        return estado, texto, correlacion


class Registro:
    def __init__(self):
        self.casos = []

    def caso(self, codigo, cr_int, tipo, descripcion, esperado, intercambios, paso_ok, observado):
        resultado = "PASA" if paso_ok else "FALLA"
        self.casos.append({
            "codigo": codigo, "cr_int": cr_int, "tipo": tipo, "descripcion": descripcion,
            "esperado": esperado, "obtenido": observado, "resultado": resultado, "fecha": ahora(),
            "intercambios": intercambios,
        })
        print(f"  {resultado}  {codigo} {descripcion}", file=sys.stderr)


def intercambio(metodo, url, cuerpo, estado, respuesta, correlacion, nota=None):
    item = {"metodo": metodo, "ruta": ruta_publica(url), "peticion": limpiar(cuerpo), "http": estado,
            "respuesta": limpiar(respuesta), "x_correlation_id": correlacion}
    if nota:
        item["nota"] = nota
    return item


def llamar(metodo, url, cuerpo=None, token=None, cabeceras=None, bus=True, nota=None):
    estado, respuesta, correlacion = pedir(metodo, url, cuerpo, token, cabeceras, bus)
    return estado, respuesta, intercambio(metodo, url, cuerpo, estado, respuesta, correlacion, nota)


def exigir(condicion, mensaje):
    if not condicion:
        raise SystemExit(f"No se puede continuar: {mensaje}")


def dni_nuevo(ultimo="1"):
    return "4" + "".join(random.choices("0123456789", k=6)) + ultimo


def main():
    exigir(PASSWORD and TOKEN_SOL and TOKEN_BUS, "faltan BNA_ADMIN_PASSWORD, CAP_SOL_TOKEN o BUS_TOKEN")
    SECRETOS.update({PASSWORD, TOKEN_SOL, TOKEN_BUS})
    reg = Registro()
    inicio = ahora()

    # ── Sesiones: administrador, una asesora y un analista (usuarios ficticios de COREDB) ──────
    estado, sesion, _ = pedir("POST", f"{COREDB}/coredb/auth/login", {"username": USUARIO, "password": PASSWORD})
    exigir(estado == 200, f"login del administrador: {estado}")
    admin = sesion["access_token"]
    SECRETOS.add(admin)

    def usuario(rol):
        nombre, clave = rol.lower()[:2] + uuid.uuid4().hex[:10], "clave-" + uuid.uuid4().hex
        SECRETOS.add(clave)
        estado, _, _ = pedir("POST", f"{COREDB}/coredb/usuarios", {"username": nombre, "password": clave,
                                                                  "nombre": f"{rol.title()} de evidencias", "rol": rol}, admin)
        exigir(estado == 201, f"alta del usuario {rol}: {estado}")
        estado, datos, _ = pedir("POST", f"{COREDB}/coredb/auth/login", {"username": nombre, "password": clave})
        exigir(estado == 200, f"login del usuario {rol}: {estado}")
        SECRETOS.add(datos["access_token"])
        return nombre, clave, datos["access_token"]

    asesora, clave_asesora, token = usuario("ASESOR")
    _, _, token_analista = usuario("ANALISTA")

    # Versiones desplegadas, para el acta.
    versiones = {}
    for nombre, url in (("bus", f"{BUS}/salud"), ("captacion", f"{CAPTACION}/health"),
                        ("sol", f"{BUS}/bus/sol/health"), ("coredb", f"{COREDB}/coredb/salud")):
        estado, datos, _ = pedir("GET", url)
        versiones[nombre] = {"http": estado, "respuesta": limpiar(datos)}

    def cap(metodo, ruta, cuerpo=None, tok=None, nota=None):
        return llamar(metodo, CAP + ruta, cuerpo, tok or token, nota=nota)

    def captar_hasta_aprobado(dni, nombres="Rosa", paterno="Huamán", materno="Ccori"):
        """Solicitante, caso, consentimientos, OTP, validaciones, central y perfil. Devuelve
        (id_solicitante, id_caso, intercambios)."""
        pasos = []
        celular = "9" + "".join(random.choices("0123456789", k=8))
        e, r, i = cap("POST", "/solicitantes", {"tipo_documento": "DNI", "numero_documento": dni, "nombres": nombres,
                                                "apellido_paterno": paterno, "apellido_materno": materno,
                                                "celular": celular, "correo": f"evid.{uuid.uuid4().hex[:8]}@example.com"})
        pasos.append(i)
        exigir(e == 201, f"registro del solicitante: {e} {r}")
        id_sol = r["data"]["solicitante"]["id_solicitante"]
        e, r, i = cap("POST", "/casos", {"id_solicitante": id_sol, "canal": "AGENCIA", "id_agencia": AGENCIA})
        pasos.append(i)
        exigir(e == 201, f"apertura del caso: {e} {r}")
        caso = r["data"]["id_caso"]
        for metodo, ruta, cuerpo in (
            ("POST", f"/casos/{caso}/consentimientos", {"consentimientos": [
                {"tipo": t, "aceptado": True} for t in ("TRATAMIENTO_DATOS", "CONSULTA_BUROS", "TERMINOS")]}),
        ):
            e, r, i = cap(metodo, ruta, cuerpo)
            pasos.append(i)
        e, r, i = cap("POST", f"/casos/{caso}/otp", {"canal": "SMS"})
        pasos.append(i)
        codigo = r["data"]["codigo_simulado"]
        SECRETOS.add(codigo)
        for metodo, ruta, cuerpo in (
            ("POST", f"/casos/{caso}/otp/verificar", {"codigo": codigo}),
            ("POST", f"/casos/{caso}/validaciones", {"tipos": ["RENIEC", "LISTAS_NEGRAS", "PEP"]}),
            ("POST", f"/casos/{caso}/consultas-riesgo", {"central": "SBS"}),
            ("POST", f"/casos/{caso}/perfil", None),
        ):
            e, r, i = cap(metodo, ruta, cuerpo)
            pasos.append(i)
        return id_sol, caso, pasos

    def buscar_ref(dni):
        return llamar("POST", f"{CAPTACION}/cap/references/search", {"search": dni, "limit": 50}, TOKEN_SOL)

    def clientes_con_documento(dni):
        """Cuántos clientes devuelve CAPTACION para ese documento (lectura, sin efectos)."""
        e, r, i = buscar_ref(dni)
        return (len(r) if e == 200 else None), i

    print("CR-INT-09  CAPTACION ↔ Clientes (COREDB)", file=sys.stderr)
    dni_a = dni_nuevo("1")
    sol_a, caso_a, pasos = captar_hasta_aprobado(dni_a)
    e, r, i = cap("POST", f"/casos/{caso_a}/habilitar")
    pasos.append(i)
    datos = r.get("data", {}) if isinstance(r, dict) else {}
    cod_a = datos.get("cod_cliente")
    reg.caso("PR-CAP-09-01", "CR-INT-09", "Funcional positiva",
             "Un prospecto con todos los requisitos se habilita y COREDB le asigna el identificador maestro",
             "HTTP 200, estado HABILITADO, cliente_nuevo = true y cod_cliente generado por COREDB",
             pasos, e == 200 and datos.get("estado") == "HABILITADO" and datos.get("cliente_nuevo") is True
             and bool(cod_a), f"HTTP {e}, estado {datos.get('estado')}, cliente_nuevo {si_no(datos.get('cliente_nuevo'))}, "
                              f"cod_cliente {cod_a}")
    exigir(cod_a, "sin cliente habilitado no se puede continuar")

    e1, cli, i1 = llamar("GET", f"{COREDB}/coredb/clientes/{cod_a}", token=token)
    e2, caso_leido, i2 = cap("GET", f"/casos/{caso_a}")
    e3, ref, i3 = llamar("GET", f"{CAPTACION}/cap/references/{cod_a}", token=TOKEN_SOL)
    caso_d = caso_leido.get("data", {}) if isinstance(caso_leido, dict) else {}
    ok = (e1 == 200 and cli.get("numero_documento") == dni_a and cli.get("estado_cliente") == "ACTIVO"
          and cli.get("estado_habilitante") == "HABILITADO" and e2 == 200 and caso_d.get("estado") == "HABILITADO"
          and caso_d.get("cod_cliente") == cod_a and e3 == 200
          and ref.get("id_verificacion") == cli.get("id_verificacion_captacion"))
    reg.caso("PR-CAP-09-02", "CR-INT-09", "Persistencia",
             "Releer el cliente en COREDB y el caso: el identificador y la verificación quedaron guardados y coinciden",
             "Cliente ACTIVO/HABILITADO con el mismo documento; caso HABILITADO ligado al mismo cod_cliente; "
             "id_verificacion de la referencia = id_verificacion_captacion de COREDB",
             [i1, i2, i3], ok, f"COREDB {e1} {cli.get('estado_cliente')}/{cli.get('estado_habilitante')}; caso {e2} "
                               f"{caso_d.get('estado')} → {caso_d.get('cod_cliente')}; verificación coincide: "
                               f"{si_no(ref.get('id_verificacion') == cli.get('id_verificacion_captacion'))}")

    e, r, i = cap("POST", f"/casos/{caso_a}/habilitar", nota="Segunda habilitación del mismo caso")
    datos = r.get("data", {}) if isinstance(r, dict) else {}
    n, ib = clientes_con_documento(dni_a)
    reg.caso("PR-CAP-09-03", "CR-INT-09", "Duplicados",
             "Repetir la habilitación del mismo caso no crea otro cliente",
             "HTTP 200 con el mismo cod_cliente y un solo cliente con ese documento",
             [i, ib], e == 200 and datos.get("cod_cliente") == cod_a and n == 1,
             f"HTTP {e}, cod_cliente {datos.get('cod_cliente')}, clientes con el documento: {n}")

    e, r, i = cap("POST", "/solicitantes", {"tipo_documento": "DNI", "numero_documento": dni_a, "nombres": "Rosa",
                                            "apellido_paterno": "Huamán", "apellido_materno": "Ccori",
                                            "celular": "9" + "".join(random.choices("0123456789", k=8)),
                                            "correo": f"evid.{uuid.uuid4().hex[:8]}@example.com"},
                  nota="Mismo documento que PR-CAP-09-01")
    datos = r.get("data", {}) if isinstance(r, dict) else {}
    reg.caso("PR-CAP-09-04", "CR-INT-09", "Duplicados",
             "Registrar otra vez a la misma persona devuelve el solicitante existente",
             "HTTP 200 con duplicado = true y el mismo id_solicitante",
             [i], e == 200 and datos.get("duplicado") is True
             and datos.get("solicitante", {}).get("id_solicitante") == sol_a,
             f"HTTP {e}, duplicado {si_no(datos.get('duplicado'))}")

    # Error de negocio: habilitar sin requisitos.
    dni_b = dni_nuevo("2")
    e, r, i1 = cap("POST", "/solicitantes", {"tipo_documento": "DNI", "numero_documento": dni_b, "nombres": "Luis",
                                             "apellido_paterno": "Quispe", "apellido_materno": "Mamani",
                                             "celular": "9" + "".join(random.choices("0123456789", k=8)),
                                            "correo": f"evid.{uuid.uuid4().hex[:8]}@example.com"})
    id_sol_b = r["data"]["solicitante"]["id_solicitante"]
    e, r, i2 = cap("POST", "/casos", {"id_solicitante": id_sol_b, "canal": "AGENCIA", "id_agencia": AGENCIA})
    caso_b = r["data"]["id_caso"]
    e, r, i3 = cap("POST", f"/casos/{caso_b}/habilitar", nota="Sin consentimientos, OTP ni validaciones")
    n, i4 = clientes_con_documento(dni_b)
    reg.caso("PR-CAP-09-05", "CR-INT-09", "Error de negocio",
             "Habilitar un caso sin requisitos se rechaza y no crea cliente",
             "HTTP 400 ERR-CAP-CASO-NO-LISTO con la lista de faltantes; ningún cliente con ese documento",
             [i1, i2, i3, i4], e == 400 and r.get("error_code") == "ERR-CAP-CASO-NO-LISTO" and n == 0,
             f"HTTP {e} {r.get('error_code') if isinstance(r, dict) else r}; clientes con el documento: {n}")

    # Error de negocio: lista restrictiva.
    dni_c = "99999999"
    e, r, i1 = cap("POST", "/solicitantes", {"tipo_documento": "DNI", "numero_documento": dni_c, "nombres": "Prueba",
                                             "apellido_paterno": "Lista", "apellido_materno": "Restrictiva",
                                             "celular": "9" + "".join(random.choices("0123456789", k=8)),
                                            "correo": f"evid.{uuid.uuid4().hex[:8]}@example.com"})
    id_sol_c = r["data"]["solicitante"]["id_solicitante"]
    e, r, i2 = cap("POST", "/casos", {"id_solicitante": id_sol_c, "canal": "AGENCIA", "id_agencia": AGENCIA})
    intercambios = [i1, i2]
    if e == 201:
        caso_c = r["data"]["id_caso"]
        for metodo, ruta, cuerpo in (
            ("POST", f"/casos/{caso_c}/consentimientos", {"consentimientos": [
                {"tipo": t, "aceptado": True} for t in ("TRATAMIENTO_DATOS", "CONSULTA_BUROS", "TERMINOS")]}),
            ("POST", f"/casos/{caso_c}/validaciones", {"tipos": ["RENIEC", "LISTAS_NEGRAS", "PEP"]}),
        ):
            _, _, i = cap(metodo, ruta, cuerpo)
            intercambios.append(i)
        e_l, leido, i = cap("GET", f"/casos/{caso_c}")
        intercambios.append(i)
        estado_c = leido.get("data", {}).get("estado")
        e_h, r_h, i = cap("POST", f"/casos/{caso_c}/habilitar")
        intercambios.append(i)
    else:
        # El documento ya tiene un caso de una corrida anterior: se usa el que está abierto o cerrado.
        estado_c, e_h, r_h = "RECHAZADO (corrida anterior)", None, {}
    reg.caso("PR-CAP-09-06", "CR-INT-09", "Error de negocio",
             "Un documento en lista restrictiva deja el caso RECHAZADO y no se puede habilitar",
             "Caso RECHAZADO y habilitar responde 4xx sin crear cliente",
             intercambios, estado_c.startswith("RECHAZADO") and (e_h is None or 400 <= e_h < 500),
             f"caso {estado_c}; habilitar → HTTP {e_h} {r_h.get('error_code') if isinstance(r_h, dict) else ''}")

    print("CR-INT-10  Seguridad (parte de Captación)", file=sys.stderr)
    e1, r1, i1 = llamar("GET", f"{CAP}/casos/{caso_a}", nota="Sin Authorization")
    e2, r2, i2 = llamar("GET", f"{CAP}/casos/{caso_a}", token="token-invalido", nota="Token que no es de COREDB")
    reg.caso("PR-CAP-10-01", "CR-INT-10", "Seguridad",
             "Sin credencial o con una credencial inválida no se lee un expediente",
             "HTTP 401 en ambos casos", [i1, i2], e1 == 401 and e2 == 401, f"HTTP {e1} y {e2}")

    e, r, i = cap("POST", "/solicitantes", {"tipo_documento": "DNI", "numero_documento": dni_nuevo("3"),
                                            "nombres": "Ana", "apellido_paterno": "Torres", "apellido_materno": "Paz",
                                            "celular": "9" + "".join(random.choices("0123456789", k=8)),
                                            "correo": f"evid.{uuid.uuid4().hex[:8]}@example.com"},
                  tok=token_analista, nota="Usuario con rol ANALISTA (sin CREAR_CLIENTE)")
    e2, r2, i2 = cap("POST", f"/casos/{caso_b}/habilitar", tok=token_analista, nota="ANALISTA intenta habilitar")
    reg.caso("PR-CAP-10-02", "CR-INT-10", "Seguridad",
             "Un rol sin permiso CREAR_CLIENTE no registra prospectos ni habilita clientes",
             "HTTP 403 en ambos casos", [i, i2], e == 403 and e2 == 403, f"HTTP {e} y {e2}")

    e1, r1, i1 = llamar("GET", f"{CAPTACION}/health", bus=False, nota="Sin X-Bus-Token")
    e2, r2, i2 = llamar("GET", f"{CAPTACION}/health", bus=False, cabeceras={"X-Bus-Token": "x" * 40},
                        nota="X-Bus-Token desconocido")
    reg.caso("PR-CAP-10-03", "CR-INT-10", "Seguridad",
             "El Bus no deja pasar a CAPTACION a un consumidor sin credencial",
             "HTTP 401 en ambos casos", [i1, i2], e1 == 401 and e2 == 401, f"HTTP {e1} y {e2}")

    e, eventos, i = llamar("GET", f"{COREDB}/coredb/auditoria?actor={asesora}&limite=200", token=admin)
    acciones = sorted({ev["accion"] for ev in eventos}) if e == 200 else []
    modulos = sorted({ev["modulo"] for ev in eventos}) if e == 200 else []
    con_correlacion = sum(1 for ev in eventos if ev.get("correlation_id")) if e == 200 else 0
    resumen = {"eventos": len(eventos) if e == 200 else 0, "modulos": modulos, "acciones": acciones,
               "con_correlation_id": con_correlacion}
    i["respuesta"] = resumen
    i["nota"] = "Resumen de la bitácora de COREDB para la asesora de esta corrida (sin datos personales)"
    reg.caso("PR-CAP-10-04", "CR-INT-10", "Trazabilidad",
             "Cada paso del expediente queda en la bitácora de COREDB a nombre de la asesora",
             "HTTP 200 con eventos del módulo CLIENTES a nombre de la asesora",
             [i], e == 200 and "CLIENTES" in modulos and len(eventos) > 0,
             f"HTTP {e}: {resumen['eventos']} eventos, módulos {', '.join(modulos)}")

    print("CR-INT-01  CAPTACION → SOL", file=sys.stderr)
    requeridos = ["id_cliente", "numero_documento", "nombres", "apellido_paterno", "apellido_materno",
                  "estado_cliente", "id_caso", "id_verificacion", "fecha_verificacion", "vigente_hasta",
                  "estado_habilitante", "version_contrato"]
    e, ref, i = llamar("GET", f"{CAPTACION}/cap/references/{cod_a}", token=TOKEN_SOL,
                       nota="Token de servicio de SOL (CAP_SOL_TOKEN)")
    vacios = [k for k in requeridos if not isinstance(ref.get(k), str) or not ref[k].strip()] if e == 200 else requeridos
    hoy_lima = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=5)).date()
    vigente = e == 200 and not vacios and (datetime.date.fromisoformat(ref["fecha_verificacion"]) <= hoy_lima
                                           <= datetime.date.fromisoformat(ref["vigente_hasta"]))
    sin_contacto = e == 200 and "celular" not in ref and "correo" not in ref
    reg.caso("PR-CAP-01-01", "CR-INT-01", "Contrato",
             "La referencia de un cliente habilitado cumple el contrato que valida SOL",
             "HTTP 200; los 12 campos requeridos no vacíos; ACTIVO/HABILITADO; hoy dentro de la vigencia; sin "
             "celular ni correo", [i],
             vigente and sin_contacto and ref.get("estado_cliente") == "ACTIVO"
             and ref.get("estado_habilitante") == "HABILITADO" and ref.get("id_caso") == caso_a,
             f"HTTP {e}; campos vacíos: {', '.join(vacios) or 'ninguno'}; vigencia {ref.get('fecha_verificacion')} → {ref.get('vigente_hasta')}; "
             f"versión {ref.get('version_contrato')}")

    # SOL real: la asesora entra a SOL con su usuario de COREDB y busca al cliente.
    e, r, _ = pedir("POST", f"{SOL}/auth/login", {"username": asesora, "password": clave_asesora})
    exigir(e == 200, f"login de SOL: {e} {r}")
    token_sol_persona = r["token"]
    SECRETOS.add(token_sol_persona)
    e, lista, i = llamar("POST", f"{SOL}/clients/search", {"search": dni_a}, token_sol_persona,
                         nota="SOL consulta a CAPTACION por el Bus (POST /bus/captacion/cap/references/search)")
    ids = [c.get("id_cliente") for c in lista] if e == 200 and isinstance(lista, list) else []
    reg.caso("PR-CAP-01-02", "CR-INT-01", "Funcional positiva (entre servicios)",
             "La asesora busca en SOL por documento y SOL obtiene de CAPTACION al cliente habilitado",
             "HTTP 200 con exactamente el cod_cliente habilitado",
             [i], e == 200 and ids == [cod_a], f"HTTP {e}; clientes: {', '.join(map(str, ids)) or 'ninguno'}")

    e, politica, _ = pedir("GET", f"{SOL}/policy", token=token_sol_persona)
    exigir(e == 200, f"política de SOL: {e}")
    fecha_base = (hoy_lima + datetime.timedelta(days=1)).isoformat()

    def borrador(cod):
        return {"id_cliente": cod, "monto_solicitado": politica["monto_minimo"], "moneda": "PEN",
                "plazo_meses": politica["plazo_minimo_meses"], "destino_credito": "Capital de trabajo (evidencia)",
                "fecha_base": fecha_base, "pago_doble": False,
                "garantias": [{"tipo_garantia": "PRENDARIA", "descripcion": "Prenda de evidencia",
                               "valor_tasacion": "1500.00"}], "fiadores": []}

    def total_solicitudes():
        e, pagina, _ = pedir("GET", f"{SOL}/applications?limit=1", token=token_sol_persona)
        return pagina.get("total") if e == 200 else None

    e, sol_a, i1 = llamar("POST", f"{SOL}/applications", borrador(cod_a), token_sol_persona,
                          nota="SOL vuelve a pedir la referencia a CAPTACION antes de guardar")
    id_solicitud = sol_a.get("id") if isinstance(sol_a, dict) else None
    e2, leida, i2 = llamar("GET", f"{SOL}/applications/{id_solicitud}", token=token_sol_persona)
    e3, en_core, i3 = llamar("GET", f"{COREDB}/coredb/creditos/solicitudes/{id_solicitud}", token=token)
    reg.caso("PR-CAP-01-03", "CR-INT-01", "Funcional positiva + persistencia",
             "SOL registra un borrador para el cliente habilitado y queda guardado en COREDB",
             "HTTP 201 REGISTRADA; al releer en SOL y en COREDB, codCliente = cod_cliente de CAPTACION",
             [i1, i2, i3], e == 201 and e2 == 200 and e3 == 200 and en_core.get("codCliente") == cod_a
             and leida.get("estado") == "REGISTRADA",
             f"HTTP {e} → {id_solicitud}; SOL {e2} {leida.get('estado') if isinstance(leida, dict) else ''}; "
             f"COREDB {e3} codCliente {en_core.get('codCliente') if isinstance(en_core, dict) else ''}")

    e1, a, i1 = llamar("GET", f"{CAPTACION}/cap/references/{cod_a}", token=TOKEN_SOL, nota="Primera lectura")
    e2, b, i2 = llamar("GET", f"{CAPTACION}/cap/references/{cod_a}", token=TOKEN_SOL, nota="Repetición")
    e3, r3, i3 = llamar("POST", f"{CAPTACION}/cap/references/search", {"search": dni_a, "limit": 51}, TOKEN_SOL,
                        nota="Límite mayor que 50")
    reg.caso("PR-CAP-01-04", "CR-INT-01", "Duplicados / repetición",
             "Consultar dos veces la referencia devuelve lo mismo y no cambia nada; el límite de búsqueda se respeta",
             "Dos HTTP 200 idénticos; límite 51 → HTTP 400 ERR-VALIDACION-ESQUEMA (convención ITIL-02 del proyecto)",
             [i1, i2, i3], e1 == 200 and e2 == 200 and a == b and e3 == 400
             and isinstance(r3, dict) and r3.get("error_code") == "ERR-VALIDACION-ESQUEMA",
             f"HTTP {e1}/{e2} idénticas: {si_no(a == b)}; límite 51 → {e3}")

    # Error de negocio: la habilitación se revoca entre el borrador y el envío.
    dni_d = dni_nuevo("4")
    _, caso_d, pasos = captar_hasta_aprobado(dni_d, "Carmen", "Apaza", "Ticona")
    e, r, i = cap("POST", f"/casos/{caso_d}/habilitar")
    pasos.append(i)
    cod_d = r["data"]["cod_cliente"]
    e, sol_d, i = llamar("POST", f"{SOL}/applications", borrador(cod_d), token_sol_persona)
    pasos.append(i)
    id_sol_d = sol_d["id"]
    e, r, i = cap("POST", f"/casos/{caso_d}/estado", {"accion": "REVOCAR", "motivo": "Prueba de revocación CR-INT-01"},
                  nota="El asesor revoca la habilitación en CAPTACION")
    pasos.append(i)
    e_ref, ref_d, i = llamar("GET", f"{CAPTACION}/cap/references/{cod_d}", token=TOKEN_SOL)
    pasos.append(i)
    antes = total_solicitudes()
    e_new, r_new, i = llamar("POST", f"{SOL}/applications", borrador(cod_d), token_sol_persona,
                             nota="Nuevo borrador con el cliente revocado")
    pasos.append(i)
    e_send, r_send, i = llamar("POST", f"{SOL}/applications/{id_sol_d}/send", {"revision": 1}, token_sol_persona,
                               cabeceras={"X-Idempotency-Key": str(uuid.uuid4())},
                               nota="Envío a Evaluación del borrador guardado antes de la revocación")
    pasos.append(i)
    e_l, d_leido, i = llamar("GET", f"{SOL}/applications/{id_sol_d}", token=token_sol_persona)
    pasos.append(i)
    despues = total_solicitudes()
    estado_ref = ref_d.get("estado_habilitante") if isinstance(ref_d, dict) else None
    reg.caso("PR-CAP-01-05", "CR-INT-01", "Error de negocio (entre servicios)",
             "Un cliente revocado en CAPTACION deja de servir en SOL: no se crea un borrador ni se envía el guardado",
             "Referencia no HABILITADA (o 404); nuevo borrador → 422; envío → 422; la solicitud sigue REGISTRADA y "
             "el total de solicitudes no cambia",
             pasos, estado_ref != "HABILITADO" and e_new == 422 and e_send == 422
             and d_leido.get("estado") == "REGISTRADA" and antes == despues,
             f"referencia {e_ref} {estado_ref}; nuevo borrador {e_new}; envío {e_send}; estado "
             f"{d_leido.get('estado') if isinstance(d_leido, dict) else ''}; total {antes} → {despues}")

    e1, r1, i1 = llamar("GET", f"{CAPTACION}/cap/references/CLI999999999", token=TOKEN_SOL)
    e2, r2, i2 = llamar("POST", f"{SOL}/applications", borrador("CLI999999999"), token_sol_persona)
    reg.caso("PR-CAP-01-06", "CR-INT-01", "Error de negocio",
             "Un cliente que no existe no tiene referencia y SOL no lo acepta",
             "CAPTACION 404; SOL 422", [i1, i2], e1 == 404 and e2 == 422, f"CAPTACION {e1}; SOL {e2}")

    e1, r1, i1 = llamar("GET", f"{CAPTACION}/cap/references/{cod_a}", nota="Sin Authorization")
    e2, r2, i2 = llamar("GET", f"{CAPTACION}/cap/references/{cod_a}", token=token, nota="Token de una persona (asesora)")
    e3, r3, i3 = llamar("POST", f"{SOL}/clients/search", {"search": dni_a}, nota="SOL sin sesión")
    reg.caso("PR-CAP-01-07", "CR-INT-01", "Seguridad",
             "Solo el token de servicio de SOL lee las referencias; una persona o un anónimo no",
             "HTTP 401 en los tres casos", [i1, i2, i3], e1 == 401 and e2 == 401 and e3 == 401,
             f"HTTP {e1}, {e2} y {e3}")

    # Contrato: una persona sin segundo apellido (COREDB lo admite vacío).
    dni_e = dni_nuevo("5")
    _, caso_e, pasos = captar_hasta_aprobado(dni_e, "Jorge", "Mendoza", None)
    e, r, i = cap("POST", f"/casos/{caso_e}/habilitar")
    pasos.append(i)
    cod_e = r.get("data", {}).get("cod_cliente") if isinstance(r, dict) else None
    e_ref, ref_e, i = llamar("GET", f"{CAPTACION}/cap/references/{cod_e}", token=TOKEN_SOL)
    pasos.append(i)
    e_new, r_new, i = llamar("POST", f"{SOL}/applications", borrador(cod_e), token_sol_persona,
                             nota="Borrador para un cliente sin apellido materno")
    pasos.append(i)
    reg.caso("PR-CAP-01-08", "CR-INT-01", "Contrato (caso límite)",
             "Un cliente sin segundo apellido se habilita y SOL lo acepta",
             "Referencia HTTP 200 con apellido_materno vacío; SOL crea el borrador (HTTP 201)",
             pasos, e_ref == 200 and ref_e.get("apellido_materno") == "" and e_new == 201,
             f"referencia {e_ref}, apellido_materno {ref_e.get('apellido_materno')!r}; borrador SOL {e_new}")

    e, metricas, i = llamar("GET", f"{BUS}/metricas")
    reenvios = metricas.get("reenvios", {}) if e == 200 and isinstance(metricas, dict) else {}
    sol_cap = reenvios.get("SOL", {}).get("CAPTACION", 0)
    cap_core = reenvios.get("CAPTACION", {}).get("COREDB", 0)
    i["nota"] = "Contadores del Bus (consumidor → módulo) desde que arrancó"
    reg.caso("PR-CAP-01-09", "CR-INT-01", "Trazabilidad",
             "Las llamadas de SOL a CAPTACION y de CAPTACION a COREDB pasaron por el Bus y quedaron contadas",
             "HTTP 200 con reenvíos SOL → CAPTACION y CAPTACION → COREDB mayores que cero",
             [i], e == 200 and sol_cap > 0 and cap_core > 0,
             f"HTTP {e}; SOL → CAPTACION {sol_cap}; CAPTACION → COREDB {cap_core}")

    pasan = sum(1 for c in reg.casos if c["resultado"] == "PASA")
    salida = {
        "titulo": "Evidencias de integración de Captación de Clientes (CR-INT-09, CR-INT-01, CR-INT-10)",
        "inicio": inicio, "fin": ahora(), "bus": "Bus de Servicios (todas las llamadas pasan por /bus/<módulo>)",
        "versiones": versiones,
        "datos": "Ficticios, creados en esta corrida; documentos y contactos enmascarados; sin tokens ni claves",
        "resumen": {"casos": len(reg.casos), "pasan": pasan, "fallan": len(reg.casos) - pasan},
        "casos": reg.casos,
    }
    print(json.dumps(salida, ensure_ascii=False, indent=2))
    print(f"\n{pasan} de {len(reg.casos)} casos pasan", file=sys.stderr)
    return 0 if pasan == len(reg.casos) else 1


if __name__ == "__main__":
    sys.exit(main())
