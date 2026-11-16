"""El expediente de captación, de la solicitud del prospecto a su habilitación.

  1. registrar_solicitante  → cap_solicitante
  2. abrir_caso             → cap_caso (INICIADO)
  3. consentimientos        → tratamiento de datos, consulta a burós y términos
  4. OTP                    → verifica el celular (y el correo, si se quiere)
  5. validaciones           → RENIEC, listas restrictivas, PEP, biometría
  6. centrales y perfil     → puntaje de riesgo de 0 a 1000
  7. habilitar              → registra al cliente en COREDB (o reutiliza el que ya
                              existe), anota sus validaciones y deja la referencia
                              vigente que consulta Solicitud de Crédito (CR-INT-01).

El estado del caso se recalcula después de cada paso (`_recalcular`):
INICIADO → EN_VALIDACION → APROBADO → HABILITADO, con OBSERVADO mientras algo
quede por resolver y RECHAZADO o REVOCADO como finales.
"""

import hashlib
import hmac
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from CAPTACION import proveedores
from CAPTACION.config import settings
from CAPTACION.core_client import CoreDb
from CAPTACION.errores import CaptacionError
from CAPTACION.models import (
    Caso, CodigoOtp, Consentimiento, ConsultaRiesgo, Evento, PerfilRiesgo, Solicitante, Validacion,
)

ABIERTOS = ("INICIADO", "EN_VALIDACION", "OBSERVADO", "APROBADO")
CERRADOS = ("HABILITADO", "RECHAZADO", "REVOCADO")
CONSENTIMIENTOS_REQUERIDOS = ("TRATAMIENTO_DATOS", "CONSULTA_BUROS", "TERMINOS")
OTP_MINUTOS = 5
OTP_INTENTOS = 3
VERSION_CONTRATO_SOL = "CR-INT-01-PROPUESTA-v2"
LIMA = timezone(timedelta(hours=-5))  # Perú no tiene horario de verano


def _ahora() -> datetime:
    """UTC sin zona, como se guarda en la base."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hoy_lima() -> date:
    return datetime.now(LIMA).date()


def _id() -> str:
    return str(uuid.uuid4())


def _evento(db: Session, id_caso: str | None, accion: str, actor: str, cid: str | None,
            detalle: dict | None = None) -> None:
    db.add(Evento(id_caso=id_caso, accion=accion, actor=actor, correlation_id=cid,
                  detalle=detalle, fecha=_ahora()))


# ══ Solicitante ════════════════════════════════════════════════════════════
REGLAS_DOCUMENTO = {
    # Las mismas de clientes.tipo_documento en la base integrada.
    "DNI": (8, 8, False), "CE": (9, 12, True), "PTP": (9, 9, False), "PASAPORTE": (6, 12, True),
}


def _validar_documento(tipo: str, numero: str) -> None:
    minimo, maximo, alfanumerico = REGLAS_DOCUMENTO[tipo]
    valido = minimo <= len(numero) <= maximo and (numero.isalnum() if alfanumerico else numero.isdigit())
    if not valido:
        raise CaptacionError("ERR-CAP-DOCUMENTO-INVALIDO",
                             f"El número no cumple la regla de {tipo}: {minimo} a {maximo} "
                             f"{'letras o dígitos' if alfanumerico else 'dígitos'}.", 400)


def obtener_solicitante(db: Session, id_solicitante: str) -> Solicitante:
    sol = db.get(Solicitante, id_solicitante)
    if sol is None:
        raise CaptacionError("ERR-CAP-SOLICITANTE-NO-ENCONTRADO", "El solicitante no existe.", 404)
    return sol


def registrar_solicitante(db: Session, datos: dict, actor: str, cid: str | None) -> tuple[Solicitante, bool]:
    """Si el documento ya se registró devuelve el mismo solicitante (duplicado=True)."""
    tipo, numero = datos["tipo_documento"], datos["numero_documento"]
    _validar_documento(tipo, numero)
    existente = db.scalar(select(Solicitante).where(Solicitante.tipo_documento == tipo,
                                                    Solicitante.numero_documento == numero))
    if existente is not None:
        _evento(db, None, "REGISTRAR_SOLICITANTE_DUPLICADO", actor, cid,
                {"id_solicitante": existente.id_solicitante})
        db.commit()
        return existente, True
    sol = Solicitante(id_solicitante=_id(), creado_por=actor, creado_en=_ahora(), **datos)
    db.add(sol)
    _evento(db, None, "REGISTRAR_SOLICITANTE", actor, cid, {"id_solicitante": sol.id_solicitante})
    db.commit()
    return sol, False


def buscar_solicitantes(db: Session, documento: str | None, limite: int) -> list[Solicitante]:
    consulta = select(Solicitante).order_by(Solicitante.creado_en.desc()).limit(limite)
    if documento:
        consulta = consulta.where(Solicitante.numero_documento.contains(documento.upper()))
    return list(db.scalars(consulta))


# ══ Caso ═══════════════════════════════════════════════════════════════════
def obtener_caso(db: Session, id_caso: str) -> Caso:
    caso = db.get(Caso, id_caso)
    if caso is None:
        raise CaptacionError("ERR-CAP-CASO-NO-ENCONTRADO", "El caso no existe.", 404)
    return caso


def _abierto(caso: Caso) -> None:
    if caso.estado in CERRADOS:
        raise CaptacionError("ERR-CAP-CASO-CERRADO", f"El caso está {caso.estado} y ya no admite cambios.",
                             409, {"estado": caso.estado})


def abrir_caso(db: Session, datos: dict, actor: str, cid: str | None) -> Caso:
    sol = obtener_solicitante(db, datos["id_solicitante"])
    abierto = db.scalar(select(Caso).where(Caso.id_solicitante == sol.id_solicitante,
                                           Caso.estado.in_(ABIERTOS)))
    if abierto is not None:
        raise CaptacionError("ERR-CAP-CASO-ABIERTO", "El solicitante ya tiene un caso abierto.", 409,
                             {"id_caso": abierto.id_caso, "estado": abierto.estado})
    caso = Caso(id_caso=_id(), estado="INICIADO", creado_por=actor, creado_en=_ahora(),
                cod_cliente=None, **datos)
    db.add(caso)
    _evento(db, caso.id_caso, "ABRIR_CASO", actor, cid, {"canal": caso.canal})
    db.commit()
    return caso


def listar_casos(db: Session, estado: str | None, limite: int, offset: int) -> list[tuple[Caso, Solicitante]]:
    consulta = (select(Caso, Solicitante).join(Solicitante, Solicitante.id_solicitante == Caso.id_solicitante)
                .order_by(Caso.creado_en.desc()).offset(offset).limit(limite))
    if estado:
        consulta = consulta.where(Caso.estado == estado)
    return [(c, s) for c, s in db.execute(consulta)]


# ══ Lecturas del expediente ════════════════════════════════════════════════
def _consentimientos(db: Session, id_caso: str) -> list[Consentimiento]:
    return list(db.scalars(select(Consentimiento).where(Consentimiento.id_caso == id_caso)
                           .order_by(Consentimiento.fecha, Consentimiento.id_consentimiento)))


def _validaciones(db: Session, id_caso: str) -> list[Validacion]:
    return list(db.scalars(select(Validacion).where(Validacion.id_caso == id_caso)
                           .order_by(Validacion.fecha, Validacion.id_validacion)))


def _consultas(db: Session, id_caso: str) -> list[ConsultaRiesgo]:
    return list(db.scalars(select(ConsultaRiesgo).where(ConsultaRiesgo.id_caso == id_caso)
                           .order_by(ConsultaRiesgo.fecha, ConsultaRiesgo.id_consulta)))


def _perfil(db: Session, id_caso: str) -> PerfilRiesgo | None:
    return db.scalar(select(PerfilRiesgo).where(PerfilRiesgo.id_caso == id_caso)
                     .order_by(PerfilRiesgo.fecha.desc(), PerfilRiesgo.id_perfil.desc()).limit(1))


def _ultimos(items, clave) -> dict:
    """El registro más reciente de cada tipo: una validación nueva reemplaza a la anterior."""
    ultimos = {}
    for item in items:
        ultimos[clave(item)] = item
    return ultimos


def faltantes(db: Session, caso: Caso, ignorar_perfil: bool = False) -> list[str]:
    """Lo que falta para habilitar. Vacío significa que el caso está listo."""
    f: list[str] = []
    if caso.estado in CERRADOS:
        return [f"Caso en estado {caso.estado}"]
    consent = _ultimos(_consentimientos(db, caso.id_caso), lambda c: c.tipo)
    for tipo in CONSENTIMIENTOS_REQUERIDOS:
        if not (tipo in consent and consent[tipo].aceptado):
            f.append(f"Consentimiento {tipo} aceptado")
    vals = _ultimos(_validaciones(db, caso.id_caso), lambda v: v.tipo)
    if not (vals.get("CELULAR") and vals["CELULAR"].resultado == "APROBADO"):
        f.append("Verificación OTP del celular")
    for tipo in ("RENIEC", "LISTAS_NEGRAS"):
        if not (vals.get(tipo) and vals[tipo].resultado == "APROBADO"):
            f.append(f"Validación {tipo} aprobada")
    rechazadas = sorted(t for t, v in vals.items() if v.resultado == "RECHAZADO")
    if rechazadas:
        f.append(f"Validaciones rechazadas: {', '.join(rechazadas)}")
    observadas = sorted(t for t, v in vals.items() if v.resultado == "OBSERVADO")
    if observadas:
        f.append(f"Validaciones observadas: {', '.join(observadas)} (registre una validación manual)")
    if caso.observacion:
        f.append(f"Observación del asesor: {caso.observacion}")
    if not ignorar_perfil:
        perfil = _perfil(db, caso.id_caso)
        consultas = _consultas(db, caso.id_caso)
        if perfil is None:
            f.append("Perfil de riesgo calculado")
        elif consultas and consultas[-1].fecha > perfil.fecha:
            f.append("Perfil de riesgo actualizado con la última consulta")
        elif perfil.calificacion == "MUY_ALTO":
            f.append("Perfil de riesgo MUY_ALTO")
    return f


def _recalcular(db: Session, caso: Caso) -> None:
    if caso.estado in CERRADOS:
        return
    db.flush()
    vals = _ultimos(_validaciones(db, caso.id_caso), lambda v: v.tipo)
    perfil = _perfil(db, caso.id_caso)
    rechazadas = [t for t, v in vals.items() if v.resultado == "RECHAZADO"]
    if rechazadas or (perfil is not None and perfil.calificacion == "MUY_ALTO"):
        caso.estado = "RECHAZADO"
        caso.cerrado_en = _ahora()
        caso.motivo_cierre = (f"Validación rechazada: {', '.join(sorted(rechazadas))}" if rechazadas
                              else "Perfil de riesgo MUY_ALTO")
        return
    if caso.observacion or any(v.resultado == "OBSERVADO" for v in vals.values()):
        caso.estado = "OBSERVADO"
    elif not faltantes(db, caso):
        caso.estado = "APROBADO"
    elif vals or _consentimientos(db, caso.id_caso) or _consultas(db, caso.id_caso):
        caso.estado = "EN_VALIDACION"
    else:
        caso.estado = "INICIADO"


def detalle(db: Session, id_caso: str) -> dict:
    caso = obtener_caso(db, id_caso)
    sol = obtener_solicitante(db, caso.id_solicitante)
    pendientes = faltantes(db, caso)
    return {
        "caso": caso, "solicitante": sol,
        "consentimientos": _consentimientos(db, id_caso),
        "validaciones": _validaciones(db, id_caso),
        "consultas": _consultas(db, id_caso),
        "perfil": _perfil(db, id_caso),
        "faltantes": [] if caso.estado in CERRADOS else pendientes,
        "listo_para_habilitar": caso.estado == "APROBADO" and not pendientes,
    }


# ══ Consentimientos ════════════════════════════════════════════════════════
def registrar_consentimientos(db: Session, id_caso: str, items: list[dict], actor: str,
                              cid: str | None) -> list[Consentimiento]:
    caso = obtener_caso(db, id_caso)
    _abierto(caso)
    creados = []
    for item in items:
        version = settings.cap_version_terminos if item["tipo"] == "TERMINOS" else None
        c = Consentimiento(id_consentimiento=_id(), id_caso=id_caso, tipo=item["tipo"],
                           aceptado=item["aceptado"], medio=item["medio"], version=version,
                           registrado_por=actor, fecha=_ahora())
        db.add(c)
        creados.append(c)
    _evento(db, id_caso, "REGISTRAR_CONSENTIMIENTOS", actor, cid,
            {c.tipo: c.aceptado for c in creados})
    _recalcular(db, caso)
    db.commit()
    return creados


def _exigir_consentimiento(db: Session, id_caso: str, tipo: str) -> None:
    ultimo = _ultimos(_consentimientos(db, id_caso), lambda c: c.tipo).get(tipo)
    if not (ultimo and ultimo.aceptado):
        raise CaptacionError("ERR-CAP-CONSENTIMIENTO-REQUERIDO",
                             f"El solicitante no ha aceptado el consentimiento {tipo}.", 422, {"tipo": tipo})


# ══ OTP ════════════════════════════════════════════════════════════════════
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


def enviar_otp(db: Session, id_caso: str, canal: str, actor: str, cid: str | None) -> dict:
    caso = obtener_caso(db, id_caso)
    _abierto(caso)
    _exigir_consentimiento(db, id_caso, "TRATAMIENTO_DATOS")
    sol = obtener_solicitante(db, caso.id_solicitante)
    destino = sol.celular if canal == "SMS" else sol.correo
    for previo in db.scalars(select(CodigoOtp).where(CodigoOtp.id_caso == id_caso,
                                                     CodigoOtp.canal == canal,
                                                     CodigoOtp.estado == "PENDIENTE")):
        previo.estado = "EXPIRADO"
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    otp = CodigoOtp(id_otp=_id(), id_caso=id_caso, canal=canal, destino=destino, intentos_fallidos=0,
                    estado="PENDIENTE", creado_en=_ahora(),
                    expira_en=_ahora() + timedelta(minutes=OTP_MINUTOS), codigo_hmac="")
    otp.codigo_hmac = _hmac(otp.id_otp, codigo)
    db.add(otp)
    _evento(db, id_caso, "ENVIAR_OTP", actor, cid, {"canal": canal})
    _recalcular(db, caso)
    db.commit()
    return {
        "canal": canal, "destino_enmascarado": enmascarar(destino),
        "expira_en": otp.expira_en.replace(tzinfo=timezone.utc).isoformat(),
        # Sin proveedor de SMS ni de correo, en laboratorio el código vuelve en la respuesta.
        "codigo_simulado": codigo if settings.cap_otp_simulado else None,
    }


def verificar_otp(db: Session, id_caso: str, canal: str, codigo: str, actor: str, cid: str | None) -> dict:
    caso = obtener_caso(db, id_caso)
    _abierto(caso)
    otp = db.scalar(select(CodigoOtp).where(CodigoOtp.id_caso == id_caso, CodigoOtp.canal == canal,
                                            CodigoOtp.estado == "PENDIENTE")
                    .order_by(CodigoOtp.creado_en.desc()).limit(1))
    if otp is None:
        raise CaptacionError("ERR-CAP-OTP-NO-ENCONTRADO", "No hay un código pendiente: envíe uno nuevo.", 404)
    if _ahora() > otp.expira_en:
        otp.estado = "EXPIRADO"
        db.commit()
        return {"verificado": False, "estado_codigo": "EXPIRADO", "intentos_restantes": 0}
    if hmac.compare_digest(otp.codigo_hmac, _hmac(otp.id_otp, codigo)):
        otp.estado = "USADO"
        tipo = "CELULAR" if canal == "SMS" else "CORREO"
        db.add(Validacion(id_validacion=_id(), id_caso=id_caso, tipo=tipo, resultado="APROBADO",
                          proveedor=f"OTP-{canal}", detalle=f"Código verificado en {enmascarar(otp.destino)}",
                          registrado_por=actor, fecha=_ahora()))
        _evento(db, id_caso, "VERIFICAR_OTP", actor, cid, {"canal": canal, "resultado": "OK"})
        _recalcular(db, caso)
        db.commit()
        return {"verificado": True, "estado_codigo": "USADO",
                "intentos_restantes": OTP_INTENTOS - otp.intentos_fallidos}
    otp.intentos_fallidos += 1
    if otp.intentos_fallidos >= OTP_INTENTOS:
        otp.estado = "BLOQUEADO"
    _evento(db, id_caso, "VERIFICAR_OTP", actor, cid,
            {"canal": canal, "resultado": "FALLIDO", "intentos": otp.intentos_fallidos})
    db.commit()
    return {"verificado": False, "estado_codigo": otp.estado,
            "intentos_restantes": max(OTP_INTENTOS - otp.intentos_fallidos, 0)}


# ══ Validaciones de identidad ══════════════════════════════════════════════
def ejecutar_validaciones(db: Session, id_caso: str, tipos: list[str], actor: str,
                          cid: str | None) -> list[Validacion]:
    caso = obtener_caso(db, id_caso)
    _abierto(caso)
    _exigir_consentimiento(db, id_caso, "TRATAMIENTO_DATOS")
    if "BIOMETRIA" in tipos:
        _exigir_consentimiento(db, id_caso, "BIOMETRIA")
    sol = obtener_solicitante(db, caso.id_solicitante)
    creadas = []
    for tipo in dict.fromkeys(tipos):
        resultado, texto = proveedores.validar(tipo, sol.tipo_documento, sol.numero_documento)
        v = Validacion(id_validacion=_id(), id_caso=id_caso, tipo=tipo, resultado=resultado,
                       proveedor=proveedores.NOMBRE, detalle=texto, registrado_por=actor, fecha=_ahora())
        db.add(v)
        creadas.append(v)
    _evento(db, id_caso, "EJECUTAR_VALIDACIONES", actor, cid, {v.tipo: v.resultado for v in creadas})
    _recalcular(db, caso)
    db.commit()
    return creadas


def validacion_manual(db: Session, id_caso: str, datos: dict, actor: str, cid: str | None) -> Validacion:
    """El veredicto de una revisión hecha por una persona (en agencia, o la debida
    diligencia de un PEP). Reemplaza al resultado anterior del mismo tipo."""
    caso = obtener_caso(db, id_caso)
    _abierto(caso)
    _exigir_consentimiento(db, id_caso, "TRATAMIENTO_DATOS")
    v = Validacion(id_validacion=_id(), id_caso=id_caso, tipo=datos["tipo"], resultado=datos["resultado"],
                   proveedor="MANUAL", detalle=datos["detalle"], registrado_por=actor, fecha=_ahora())
    db.add(v)
    _evento(db, id_caso, "VALIDACION_MANUAL", actor, cid, {"tipo": v.tipo, "resultado": v.resultado})
    _recalcular(db, caso)
    db.commit()
    return v


# ══ Centrales de riesgo y perfil ═══════════════════════════════════════════
def consultar_central(db: Session, id_caso: str, central: str, reporte: dict | None, actor: str,
                      cid: str | None) -> ConsultaRiesgo:
    caso = obtener_caso(db, id_caso)
    _abierto(caso)
    _exigir_consentimiento(db, id_caso, "CONSULTA_BUROS")
    sol = obtener_solicitante(db, caso.id_solicitante)
    datos = reporte or proveedores.consultar_central(sol.numero_documento)
    consulta = ConsultaRiesgo(id_consulta=_id(), id_caso=id_caso, central=central,
                              calificacion=datos["calificacion"], deuda_total=datos["deuda_total"],
                              entidades=datos["entidades"], dias_mora=datos["dias_mora"],
                              fuente="MANUAL" if reporte else proveedores.NOMBRE,
                              registrado_por=actor, fecha=_ahora())
    db.add(consulta)
    _evento(db, id_caso, "CONSULTAR_CENTRAL", actor, cid,
            {"central": central, "calificacion": consulta.calificacion, "fuente": consulta.fuente})
    _recalcular(db, caso)
    db.commit()
    return consulta


def calcular_perfil(db: Session, id_caso: str, actor: str, cid: str | None) -> PerfilRiesgo:
    caso = obtener_caso(db, id_caso)
    _abierto(caso)
    consultas = _consultas(db, id_caso)
    if not consultas:
        raise CaptacionError("ERR-CAP-SIN-CONSULTA", "Consulte al menos una central de riesgo.", 422)
    vals = _ultimos(_validaciones(db, id_caso), lambda v: v.tipo)
    observadas = sorted(t for t, v in vals.items() if v.resultado == "OBSERVADO")
    reportes = [{"calificacion": c.calificacion, "deuda_total": c.deuda_total, "entidades": c.entidades,
                 "dias_mora": c.dias_mora} for c in consultas]
    valor, calificacion, nota = proveedores.puntaje(reportes, observadas)
    perfil = PerfilRiesgo(id_perfil=_id(), id_caso=id_caso, puntaje=valor, calificacion=calificacion,
                          observacion=nota, fecha=max(_ahora(), consultas[-1].fecha))
    db.add(perfil)
    _evento(db, id_caso, "CALCULAR_PERFIL", actor, cid, {"puntaje": valor, "calificacion": calificacion})
    _recalcular(db, caso)
    db.commit()
    return perfil


# ══ Decisiones del asesor ══════════════════════════════════════════════════
def cambiar_estado(db: Session, id_caso: str, accion: str, motivo: str, actor: str, cid: str | None) -> Caso:
    caso = obtener_caso(db, id_caso)
    if accion == "REVOCAR":
        # Retira una habilitación vigente: Solicitud de Crédito ya no la aceptará.
        if caso.estado != "HABILITADO":
            raise CaptacionError("ERR-CAP-ESTADO-INVALIDO", "Solo se revoca un caso HABILITADO.", 409)
        caso.estado, caso.motivo_cierre = "REVOCADO", motivo
    else:
        _abierto(caso)
        if accion == "OBSERVAR":
            caso.observacion = motivo
        elif accion == "LEVANTAR_OBSERVACION":
            caso.observacion = None
        elif accion == "RECHAZAR":
            caso.estado, caso.motivo_cierre, caso.cerrado_en = "RECHAZADO", motivo, _ahora()
    _evento(db, id_caso, accion, actor, cid, {"motivo": motivo})
    _recalcular(db, caso)
    db.commit()
    return caso


# ══ Habilitación: el cliente en COREDB ═════════════════════════════════════
def habilitar(db: Session, core: CoreDb, id_caso: str, actor: str, cid: str | None) -> Caso:
    """Registra al cliente en COREDB como HABILITADO, o reutiliza el cliente activo que
    ya tenga ese documento, y deja la referencia vigente para Solicitud de Crédito.

    Se puede repetir: si una llamada a COREDB falla a mitad, el `cod_cliente` ya
    guardado evita registrar dos veces."""
    caso = obtener_caso(db, id_caso)
    if caso.estado == "HABILITADO":
        return caso
    pendientes = faltantes(db, caso)
    if pendientes or caso.estado != "APROBADO":
        raise CaptacionError("ERR-CAP-CASO-NO-LISTO", "El caso no cumple los requisitos para habilitarse.",
                             422, {"faltantes": pendientes or [f"Caso en estado {caso.estado}"]})
    sol = obtener_solicitante(db, caso.id_solicitante)

    if caso.cod_cliente is None:
        verificacion = core.verificar_documento(sol.tipo_documento, sol.numero_documento, cid)
        if verificacion["resultado"] == "APROBADO":
            caso.cod_cliente, caso.cliente_nuevo = verificacion["cliente"]["cod_cliente"], False
        elif verificacion.get("motivo") == "NO_ES_CLIENTE":
            terminos = _ultimos(_consentimientos(db, id_caso), lambda c: c.tipo)["TERMINOS"]
            registro = core.registrar_cliente({
                "tipo_documento": sol.tipo_documento, "numero_documento": sol.numero_documento,
                "nombres": sol.nombres, "apellido_paterno": sol.apellido_paterno,
                "apellido_materno": sol.apellido_materno, "correo": sol.correo, "celular": sol.celular,
                "version_contrato": terminos.version or settings.cap_version_terminos,
                "estado_habilitante": "HABILITADO",
            }, cid)
            caso.cod_cliente, caso.cliente_nuevo = registro["cod_cliente"], True
        else:
            # Es cliente, pero no está ACTIVO en el CORE (BLOQUEADO, SUSPENDIDO, OBSERVADO...).
            estado = (verificacion.get("cliente") or {}).get("estado_cliente", "NO ACTIVO")
            caso.observacion = f"El cliente existe en el CORE en estado {estado}"
            _evento(db, id_caso, "HABILITAR_RECHAZADO_POR_COREDB", actor, cid, {"estado_cliente": estado})
            _recalcular(db, caso)
            db.commit()
            raise CaptacionError("ERR-CAP-CLIENTE-NO-ACTIVO",
                                 f"El documento ya es de un cliente en estado {estado}: debe regularizarse "
                                 "en el CORE antes de habilitarlo.", 422, {"estado_cliente": estado})
        sol.cod_cliente = caso.cod_cliente
        _evento(db, id_caso, "CLIENTE_EN_COREDB", actor, cid,
                {"cod_cliente": caso.cod_cliente, "cliente_nuevo": caso.cliente_nuevo})
        db.commit()  # antes de seguir: un reintento no vuelve a registrar

    # Las verificaciones de contacto que hizo CAPTACION quedan también en el CORE.
    vals = _ultimos(_validaciones(db, id_caso), lambda v: v.tipo)
    for tipo in ("CELULAR", "CORREO"):
        if vals.get(tipo) and vals[tipo].resultado == "APROBADO":
            core.registrar_validacion(caso.cod_cliente, tipo, "APROBADO", f"OTP CAPTACION {id_caso[:8]}", cid)
    cliente = core.ver_cliente(caso.cod_cliente, cid)

    caso.id_verificacion_captacion = cliente["id_verificacion_captacion"]
    caso.estado_cliente = cliente["estado_cliente"]
    caso.fecha_verificacion = hoy_lima()
    caso.vigente_hasta = caso.fecha_verificacion + timedelta(days=settings.cap_vigencia_dias)
    caso.estado, caso.cerrado_en = "HABILITADO", _ahora()
    _evento(db, id_caso, "HABILITAR", actor, cid, {
        "cod_cliente": caso.cod_cliente, "vigente_hasta": caso.vigente_hasta.isoformat()})
    db.commit()
    return caso


# ══ Referencias para Solicitud de Crédito (CR-INT-01) ══════════════════════
def _referencia(caso: Caso, sol: Solicitante, cliente: dict | None = None) -> dict:
    """La referencia tal como la espera SOL (backend/SOL/integrations.py, CLIENT_FIELDS).

    Con `cliente` (la vista de COREDB) la identidad y el estado son los vigentes en el CORE;
    sin él, los guardados al habilitar."""
    fuente = cliente or {}
    return {
        "id_cliente": caso.cod_cliente,
        "cod_tipo_documento": fuente.get("tipo_documento", sol.tipo_documento),
        "numero_documento": fuente.get("numero_documento", sol.numero_documento),
        "nombres": fuente.get("nombres", sol.nombres),
        "apellido_paterno": fuente.get("apellido_paterno", sol.apellido_paterno),
        "apellido_materno": (fuente.get("apellido_materno") if cliente else sol.apellido_materno) or "",
        "estado_cliente": fuente.get("estado_cliente", caso.estado_cliente or ""),
        "id_caso": caso.id_caso,
        "id_verificacion": caso.id_verificacion_captacion or "",
        "fecha_verificacion": caso.fecha_verificacion.isoformat() if caso.fecha_verificacion else "",
        "vigente_hasta": caso.vigente_hasta.isoformat() if caso.vigente_hasta else "",
        "estado_habilitante": "HABILITADO" if caso.estado == "HABILITADO" else caso.estado,
        "version_contrato": VERSION_CONTRATO_SOL,
        # RENIEC, listas, PEP, centrales y SMS son simulados: la referencia lo dice.
        "simulado": True,
    }


def _ultimo_caso_de(db: Session, cod_cliente: str) -> Caso | None:
    return db.scalar(select(Caso).where(Caso.cod_cliente == cod_cliente,
                                        Caso.estado.in_(("HABILITADO", "REVOCADO")))
                     .order_by(Caso.fecha_verificacion.desc(), Caso.cerrado_en.desc()).limit(1))


def referencia(db: Session, core: CoreDb, cod_cliente: str, cid: str | None) -> dict | None:
    """Una referencia, con la identidad y el estado que tiene hoy el cliente en COREDB."""
    caso = _ultimo_caso_de(db, cod_cliente)
    if caso is None:
        return None
    sol = obtener_solicitante(db, caso.id_solicitante)
    try:
        cliente = core.ver_cliente(cod_cliente, cid)
    except CaptacionError as exc:
        if exc.status_code == 404:
            return None
        raise
    return _referencia(caso, sol, cliente)


def referencia_de_caso(db: Session, core: CoreDb, id_caso: str, cid: str | None) -> dict:
    caso = obtener_caso(db, id_caso)
    if caso.cod_cliente is None or caso.estado not in ("HABILITADO", "REVOCADO"):
        raise CaptacionError("ERR-CAP-SIN-REFERENCIA", "El caso todavía no está habilitado.", 409)
    sol = obtener_solicitante(db, caso.id_solicitante)
    return _referencia(caso, sol, core.ver_cliente(caso.cod_cliente, cid))


def buscar_referencias(db: Session, texto: str, limite: int) -> list[dict]:
    """Búsqueda acotada para el buscador de SOL. No consulta COREDB por cada fila: SOL
    vuelve a pedir la referencia individual antes de guardar o enviar."""
    consulta = (select(Solicitante).where(Solicitante.cod_cliente.is_not(None))
                .order_by(Solicitante.creado_en.desc()))
    texto = texto.strip()
    if texto:
        patron = f"%{texto}%"
        consulta = consulta.where(or_(Solicitante.numero_documento.ilike(patron),
                                      Solicitante.nombres.ilike(patron),
                                      Solicitante.apellido_paterno.ilike(patron),
                                      Solicitante.apellido_materno.ilike(patron)))
    resultado = []
    for sol in db.scalars(consulta.limit(200)):
        caso = _ultimo_caso_de(db, sol.cod_cliente)
        if caso is not None:
            resultado.append(_referencia(caso, sol))
        if len(resultado) >= limite:
            break
    return resultado
