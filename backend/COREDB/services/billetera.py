"""Billetera Digital (bd-v1.9): escrituras por billetera.* y lecturas de billetera.v_*_api.

Las reglas (afiliación, PIN e intentos, tope del canal BD, QR vigente, solicitud pendiente,
idempotencia) las aplica la base. Aquí se calculan la huella de cada operación de dinero
y las respuestas. Ningún mensaje ni registro repite el celular.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from COREDB.database import llamar
from COREDB.errores import ErrorCoreDb
from COREDB.transacciones import con_reintentos


def huella(operacion: str, cod_cliente: str, **parametros: Any) -> str:
    """SHA-256 de la operación, el cliente y sus parámetros: la misma llave con otros datos
    (u otro cliente) es BNA-IDEMPOTENCIA."""
    datos = {"operacion": operacion, "cod_cliente": cod_cliente, **parametros}
    return hashlib.sha256(json.dumps(datos, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _uuid(valor: bytes | None) -> uuid.UUID | None:
    return None if valor is None else uuid.UUID(bytes=bytes(valor))


@dataclass(frozen=True)
class Acceso:
    resultado: str
    cod_cliente: str | None


def validar_acceso(db: Session, celular: str, pin: str, correlacion: uuid.UUID | None) -> Acceso:
    cod, resultado, _ = con_reintentos(
        db, lambda: llamar(db, "billetera.validar_acceso", celular, pin, correlacion, salidas=3),
        nombre="validar_acceso",
    )
    return Acceso(resultado, cod)


def afiliar(db: Session, cod_cliente: str, num_cuenta: str, pin: str, actor: str,
            correlacion: uuid.UUID | None) -> bool:
    (nueva,) = con_reintentos(
        db, lambda: llamar(db, "billetera.afiliar", cod_cliente, num_cuenta, pin, actor, correlacion, salidas=1),
        nombre="afiliar",
    )
    return bool(nueva)


def registrar_comercio(db: Session, ruc: str, razon_social: str, num_cuenta: str, actor: str,
                       correlacion: uuid.UUID | None) -> uuid.UUID:
    id_comercio, _ = con_reintentos(
        db, lambda: llamar(db, "billetera.registrar_comercio", ruc, razon_social, num_cuenta, actor, correlacion,
                           salidas=2),
        nombre="registrar_comercio",
    )
    return _uuid(id_comercio)


def buscar_contacto(db: Session, cod_cliente: str, celular: str) -> str | None:
    (nombre,) = llamar(db, "billetera.buscar_contacto", cod_cliente, celular, salidas=1)
    db.commit()
    return nombre


def crear_qr(db: Session, cod_cliente: str, monto: Decimal | None, minutos: int | None, actor: str) -> uuid.UUID:
    id_qr, _ = con_reintentos(
        db, lambda: llamar(db, "billetera.crear_qr", cod_cliente, monto, minutos, actor, None, salidas=2),
        nombre="crear_qr",
    )
    return _uuid(id_qr)


def transferir(db: Session, cod_cliente: str, celular_destino: str, monto: Decimal, referencia: str | None,
               llave: str, actor: str, correlacion: uuid.UUID | None) -> tuple[uuid.UUID, bool]:
    marca = huella("P2P", cod_cliente, celular_destino=celular_destino, monto=monto, referencia=referencia)
    id_operacion, _, repetido = con_reintentos(
        db, lambda: llamar(db, "billetera.transferir", cod_cliente, celular_destino, monto, referencia, llave,
                           marca, actor, correlacion, salidas=3),
        nombre="transferir",
    )
    return _uuid(id_operacion), bool(repetido)


def pagar_qr(db: Session, cod_cliente: str, id_qr: uuid.UUID, monto: Decimal | None, llave: str, actor: str,
             correlacion: uuid.UUID | None) -> tuple[uuid.UUID, bool]:
    marca = huella("QR", cod_cliente, id_qr=id_qr, monto=monto)
    id_operacion, _, repetido = con_reintentos(
        db, lambda: llamar(db, "billetera.pagar_qr", cod_cliente, id_qr, monto, llave, marca, actor, correlacion,
                           salidas=3),
        nombre="pagar_qr",
    )
    return _uuid(id_operacion), bool(repetido)


def crear_solicitud(db: Session, cod_cliente: str, celular: str, monto: Decimal, concepto: str | None,
                    actor: str) -> uuid.UUID:
    (id_solicitud,) = con_reintentos(
        db, lambda: llamar(db, "billetera.crear_solicitud", cod_cliente, celular, monto, concepto, actor, None,
                           salidas=1),
        nombre="crear_solicitud",
    )
    return _uuid(id_solicitud)


def responder_solicitud(db: Session, cod_cliente: str, id_solicitud: uuid.UUID, accion: str, llave: str | None,
                        actor: str) -> tuple[str, uuid.UUID | None, bool]:
    marca = huella("SOLICITUD", cod_cliente, id_solicitud=id_solicitud) if llave else None
    estado, id_operacion, _, repetido = con_reintentos(
        db, lambda: llamar(db, "billetera.responder_solicitud", cod_cliente, id_solicitud, accion, llave, marca,
                           actor, None, salidas=4),
        nombre="responder_solicitud",
    )
    return estado, _uuid(id_operacion), bool(repetido)


def marcar_leidas(db: Session, cod_cliente: str) -> int:
    (filas,) = con_reintentos(
        db, lambda: llamar(db, "billetera.marcar_notificaciones_leidas", cod_cliente, salidas=1),
        nombre="marcar_notificaciones_leidas",
    )
    return int(filas or 0)


# --- Lecturas -----------------------------------------------------------------------

def _filas(db: Session, sql: str, **parametros: Any) -> list[dict[str, Any]]:
    return [dict(f._mapping) for f in db.execute(text(sql), parametros)]


def _una(db: Session, sql: str, codigo: str, mensaje: str, **parametros: Any) -> dict[str, Any]:
    filas = _filas(db, sql, **parametros)
    if not filas:
        raise ErrorCoreDb(codigo, mensaje, 404)
    return filas[0]


def afiliacion(db: Session, cod_cliente: str) -> dict[str, Any]:
    return _una(db, "SELECT * FROM billetera.v_afiliacion_api WHERE cod_cliente = :c",
                "AFILIACION_NO_ENCONTRADA", "El cliente no está afiliado a la billetera.", c=cod_cliente)


def perfil(db: Session, cod_cliente: str) -> dict[str, Any]:
    datos = afiliacion(db, cod_cliente)
    tope = datos["tope_diario"]
    datos["disponible_hoy"] = None if tope is None else max(Decimal("0"), tope - datos["consumido_hoy"])
    datos["notificaciones_sin_leer"] = db.execute(text(
        "SELECT COUNT(*) FROM billetera.v_notificacion_api WHERE cod_cliente = :c AND leida = 0"),
        {"c": cod_cliente}).scalar_one()
    datos["solicitudes_pendientes"] = db.execute(text(
        "SELECT COUNT(*) FROM billetera.v_solicitud_api WHERE cod_pagador = :c AND estado = 'PENDIENTE'"),
        {"c": cod_cliente}).scalar_one()
    return datos


def comercio(db: Session, id_comercio: uuid.UUID) -> dict[str, Any]:
    return _una(db, "SELECT * FROM billetera.v_comercio_api WHERE id_comercio = :i",
                "COMERCIO_NO_ENCONTRADO", "El comercio no existe.", i=str(id_comercio))


def comercios_activos(db: Session) -> list[dict[str, Any]]:
    return _filas(db, "SELECT id_comercio, razon_social, id_qr FROM billetera.v_comercio_api "
                      "WHERE estado = 'ACTIVO' AND id_qr IS NOT NULL ORDER BY razon_social")


def qr(db: Session, id_qr: uuid.UUID) -> dict[str, Any]:
    fila = _una(db, "SELECT * FROM billetera.v_qr_api WHERE id_qr = :i",
                "QR_NO_ENCONTRADO", "El código QR no existe.", i=str(id_qr))
    fila["es_comercio"] = fila["id_comercio"] is not None
    return fila


def operacion(db: Session, id_operacion: uuid.UUID, cod_cliente: str) -> dict[str, Any]:
    fila = _una(db, "SELECT * FROM billetera.v_operacion_api WHERE id_operacion = :i "
                    "AND (cod_cliente_origen = :c OR cod_cliente_destino = :c)",
                "OPERACION_NO_ENCONTRADA", "La operación no existe.", i=str(id_operacion), c=cod_cliente)
    return _con_sentido(fila, cod_cliente)


def _con_sentido(fila: dict[str, Any], cod_cliente: str) -> dict[str, Any]:
    fila["sentido"] = "ENVIADA" if fila["cod_cliente_origen"] == cod_cliente else "RECIBIDA"
    return fila


def operaciones(db: Session, cod_cliente: str, limite: int) -> list[dict[str, Any]]:
    filas = _filas(db, "SELECT * FROM billetera.v_operacion_api WHERE cod_cliente_origen = :c "
                       "OR cod_cliente_destino = :c ORDER BY fecha_hora DESC, id_operacion LIMIT :l",
                   c=cod_cliente, l=limite)
    return [_con_sentido(f, cod_cliente) for f in filas]


def movimientos(db: Session, num_cuenta: str, limite: int) -> list[dict[str, Any]]:
    return _filas(db, "SELECT uuid_transaccion, num_cuenta, tipo_operacion, naturaleza, monto, moneda, glosa, "
                      "id_canal, estado_transaccion, fecha_hora FROM cuentas.v_movimiento_api "
                      "WHERE num_cuenta = :n ORDER BY fecha_hora DESC, uuid_transaccion LIMIT :l",
                  n=num_cuenta, l=limite)


def solicitud(db: Session, id_solicitud: uuid.UUID) -> dict[str, Any]:
    return _una(db, "SELECT * FROM billetera.v_solicitud_api WHERE id_solicitud = :i",
                "SOLICITUD_NO_ENCONTRADA", "La solicitud no existe.", i=str(id_solicitud))


def solicitudes(db: Session, cod_cliente: str, limite: int) -> dict[str, list[dict[str, Any]]]:
    consulta = ("SELECT * FROM billetera.v_solicitud_api WHERE {col} = :c "
                "ORDER BY fecha_solicitud DESC, id_solicitud LIMIT :l")
    return {
        "recibidas": _filas(db, consulta.format(col="cod_pagador"), c=cod_cliente, l=limite),
        "enviadas": _filas(db, consulta.format(col="cod_solicitante"), c=cod_cliente, l=limite),
    }


def notificaciones(db: Session, cod_cliente: str, limite: int) -> list[dict[str, Any]]:
    return _filas(db, "SELECT * FROM billetera.v_notificacion_api WHERE cod_cliente = :c "
                      "ORDER BY id_notificacion DESC LIMIT :l", c=cod_cliente, l=limite)
