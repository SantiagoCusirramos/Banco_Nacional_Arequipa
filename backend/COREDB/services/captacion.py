"""Captación: el expediente del prospecto sobre clientes.*_captacion (bd-v1.7-mysql).

La base guarda el expediente y aplica sus reglas (consentimientos exigidos, OTP con
vencimiento e intentos, un caso abierto por solicitante, estado recalculado). El módulo
CAPTACION llama a los proveedores, calcula el puntaje y el HMAC del OTP. La API escribe
por procedimientos y lee las vistas v_*_captacion_api, que no exponen el hash del OTP.
Los mensajes de la base de esta sección no llevan valores de entrada.
"""

import json
import uuid
from collections.abc import Callable
from datetime import timezone
from decimal import Decimal
from typing import Any, TypeVar

from sqlalchemy import text
from sqlalchemy.orm import Session

from COREDB.database import llamar
from COREDB.errores import ErrorCoreDb
from COREDB.transacciones import con_reintentos

T = TypeVar("T")

# Regla de la base → (código de la API, estado HTTP).
REGLAS: dict[str, tuple[str, int]] = {
    "BNA-DOCUMENTO": ("DOCUMENTO_INVALIDO", 422),
    "BNA-SOLICITANTE-DATOS": ("DATOS_INVALIDOS", 422),
    "BNA-SOLICITANTE": ("SOLICITANTE_NO_ENCONTRADO", 404),
    "BNA-CASO": ("CASO_NO_ENCONTRADO", 404),
    "BNA-CASO-ABIERTO": ("CASO_ABIERTO", 409),
    "BNA-CASO-CERRADO": ("CASO_CERRADO", 409),
    "BNA-CASO-DATOS": ("DATOS_INVALIDOS", 422),
    "BNA-CASO-ESTADO": ("ESTADO_INVALIDO", 409),
    "BNA-CASO-NO-LISTO": ("CASO_NO_LISTO", 422),
    "BNA-CASO-CLIENTE": ("CASO_CON_OTRO_CLIENTE", 409),
    "BNA-AGENCIA": ("AGENCIA_NO_ENCONTRADA", 422),
    "BNA-CONSENTIMIENTO-DATOS": ("DATOS_INVALIDOS", 422),
    "BNA-CONSENTIMIENTO-REQUERIDO": ("CONSENTIMIENTO_REQUERIDO", 422),
    "BNA-OTP": ("OTP_NO_ENCONTRADO", 404),
    "BNA-OTP-DATOS": ("DATOS_INVALIDOS", 422),
    "BNA-VALIDACION-CAPTACION": ("DATOS_INVALIDOS", 422),
    "BNA-RIESGO-DATOS": ("DATOS_INVALIDOS", 422),
    "BNA-SIN-CONSULTA": ("SIN_CONSULTA", 422),
    "BNA-CLIENTE": ("CLIENTE_NO_ENCONTRADO", 404),
    "BNA-CLIENTE-DOCUMENTO": ("CLIENTE_NO_COINCIDE", 422),
    "BNA-CLIENTE-NO-ACTIVO": ("CLIENTE_NO_ACTIVO", 422),
}
# Dos altas simultáneas chocan con una restricción única.
DUPLICADOS = {
    "uk_caso_captacion_1": ("CASO_ABIERTO", "El solicitante ya tiene un caso abierto."),
}


def _mensaje(mensaje: str) -> str:
    texto = mensaje.split(":", 1)[-1].strip()
    return (texto[:1].upper() + texto[1:] + ("" if texto.endswith(".") else ".")) if texto else "Rechazado."


def traducir(exc: ErrorCoreDb) -> ErrorCoreDb:
    restriccion = getattr(exc, "restriccion", None)
    if exc.code == "REGISTRO_DUPLICADO":
        if restriccion in DUPLICADOS:
            codigo, texto = DUPLICADOS[restriccion]
            return ErrorCoreDb(codigo, texto, 409)
        if restriccion == "PRIMARY":
            return ErrorCoreDb("IDENTIFICADOR_DUPLICADO", "Ya existe un registro con ese identificador.", 409)
    if exc.code in REGLAS:
        codigo, estado = REGLAS[exc.code]
        return ErrorCoreDb(codigo, _mensaje(exc.message), estado)
    return exc


def _escribir(db: Session, operacion: Callable[[], T], nombre: str) -> T:
    try:
        return con_reintentos(db, operacion, nombre=nombre)
    except ErrorCoreDb as exc:
        raise traducir(exc) from None


def caso_no_encontrado() -> ErrorCoreDb:
    return ErrorCoreDb("CASO_NO_ENCONTRADO", "El caso no existe.", 404)


def _utc(valor):
    return None if valor is None else valor.replace(tzinfo=timezone.utc)


def _fila(fila, fechas=(), logicos=()) -> dict[str, Any]:
    datos = dict(fila._mapping)
    for campo in fechas:
        datos[campo] = _utc(datos[campo])
    for campo in logicos:
        if datos[campo] is not None:
            datos[campo] = bool(datos[campo])
    return datos


# ── Solicitantes ────────────────────────────────────────────────────────────

_SOLICITANTE = ("SELECT id_solicitante, tipo_documento, numero_documento, nombres, apellido_paterno, apellido_materno, "
                "celular, correo, cod_cliente, creado_por, fecha_registro FROM clientes.v_solicitante_captacion_api")


def _solicitante(fila) -> dict[str, Any]:
    return _fila(fila, fechas=("fecha_registro",))


def ver_solicitante(db: Session, id_solicitante: uuid.UUID) -> dict[str, Any]:
    fila = db.execute(text(f"{_SOLICITANTE} WHERE id_solicitante = :id"), {"id": str(id_solicitante)}).first()
    if fila is None:
        raise ErrorCoreDb("SOLICITANTE_NO_ENCONTRADO", "El solicitante no existe.", 404)
    return _solicitante(fila)


def registrar_solicitante(db: Session, datos: dict[str, Any], *, correlation_id: uuid.UUID,
                          actor: str) -> tuple[dict[str, Any], bool]:
    """Un documento ya registrado devuelve el mismo solicitante (duplicado) sin cambiarlo."""
    def operacion():
        return llamar(
            db, "clientes.registrar_solicitante_captacion",
            uuid.uuid4(), datos["tipo_documento"], datos["numero_documento"], datos["nombres"],
            datos["apellido_paterno"], datos["apellido_materno"], datos["celular"], datos["correo"], actor,
            correlation_id, salidas=2,
        )

    try:
        id_bin, duplicado = _escribir(db, operacion, "registrar_solicitante_captacion")
    except ErrorCoreDb as exc:
        # Dos altas simultáneas del mismo documento: la segunda encuentra a la primera.
        if exc.code != "REGISTRO_DUPLICADO" or getattr(exc, "restriccion", None) != "uk_solicitante_captacion_1":
            raise
        id_bin, duplicado = _escribir(db, operacion, "registrar_solicitante_captacion")
    return ver_solicitante(db, uuid.UUID(bytes=id_bin)), bool(duplicado)


def buscar_solicitantes(db: Session, *, documento: str | None, texto: str | None, con_cliente: bool,
                        limite: int) -> list[dict[str, Any]]:
    condiciones, parametros = [], {"limite": limite}
    if documento:
        condiciones.append("numero_documento LIKE :documento")
        parametros["documento"] = f"%{_sin_comodines(documento.upper())}%"
    if texto:
        condiciones.append("(LOWER(numero_documento) LIKE :texto OR LOWER(nombres) LIKE :texto "
                           "OR LOWER(apellido_paterno) LIKE :texto OR LOWER(coalesce(apellido_materno, '')) LIKE :texto)")
        parametros["texto"] = f"%{_sin_comodines(texto.lower())}%"
    if con_cliente:
        condiciones.append("cod_cliente IS NOT NULL")
    donde = f" WHERE {' AND '.join(condiciones)}" if condiciones else ""
    filas = db.execute(text(f"{_SOLICITANTE}{donde} ORDER BY fecha_registro DESC, id_solicitante LIMIT :limite"),
                       parametros)
    return [_solicitante(f) for f in filas]


def _sin_comodines(valor: str) -> str:
    return valor.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# ── Casos ───────────────────────────────────────────────────────────────────

_CASO = ("SELECT id_caso, id_solicitante, canal, id_agencia, producto_interes, estado, observacion, motivo_cierre, "
         "cod_cliente, cliente_nuevo, id_verificacion_captacion, estado_cliente, fecha_verificacion, vigente_hasta, "
         "creado_por, fecha_apertura, fecha_cierre, faltantes FROM clientes.v_caso_captacion_api")


def _caso(fila) -> dict[str, Any]:
    datos = _fila(fila, fechas=("fecha_apertura", "fecha_cierre"), logicos=("cliente_nuevo",))
    faltantes = datos["faltantes"]
    datos["faltantes"] = json.loads(faltantes) if isinstance(faltantes, str) else list(faltantes or [])
    return datos


def abrir_caso(db: Session, datos: dict[str, Any], *, correlation_id: uuid.UUID, actor: str) -> dict[str, Any]:
    id_caso = uuid.uuid4()
    _escribir(db, lambda: llamar(
        db, "clientes.abrir_caso_captacion", id_caso, datos["id_solicitante"], datos["canal"], datos["id_agencia"],
        datos["producto_interes"], actor, correlation_id,
    ), "abrir_caso_captacion")
    return ver_caso(db, id_caso)


def ver_caso(db: Session, id_caso: uuid.UUID) -> dict[str, Any]:
    fila = db.execute(text(f"{_CASO} WHERE id_caso = :id"), {"id": str(id_caso)}).first()
    if fila is None:
        raise caso_no_encontrado()
    return _caso(fila)


def listar_casos(db: Session, *, estado: str | None, id_solicitante: uuid.UUID | None, cod_cliente: str | None,
                 limite: int, offset: int) -> list[dict[str, Any]]:
    condiciones, parametros = [], {"limite": limite, "offset": offset}
    if estado:
        condiciones.append("estado = :estado")
        parametros["estado"] = estado
    if id_solicitante:
        condiciones.append("id_solicitante = :sol")
        parametros["sol"] = str(id_solicitante)
    if cod_cliente:
        condiciones.append("cod_cliente = :cliente")
        parametros["cliente"] = cod_cliente
    donde = f" WHERE {' AND '.join(condiciones)}" if condiciones else ""
    casos = [_caso(f) for f in db.execute(
        text(f"{_CASO}{donde} ORDER BY fecha_apertura DESC, id_caso LIMIT :limite OFFSET :offset"), parametros)]
    ids = sorted({c["id_solicitante"] for c in casos})
    solicitantes = {}
    if ids:
        marcas = ", ".join(f":s{i}" for i in range(len(ids)))
        for fila in db.execute(text(f"{_SOLICITANTE} WHERE id_solicitante IN ({marcas})"),
                               {f"s{i}": v for i, v in enumerate(ids)}):
            solicitantes[fila.id_solicitante] = _solicitante(fila)
    return [{**c, "solicitante": solicitantes[c["id_solicitante"]]} for c in casos]


def expediente(db: Session, id_caso: uuid.UUID) -> dict[str, Any]:
    caso = ver_caso(db, id_caso)
    parametros = {"id": str(id_caso)}

    def filas(sql, **opciones):
        return [_fila(f, **opciones) for f in db.execute(text(sql), parametros)]

    consentimientos = filas(
        "SELECT tipo, aceptado, medio, version, registrado_por, fecha FROM clientes.v_consentimiento_captacion_api "
        "WHERE id_caso = :id ORDER BY id_consentimiento", fechas=("fecha",), logicos=("aceptado",))
    otps = filas(
        "SELECT id_otp, canal, estado, intentos_fallidos, fecha_emision, fecha_expiracion "
        "FROM clientes.v_otp_captacion_api WHERE id_caso = :id ORDER BY fecha_emision, id_otp",
        fechas=("fecha_emision", "fecha_expiracion"))
    validaciones = filas(
        "SELECT tipo, resultado, proveedor, detalle, registrado_por, fecha FROM clientes.v_validacion_captacion_api "
        "WHERE id_caso = :id ORDER BY id_validacion", fechas=("fecha",))
    consultas = filas(
        "SELECT central, calificacion, deuda_total, entidades, dias_mora, fuente, registrado_por, fecha "
        "FROM clientes.v_consulta_riesgo_captacion_api WHERE id_caso = :id ORDER BY id_consulta", fechas=("fecha",))
    perfiles = filas(
        "SELECT puntaje, calificacion, observacion, registrado_por, fecha, vigente "
        "FROM clientes.v_perfil_riesgo_captacion_api WHERE id_caso = :id ORDER BY id_perfil DESC LIMIT 1",
        fechas=("fecha",), logicos=("vigente",))
    for c in consultas:
        c["deuda_total"] = Decimal(c["deuda_total"]).quantize(Decimal("0.01"))
    return {
        **caso,
        "solicitante": ver_solicitante(db, uuid.UUID(caso["id_solicitante"])),
        "consentimientos": consentimientos,
        "otps": otps,
        "validaciones": validaciones,
        "consultas": consultas,
        "perfil": perfiles[0] if perfiles else None,
        "listo_para_habilitar": caso["estado"] == "APROBADO" and not caso["faltantes"],
    }


def _exige_caso(db: Session, id_caso: uuid.UUID) -> None:
    """Un caso inexistente es 404 antes de llamar a la base."""
    if db.execute(text("SELECT 1 FROM clientes.v_caso_captacion_api WHERE id_caso = :id"),
                  {"id": str(id_caso)}).first() is None:
        raise caso_no_encontrado()


def _paso(db: Session, id_caso: uuid.UUID, procedimiento: str, *entradas: Any, salidas: int = 0) -> tuple:
    _exige_caso(db, id_caso)
    return _escribir(db, lambda: llamar(db, f"clientes.{procedimiento}", *entradas, salidas=salidas), procedimiento)


def registrar_consentimientos(db: Session, id_caso: uuid.UUID, consentimientos: list[dict[str, Any]],
                              version_terminos: str | None, *, correlation_id: uuid.UUID, actor: str) -> None:
    _paso(db, id_caso, "registrar_consentimientos_captacion", id_caso, json.dumps(consentimientos), version_terminos,
          actor, correlation_id, salidas=1)


def emitir_otp(db: Session, id_caso: uuid.UUID, *, id_otp: uuid.UUID, canal: str, codigo_hmac: str,
               correlation_id: uuid.UUID, actor: str) -> dict[str, Any]:
    _paso(db, id_caso, "emitir_otp_captacion", id_otp, id_caso, canal, codigo_hmac, actor, correlation_id, salidas=1)
    fila = db.execute(text(
        "SELECT id_otp, canal, estado, intentos_fallidos, fecha_emision, fecha_expiracion "
        "FROM clientes.v_otp_captacion_api WHERE id_otp = :id"), {"id": str(id_otp)}).one()
    return _fila(fila, fechas=("fecha_emision", "fecha_expiracion"))


def verificar_otp(db: Session, id_caso: uuid.UUID, id_otp: uuid.UUID, codigo_hmac: str, *,
                  correlation_id: uuid.UUID, actor: str) -> dict[str, Any]:
    estado_codigo, restantes, estado = _paso(
        db, id_caso, "verificar_otp_captacion", id_otp, id_caso, codigo_hmac, actor, correlation_id, salidas=3)
    return {"estado_codigo": estado_codigo, "intentos_restantes": int(restantes), "estado": estado}


def registrar_validacion(db: Session, id_caso: uuid.UUID, datos: dict[str, Any], *, correlation_id: uuid.UUID,
                         actor: str) -> None:
    _paso(db, id_caso, "registrar_validacion_captacion", id_caso, datos["tipo"], datos["resultado"],
          datos["proveedor"], datos["detalle"], actor, correlation_id, salidas=1)


def registrar_consulta(db: Session, id_caso: uuid.UUID, datos: dict[str, Any], *, correlation_id: uuid.UUID,
                       actor: str) -> None:
    _paso(db, id_caso, "registrar_consulta_riesgo_captacion", id_caso, datos["central"], datos["calificacion"],
          datos["deuda_total"], datos["entidades"], datos["dias_mora"], datos["fuente"], actor, correlation_id,
          salidas=1)


def registrar_perfil(db: Session, id_caso: uuid.UUID, datos: dict[str, Any], *, correlation_id: uuid.UUID,
                     actor: str) -> None:
    _paso(db, id_caso, "registrar_perfil_captacion", id_caso, datos["puntaje"], datos["calificacion"],
          datos["observacion"], actor, correlation_id, salidas=1)


def cambiar_estado(db: Session, id_caso: uuid.UUID, accion: str, motivo: str, *, correlation_id: uuid.UUID,
                   actor: str) -> None:
    _paso(db, id_caso, "cambiar_estado_caso_captacion", id_caso, accion, motivo, actor, correlation_id, salidas=1)


def vincular_cliente(db: Session, id_caso: uuid.UUID, cod_cliente: str, cliente_nuevo: bool, *,
                     correlation_id: uuid.UUID, actor: str) -> None:
    _paso(db, id_caso, "vincular_cliente_captacion", id_caso, cod_cliente, cliente_nuevo, actor, correlation_id)


def habilitar(db: Session, id_caso: uuid.UUID, vigencia_dias: int, *, correlation_id: uuid.UUID, actor: str) -> None:
    _paso(db, id_caso, "habilitar_caso_captacion", id_caso, vigencia_dias, actor, correlation_id, salidas=1)
