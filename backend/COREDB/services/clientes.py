"""Clientes sobre los procedimientos de la base.

El usuario de la API no lee `clientes.*`: el cliente llega como JSON de un
procedimiento, sin datos biométricos. Los mensajes de error nunca repiten el
documento, el correo ni el celular.
"""

import json
import uuid
from collections.abc import Callable
from typing import Any, TypeVar

from sqlalchemy.orm import Session

from COREDB.database import llamar
from COREDB.errores import ErrorCoreDb
from COREDB.transacciones import con_reintentos

T = TypeVar("T")

# Restricción única de clientes.cliente → error del contrato.
DUPLICADOS = {
    "uk_cliente_1": ("CLIENTE_DUPLICADO", "Ya existe un cliente con ese documento."),
    "uk_cliente_2": ("CORREO_DUPLICADO", "Ese correo ya pertenece a un cliente."),
    "uk_cliente_3": ("CELULAR_DUPLICADO", "Ese celular ya pertenece a un cliente."),
}
# Reglas de la base que el contrato publica con otro código.
REGLAS = {
    "BNA-CLIENTE": ("CLIENTE_NO_ENCONTRADO", "El cliente no existe.", 404),
    "BNA-DATOS-CLIENTE": ("DATOS_INVALIDOS", "Los datos no cumplen las reglas de la base.", 422),
    "BNA-VALIDACION": ("DATOS_INVALIDOS", "Los datos no cumplen las reglas de la base.", 422),
}


def no_encontrado() -> ErrorCoreDb:
    return ErrorCoreDb(*REGLAS["BNA-CLIENTE"])


def _traducir(exc: ErrorCoreDb) -> ErrorCoreDb:
    duplicado = DUPLICADOS.get(getattr(exc, "restriccion", None) or "")
    if duplicado:
        return ErrorCoreDb(*duplicado, 409)
    if exc.code in REGLAS:
        return ErrorCoreDb(*REGLAS[exc.code])
    return exc


def _escribir(db: Session, operacion: Callable[[], T], nombre: str) -> T:
    try:
        return con_reintentos(db, operacion, nombre=nombre)
    except ErrorCoreDb as exc:
        raise _traducir(exc) from None


def _json(valor: str | None) -> Any:
    return None if valor is None else json.loads(valor)


def consultar(db: Session, cod_cliente: str) -> dict[str, Any]:
    (cliente,) = llamar(db, "clientes.consultar_cliente", cod_cliente, salidas=1)
    if cliente is None:
        raise no_encontrado()
    return _json(cliente)


def registrar(
    db: Session, *, tipo_documento: str, numero_documento: str, nombres: str,
    apellido_paterno: str, apellido_materno: str | None, correo: str, celular: str,
    version_contrato: str, estado_habilitante: str, correlation_id: uuid.UUID, actor: str,
) -> dict[str, Any]:
    def operacion() -> dict[str, Any]:
        (cod_cliente,) = llamar(
            db, "clientes.registrar_cliente",
            tipo_documento, numero_documento, nombres, apellido_paterno, apellido_materno,
            correo, celular, version_contrato, estado_habilitante, correlation_id, actor,
            salidas=1,
        )
        return consultar(db, cod_cliente)

    return _escribir(db, operacion, "registrar_cliente")


def verificar_documento(
    db: Session, *, tipo_documento: str, numero_documento: str, identidad_verificada: bool,
    motivo: str | None, correlation_id: uuid.UUID, actor: str,
) -> dict[str, Any]:
    id_validacion, resultado, motivo_core, cliente = _escribir(
        db,
        lambda: llamar(
            db, "clientes.verificar_documento",
            tipo_documento, numero_documento, identidad_verificada, motivo, correlation_id, actor,
            salidas=4,
        ),
        "verificar_documento",
    )
    return {"id_validacion": id_validacion, "resultado": resultado, "motivo": motivo_core,
            "cliente": _json(cliente)}


def registrar_validacion(
    db: Session, *, cod_cliente: str, tipo_validacion: str, resultado: str, motivo: str | None,
    correlation_id: uuid.UUID, actor: str,
) -> int:
    (id_validacion,) = _escribir(
        db,
        lambda: llamar(
            db, "clientes.registrar_validacion",
            cod_cliente, tipo_validacion, resultado, motivo, correlation_id, actor, salidas=1,
        ),
        "registrar_validacion",
    )
    return id_validacion


def cambiar_estado(
    db: Session, *, cod_cliente: str, estado: str, motivo: str, actor: str
) -> dict[str, Any]:
    def operacion() -> dict[str, Any]:
        (anterior,) = llamar(
            db, "clientes.cambiar_estado_cliente", cod_cliente, estado, motivo, actor, salidas=1
        )
        return {**consultar(db, cod_cliente), "estado_anterior": anterior}

    return _escribir(db, operacion, "cambiar_estado_cliente")


def catalogos(db: Session) -> dict[str, Any]:
    (valor,) = llamar(db, "clientes.catalogos_cliente", salidas=1)
    return _json(valor)
