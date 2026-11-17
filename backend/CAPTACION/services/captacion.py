"""El expediente de captación, de la solicitud del prospecto a su habilitación.

CAPTACION no tiene base propia: el expediente vive en la base integrada
(clientes.*_captacion, desde bd-v1.7-mysql) y se trabaja por /coredb/captacion. La base
guarda cada paso, aplica las reglas (consentimientos exigidos, OTP con vencimiento e
intentos, un caso abierto por solicitante) y recalcula el estado:
INICIADO → EN_VALIDACION → APROBADO → HABILITADO, con OBSERVADO mientras algo quede por
resolver y RECHAZADO o REVOCADO como finales. Aquí queda lo que es del módulo:

  1. los proveedores (RENIEC, listas, PEP, biometría, centrales), hoy simulados;
  2. el puntaje del perfil de riesgo (proveedores.puntaje);
  3. el código OTP: se genera aquí, se envía (o se devuelve en laboratorio) y COREDB solo
     recibe su HMAC, calculado con CAP_OTP_CLAVE y el id del OTP;
  4. la habilitación: con el usuario de servicio (módulo CLIENTES, punto R-01) verifica el
     documento, registra al cliente HABILITADO o reutiliza el activo, lo liga al caso, y
     con el token del asesor habilita;
  5. la referencia CR-INT-01 que consulta Solicitud de Crédito.

Lo que hace el asesor va a COREDB con su token: queda a su nombre en la bitácora.
"""

import hashlib
import hmac
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from CAPTACION import proveedores
from CAPTACION.config import settings
from CAPTACION.core_client import CoreDb
from CAPTACION.errores import CaptacionError

CERRADOS = ("HABILITADO", "RECHAZADO", "REVOCADO")
ABIERTOS = ("INICIADO", "EN_VALIDACION", "OBSERVADO", "APROBADO")
VERSION_CONTRATO_SOL = "CR-INT-01-PROPUESTA-v2"
LIMA = timezone(timedelta(hours=-5))  # Perú no tiene horario de verano
RUTA = "/coredb/captacion"


def hoy_lima() -> date:
    return datetime.now(LIMA).date()


# ── Formas de las respuestas (las mismas que antes de pasar a COREDB) ───────
def _solicitante(s: dict) -> dict:
    return {
        "id_solicitante": s["id_solicitante"], "tipo_documento": s["tipo_documento"],
        "numero_documento": s["numero_documento"], "nombres": s["nombres"],
        "apellido_paterno": s["apellido_paterno"], "apellido_materno": s["apellido_materno"],
        "celular": s["celular"], "correo": s["correo"], "cod_cliente": s["cod_cliente"],
        "creado_en": s["fecha_registro"],
    }


def _caso(c: dict) -> dict:
    return {
        "id_caso": c["id_caso"], "id_solicitante": c["id_solicitante"], "canal": c["canal"],
        "id_agencia": c["id_agencia"], "producto_interes": c["producto_interes"], "estado": c["estado"],
        "observacion": c["observacion"], "motivo_cierre": c["motivo_cierre"], "cod_cliente": c["cod_cliente"],
        "cliente_nuevo": c["cliente_nuevo"], "id_verificacion_captacion": c["id_verificacion_captacion"],
        "fecha_verificacion": c["fecha_verificacion"], "vigente_hasta": c["vigente_hasta"],
        "creado_por": c["creado_por"], "creado_en": c["fecha_apertura"], "cerrado_en": c["fecha_cierre"],
    }


def _ultimos(items: list[dict]) -> dict:
    """El registro más reciente de cada tipo: una validación nueva reemplaza a la anterior."""
    return {i["tipo"]: i for i in items}


# ── Solicitante ─────────────────────────────────────────────────────────────
def obtener_solicitante(core: CoreDb, token: str, id_solicitante: str, cid: str | None) -> dict:
    _uuid_o_404(id_solicitante, "ERR-CAP-SOLICITANTE-NO-ENCONTRADO", "El solicitante no existe.")
    return _solicitante(core.persona("GET", f"{RUTA}/solicitantes/{id_solicitante}", token, cid))


def registrar_solicitante(core: CoreDb, token: str, datos: dict, cid: str | None) -> tuple[dict, bool]:
    """Si el documento ya se registró devuelve el mismo solicitante (duplicado=True)."""
    r = core.persona("POST", f"{RUTA}/solicitantes", token, cid, json=datos)
    return _solicitante(r["solicitante"]), r["duplicado"]


def buscar_solicitantes(core: CoreDb, token: str, documento: str | None, limite: int, cid: str | None) -> list[dict]:
    params = {"limite": limite, **({"documento": documento} if documento else {})}
    return [_solicitante(s) for s in core.persona("GET", f"{RUTA}/solicitantes", token, cid, params=params)]


# ── Caso ────────────────────────────────────────────────────────────────────
def _uuid_o_404(valor: str, codigo: str, mensaje: str) -> None:
    try:
        uuid.UUID(valor)
    except ValueError:
        raise CaptacionError(codigo, mensaje, 404) from None


def _expediente(core: CoreDb, token: str, id_caso: str, cid: str | None) -> dict:
    _uuid_o_404(id_caso, "ERR-CAP-CASO-NO-ENCONTRADO", "El caso no existe.")
    return core.persona("GET", f"{RUTA}/casos/{id_caso}", token, cid)


def abrir_caso(core: CoreDb, token: str, datos: dict, cid: str | None) -> dict:
    try:
        return _caso(core.persona("POST", f"{RUTA}/casos", token, cid, json=datos))
    except CaptacionError as exc:
        if exc.code != "ERR-CAP-CASO-ABIERTO":
            raise
        abiertos = [c for c in core.persona("GET", f"{RUTA}/casos", token, cid,
                                            params={"id_solicitante": datos["id_solicitante"]})
                    if c["estado"] in ABIERTOS]
        if abiertos:
            exc.details = {"id_caso": abiertos[0]["id_caso"], "estado": abiertos[0]["estado"]}
        raise


def listar_casos(core: CoreDb, token: str, estado: str | None, limite: int, offset: int,
                 cid: str | None) -> list[tuple[dict, dict]]:
    params = {"limite": limite, "offset": offset, **({"estado": estado} if estado else {})}
    return [(_caso(c), _solicitante(c["solicitante"]))
            for c in core.persona("GET", f"{RUTA}/casos", token, cid, params=params)]


def detalle(core: CoreDb, token: str, id_caso: str, cid: str | None, expediente: dict | None = None) -> dict:
    e = expediente or _expediente(core, token, id_caso, cid)
    return {
        "caso": _caso(e), "solicitante": _solicitante(e["solicitante"]),
        "consentimientos": e["consentimientos"], "validaciones": e["validaciones"],
        "consultas": e["consultas"], "perfil": e["perfil"],
        "faltantes": e["faltantes"], "listo_para_habilitar": e["listo_para_habilitar"],
    }


# ── Consentimientos ─────────────────────────────────────────────────────────
def registrar_consentimientos(core: CoreDb, token: str, id_caso: str, items: list[dict], cid: str | None) -> list[dict]:
    _uuid_o_404(id_caso, "ERR-CAP-CASO-NO-ENCONTRADO", "El caso no existe.")
    cuerpo = {"consentimientos": items}
    if any(i["tipo"] == "TERMINOS" for i in items):
        cuerpo["version_terminos"] = settings.cap_version_terminos
    e = core.persona("POST", f"{RUTA}/casos/{id_caso}/consentimientos", token, cid, json=cuerpo)
    return e["consentimientos"][-len(items):]


# ── OTP ─────────────────────────────────────────────────────────────────────
def _hmac(id_otp: str, codigo: str) -> str:
    clave = (settings.cap_otp_clave or "").encode()
    if not clave:
        raise CaptacionError("ERR-CAP-CONFIGURACION", "Falta CAP_OTP_CLAVE.", 503)
    return hmac.new(clave, f"{id_otp}:{codigo}".encode(), hashlib.sha256).hexdigest()


def enmascarar(destino: str) -> str:
    if "@" in destino:
        usuario, dominio = destino.split("@", 1)
        return usuario[:2] + "***@" + dominio
    return "*" * max(len(destino) - 3, 0) + destino[-3:]


def enviar_otp(core: CoreDb, token: str, id_caso: str, canal: str, cid: str | None) -> dict:
    e = _expediente(core, token, id_caso, cid)
    destino = e["solicitante"]["celular"] if canal == "SMS" else e["solicitante"]["correo"]
    id_otp, codigo = str(uuid.uuid4()), f"{secrets.randbelow(1_000_000):06d}"
    otp = core.persona("POST", f"{RUTA}/casos/{id_caso}/otps", token, cid,
                       json={"id_otp": id_otp, "canal": canal, "codigo_hmac": _hmac(id_otp, codigo)})
    return {
        "canal": canal, "destino_enmascarado": enmascarar(destino), "expira_en": otp["fecha_expiracion"],
        # Sin proveedor de SMS ni de correo, en laboratorio el código vuelve en la respuesta.
        "codigo_simulado": codigo if settings.cap_otp_simulado else None,
    }


def verificar_otp(core: CoreDb, token: str, id_caso: str, canal: str, codigo: str, cid: str | None) -> dict:
    e = _expediente(core, token, id_caso, cid)
    pendientes = [o for o in e["otps"] if o["canal"] == canal and o["estado"] == "PENDIENTE"]
    if not pendientes:
        raise CaptacionError("ERR-CAP-OTP-NO-ENCONTRADO", "No hay un código pendiente: envíe uno nuevo.", 404)
    id_otp = pendientes[-1]["id_otp"]
    r = core.persona("POST", f"{RUTA}/casos/{id_caso}/otps/{id_otp}/verificacion", token, cid,
                     json={"codigo_hmac": _hmac(id_otp, codigo)})
    return {"verificado": r["estado_codigo"] == "USADO", "estado_codigo": r["estado_codigo"],
            "intentos_restantes": r["intentos_restantes"]}


# ── Validaciones de identidad ───────────────────────────────────────────────
def _exigir_consentimiento(e: dict, tipo: str) -> None:
    ultimo = _ultimos(e["consentimientos"]).get(tipo)
    if not (ultimo and ultimo["aceptado"]):
        raise CaptacionError("ERR-CAP-CONSENTIMIENTO-REQUERIDO",
                             f"El solicitante no ha aceptado el consentimiento {tipo}.", 422, {"tipo": tipo})


def _abierto(e: dict) -> None:
    if e["estado"] in CERRADOS:
        raise CaptacionError("ERR-CAP-CASO-CERRADO", f"El caso está {e['estado']} y ya no admite cambios.",
                             409, {"estado": e["estado"]})


def ejecutar_validaciones(core: CoreDb, token: str, id_caso: str, tipos: list[str], cid: str | None) -> list[dict]:
    """Consulta a cada proveedor y guarda su resultado. Si uno rechaza, el caso se cierra
    y los siguientes ya no se consultan."""
    e = _expediente(core, token, id_caso, cid)
    _abierto(e)
    _exigir_consentimiento(e, "TRATAMIENTO_DATOS")
    if "BIOMETRIA" in tipos:
        _exigir_consentimiento(e, "BIOMETRIA")
    sol = e["solicitante"]
    antes = len(e["validaciones"])
    for tipo in dict.fromkeys(tipos):
        resultado, texto = proveedores.validar(tipo, sol["tipo_documento"], sol["numero_documento"])
        e = core.persona("POST", f"{RUTA}/casos/{id_caso}/validaciones", token, cid, json={
            "tipo": tipo, "resultado": resultado, "proveedor": proveedores.NOMBRE, "detalle": texto})
        if e["estado"] in CERRADOS:
            break
    return e["validaciones"][antes:]


def validacion_manual(core: CoreDb, token: str, id_caso: str, datos: dict, cid: str | None) -> dict:
    """El veredicto de una revisión hecha por una persona (en agencia, o la debida
    diligencia de un PEP). Reemplaza al resultado anterior del mismo tipo."""
    _uuid_o_404(id_caso, "ERR-CAP-CASO-NO-ENCONTRADO", "El caso no existe.")
    e = core.persona("POST", f"{RUTA}/casos/{id_caso}/validaciones", token, cid, json={
        "tipo": datos["tipo"], "resultado": datos["resultado"], "proveedor": "MANUAL", "detalle": datos["detalle"]})
    return e["validaciones"][-1]


# ── Centrales de riesgo y perfil ────────────────────────────────────────────
def consultar_central(core: CoreDb, token: str, id_caso: str, central: str, reporte: dict | None,
                      cid: str | None) -> dict:
    e = _expediente(core, token, id_caso, cid)
    _abierto(e)
    _exigir_consentimiento(e, "CONSULTA_BUROS")
    datos = reporte or proveedores.consultar_central(e["solicitante"]["numero_documento"])
    e = core.persona("POST", f"{RUTA}/casos/{id_caso}/consultas-riesgo", token, cid, json={
        "central": central, "calificacion": datos["calificacion"], "deuda_total": str(datos["deuda_total"]),
        "entidades": datos["entidades"], "dias_mora": datos["dias_mora"],
        "fuente": "MANUAL" if reporte else proveedores.NOMBRE})
    return e["consultas"][-1]


def calcular_perfil(core: CoreDb, token: str, id_caso: str, cid: str | None) -> dict:
    e = _expediente(core, token, id_caso, cid)
    _abierto(e)
    if not e["consultas"]:
        raise CaptacionError("ERR-CAP-SIN-CONSULTA", "Consulte al menos una central de riesgo.", 422)
    observadas = sorted(t for t, v in _ultimos(e["validaciones"]).items() if v["resultado"] == "OBSERVADO")
    reportes = [{"calificacion": c["calificacion"], "deuda_total": Decimal(c["deuda_total"]),
                 "entidades": c["entidades"], "dias_mora": c["dias_mora"]} for c in e["consultas"]]
    valor, calificacion, nota = proveedores.puntaje(reportes, observadas)
    e = core.persona("POST", f"{RUTA}/casos/{id_caso}/perfil", token, cid,
                     json={"puntaje": valor, "calificacion": calificacion, "observacion": nota})
    return e["perfil"]


# ── Decisiones del asesor ───────────────────────────────────────────────────
def cambiar_estado(core: CoreDb, token: str, id_caso: str, accion: str, motivo: str, cid: str | None) -> dict:
    _uuid_o_404(id_caso, "ERR-CAP-CASO-NO-ENCONTRADO", "El caso no existe.")
    return _caso(core.persona("POST", f"{RUTA}/casos/{id_caso}/estado", token, cid,
                              json={"accion": accion, "motivo": motivo}))


# ── Habilitación: el cliente en COREDB ──────────────────────────────────────
def habilitar(core: CoreDb, token: str, id_caso: str, cid: str | None) -> dict:
    """Registra al cliente en COREDB como HABILITADO, o reutiliza el cliente activo que ya
    tenga ese documento, lo liga al caso y lo habilita para Solicitud de Crédito.

    Se puede repetir: un caso HABILITADO se devuelve igual, y un caso que ya tiene su
    cliente ligado no vuelve a registrarlo. Si el alta salió bien y el vínculo falló, el
    reintento encuentra al cliente activo y lo reutiliza."""
    e = _expediente(core, token, id_caso, cid)
    if e["estado"] == "HABILITADO":
        return _caso(e)
    if not e["listo_para_habilitar"]:
        raise CaptacionError("ERR-CAP-CASO-NO-LISTO", "El caso no cumple los requisitos para habilitarse.",
                             422, {"faltantes": e["faltantes"] or [f"Caso en estado {e['estado']}"]})
    sol = e["solicitante"]
    if e["cod_cliente"] is None:
        verificacion = core.verificar_documento(sol["tipo_documento"], sol["numero_documento"], cid)
        if verificacion["resultado"] == "APROBADO":
            cod_cliente, nuevo = verificacion["cliente"]["cod_cliente"], False
        elif verificacion.get("motivo") == "NO_ES_CLIENTE":
            terminos = _ultimos(e["consentimientos"])["TERMINOS"]
            registro = core.registrar_cliente({
                "tipo_documento": sol["tipo_documento"], "numero_documento": sol["numero_documento"],
                "nombres": sol["nombres"], "apellido_paterno": sol["apellido_paterno"],
                "apellido_materno": sol["apellido_materno"], "correo": sol["correo"], "celular": sol["celular"],
                "version_contrato": terminos["version"] or settings.cap_version_terminos,
                "estado_habilitante": "HABILITADO",
            }, cid)
            cod_cliente, nuevo = registro["cod_cliente"], True
        else:
            # Es cliente, pero no está ACTIVO en el CORE (BLOQUEADO, SUSPENDIDO, OBSERVADO...).
            estado = (verificacion.get("cliente") or {}).get("estado_cliente", "NO ACTIVO")
            core.persona("POST", f"{RUTA}/casos/{id_caso}/estado", token, cid, json={
                "accion": "OBSERVAR", "motivo": f"El cliente existe en el CORE en estado {estado}"})
            raise CaptacionError("ERR-CAP-CLIENTE-NO-ACTIVO",
                                 f"El documento ya es de un cliente en estado {estado}: debe regularizarse "
                                 "en el CORE antes de habilitarlo.", 422, {"estado_cliente": estado})
        core.servicio("POST", f"{RUTA}/casos/{id_caso}/cliente", cid,
                      json={"cod_cliente": cod_cliente, "cliente_nuevo": nuevo})
    # La base deja también en el cliente las verificaciones de celular y correo.
    return _caso(core.persona("POST", f"{RUTA}/casos/{id_caso}/habilitacion", token, cid,
                              json={"vigencia_dias": settings.cap_vigencia_dias}))


# ── Referencias para Solicitud de Crédito (CR-INT-01) ───────────────────────
def _referencia(caso: dict, sol: dict, cliente: dict | None = None) -> dict:
    """La referencia tal como la espera SOL (backend/SOL/integrations.py, CLIENT_FIELDS).

    Con `cliente` (la vista de COREDB) la identidad y el estado son los vigentes en el CORE;
    sin él, los que trae el caso."""
    fuente = cliente or {}
    return {
        "id_cliente": caso["cod_cliente"],
        "cod_tipo_documento": fuente.get("tipo_documento", sol["tipo_documento"]),
        "numero_documento": fuente.get("numero_documento", sol["numero_documento"]),
        "nombres": fuente.get("nombres", sol["nombres"]),
        "apellido_paterno": fuente.get("apellido_paterno", sol["apellido_paterno"]),
        "apellido_materno": (fuente.get("apellido_materno") if cliente else sol["apellido_materno"]) or "",
        "estado_cliente": fuente.get("estado_cliente", caso["estado_cliente"] or ""),
        "id_caso": caso["id_caso"],
        "id_verificacion": caso["id_verificacion_captacion"] or "",
        "fecha_verificacion": caso["fecha_verificacion"] or "",
        "vigente_hasta": caso["vigente_hasta"] or "",
        "estado_habilitante": "HABILITADO" if caso["estado"] == "HABILITADO" else caso["estado"],
        "version_contrato": VERSION_CONTRATO_SOL,
        # RENIEC, listas, PEP, centrales y SMS son simulados: la referencia lo dice.
        "simulado": True,
    }


def _ultimo_caso_de(core: CoreDb, cod_cliente: str, cid: str | None) -> dict | None:
    casos = [c for c in core.servicio("GET", f"{RUTA}/casos", cid, params={"cod_cliente": cod_cliente})
             if c["estado"] in ("HABILITADO", "REVOCADO")]
    casos.sort(key=lambda c: (c["fecha_verificacion"] or "", c["fecha_cierre"] or ""), reverse=True)
    return casos[0] if casos else None


def referencia(core: CoreDb, cod_cliente: str, cid: str | None) -> dict | None:
    """Una referencia, con la identidad y el estado que tiene hoy el cliente en COREDB."""
    caso = _ultimo_caso_de(core, cod_cliente, cid)
    if caso is None:
        return None
    try:
        cliente = core.ver_cliente(cod_cliente, cid)
    except CaptacionError as exc:
        if exc.status_code == 404:
            return None
        raise
    return _referencia(caso, caso["solicitante"], cliente)


def referencia_de_caso(core: CoreDb, token: str, id_caso: str, cid: str | None) -> dict:
    e = _expediente(core, token, id_caso, cid)
    if e["cod_cliente"] is None or e["estado"] not in ("HABILITADO", "REVOCADO"):
        raise CaptacionError("ERR-CAP-SIN-REFERENCIA", "El caso todavía no está habilitado.", 409)
    return _referencia(e, e["solicitante"], core.ver_cliente(e["cod_cliente"], cid))


def buscar_referencias(core: CoreDb, texto: str, limite: int, cid: str | None) -> list[dict]:
    """Búsqueda acotada para el buscador de SOL. No consulta al cliente por cada fila: SOL
    vuelve a pedir la referencia individual antes de guardar o enviar."""
    params = {"con_cliente": True, "limite": 200, **({"texto": texto.strip()} if texto.strip() else {})}
    resultado = []
    for sol in core.servicio("GET", f"{RUTA}/solicitantes", cid, params=params):
        caso = _ultimo_caso_de(core, sol["cod_cliente"], cid)
        if caso is not None:
            resultado.append(_referencia(caso, sol))
        if len(resultado) >= limite:
            break
    return resultado
