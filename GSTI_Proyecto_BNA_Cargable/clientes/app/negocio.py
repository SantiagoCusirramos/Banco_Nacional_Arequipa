"""Reglas de negocio del módulo de Clientes: las tres operaciones.

Principios:
  * Clientes no tiene BD: todo dato bancario va y viene por el Bus hacia el Core.
  * Todo intento (aceptado o rechazado) deja una fila de auditoría en el Core cuando éste está disponible.
  * Nunca se devuelven datos personales si la identidad no quedó verificada.
  * Nunca se registran plantillas biométricas en logs.
"""
import logging

from shared.comun import ApiError, enmascarar_doc
from shared.esquemas import DatosCliente, MODULOS_ORIGEN, ValidarBiometriaIn, ValidarDocumentoIn

from . import conexiones as con

log = logging.getLogger("clientes.negocio")

MENSAJES_IDENTIDAD = {
    "DNI_NO_ENCONTRADO": "El DNI no existe en RENIEC",
    "DATOS_NO_COINCIDEN": "Los datos no coinciden con los registrados en RENIEC",
}


async def _auditar_registro(modulo: str, tipo: str, numero: str, resultado: str) -> None:
    """Mejor esfuerzo: si el Core no responde, el rechazo original sigue siendo el error que se informa."""
    try:
        await con.core("POST", "auditar-registro", {"modulo_origen": modulo, "tipo_documento": tipo,
                                                    "numero_documento": numero[:40], "resultado": resultado})
    except Exception as e:  # noqa: BLE001
        log.warning("No se pudo auditar el registro en el Core (%s)", type(e).__name__)


async def auditar_payload_invalido(cuerpo: object) -> None:
    """Petición de registro que no superó la validación: se registra lo que se pueda identificar."""
    if not isinstance(cuerpo, dict):
        return
    modulo = cuerpo.get("modulo_origen")
    tipo = cuerpo.get("tipo_documento")
    numero = cuerpo.get("numero_documento")
    await _auditar_registro(
        modulo if modulo in MODULOS_ORIGEN else "DESCONOCIDO",
        tipo if isinstance(tipo, str) and len(tipo) <= 20 else "DESCONOCIDO",
        numero if isinstance(numero, str) else "DESCONOCIDO",
        "RECHAZADO_DATOS_INVALIDOS",
    )


# ------------------------------------------------------------------ 1. registrar
async def registrar(d: DatosCliente) -> dict:
    verificado = False
    if d.tipo_documento == "DNI":
        try:
            r = await con.reniec_post("/interno/validar-dni", {
                "numero_documento": d.numero_documento, "fecha_nacimiento": d.fecha_nacimiento.isoformat(),
                "nombres": d.nombres, "apellidos": d.apellidos})
        except con.ReniecNoDisponible:
            await _auditar_registro(d.modulo_origen, d.tipo_documento, d.numero_documento, "RECHAZADO_RENIEC_NO_DISPONIBLE")
            raise ApiError(503, "RENIEC_NO_DISPONIBLE", "RENIEC no está disponible; no se puede verificar el DNI")
        if r["estado"] != "DNI_VALIDO":
            await _auditar_registro(d.modulo_origen, d.tipo_documento, d.numero_documento, f"RECHAZADO_{r['estado']}")
            raise ApiError(422, r["estado"], MENSAJES_IDENTIDAD.get(r["estado"], "Identidad no verificada"))
        verificado = True

    cuerpo = d.model_dump(mode="json")
    cuerpo["verificado_reniec"] = verificado
    r = await con.core("POST", "registrar-cliente", cuerpo)  # duplicado -> ApiError 409 propagado desde el Core
    salida = {"correcto": True, "cliente_id": r["cliente_id"], "verificacion_reniec": verificado}
    if not verificado:
        salida["aviso"] = f"Registro sin verificación en RENIEC ({d.tipo_documento}): solo se aplicaron validaciones locales"
    return salida


# ------------------------------------------------------------------ 2. validar por documento
async def validar_documento(d: ValidarDocumentoIn) -> dict:
    base = {"modulo_origen": d.modulo_origen, "tipo_documento": d.tipo_documento,
            "numero_documento": d.numero_documento, "fecha_nacimiento": d.fecha_nacimiento.isoformat()}

    if d.tipo_documento == "DNI":
        try:
            r = await con.reniec_post("/interno/validar-dni", {"numero_documento": d.numero_documento,
                                                               "fecha_nacimiento": d.fecha_nacimiento.isoformat()})
        except con.ReniecNoDisponible:
            try:  # queda constancia de la solicitud aunque no se pueda dar respuesta
                await con.core("POST", "validar-documento", {**base, "identidad": "RENIEC_NO_DISPONIBLE", "consultar": False})
            except ApiError:
                pass
            raise ApiError(503, "RENIEC_NO_DISPONIBLE", "RENIEC no está disponible; no se puede verificar la identidad")
        identidad = r["estado"]
    else:
        identidad = f"{d.tipo_documento}_NO_CONSULTADO"  # PASAPORTE / PTP: no hay validación externa

    c = await con.core("POST", "validar-documento", {**base, "identidad": identidad, "consultar": True})

    salida = {"correcto": True, "identidad": identidad, "registrado_bna": c["registrado"]}
    cliente = c.get("cliente")  # el Core solo lo entrega si la fecha coincide con la registrada
    if identidad == "DNI_VALIDO" and cliente:
        salida["cliente"] = cliente
    elif d.tipo_documento != "DNI" and cliente:
        # La fecha coincide con el banco, pero el documento NO fue verificado oficialmente: solo el identificador.
        salida["cliente"] = {"id": cliente["id"]}
        salida["aviso"] = "Documento no verificado por RENIEC; solo se confirma el registro en el banco"
    elif c["registrado"] and c["fecha_coincide"] is False:
        salida["aviso"] = "La fecha de nacimiento no coincide con la registrada en el banco"
    return salida


# ------------------------------------------------------------------ 3. validar biometría
async def validar_biometria(d: ValidarBiometriaIn) -> dict:
    cuerpo_reniec = {"numero_documento": d.numero_documento, "tipo_biometria": d.tipo_biometria,
                     "formato": d.formato, "codificacion": d.codificacion, "template": d.template}
    base_core = {"modulo_origen": d.modulo_origen, "numero_documento": d.numero_documento, "tipo_validacion": d.tipo_biometria}

    try:
        r = await con.reniec_post("/interno/comparar-biometria", cuerpo_reniec)
    except con.ReniecNoDisponible:
        try:
            await con.core("POST", "validar-biometria", {**base_core, "resultado_biometrico": "RENIEC_NO_DISPONIBLE", "consultar": False})
        except ApiError:
            pass
        raise ApiError(503, "RENIEC_NO_DISPONIBLE", "RENIEC no está disponible; no se puede validar la biometría")
    except ApiError as e:  # error técnico (plantilla inválida, versión incompatible...): igual se audita
        try:
            await con.core("POST", "validar-biometria", {**base_core, "resultado_biometrico": f"ERROR_{e.codigo}"[:40], "consultar": False})
        except ApiError:
            pass
        raise

    estado = r["estado"]
    if estado != "COINCIDE":  # resultado negativo NORMAL: sin datos personales
        await con.core("POST", "validar-biometria", {**base_core, "resultado_biometrico": estado, "consultar": False})
        return {"correcto": True, "coincide": False, "motivo": estado}

    c = await con.core("POST", "validar-biometria", {**base_core, "resultado_biometrico": "COINCIDE", "consultar": True})
    salida = {"correcto": True, "coincide": True, "registrado_bna": c["registrado"]}
    if c.get("cliente"):
        salida["cliente"] = c["cliente"]
    log.info("validacion biometrica %s dni=%s coincide=True", d.tipo_biometria, enmascarar_doc(d.numero_documento))
    return salida
