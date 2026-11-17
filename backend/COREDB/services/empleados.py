"""Empleados: el administrador los registra y los liga a su usuario (core.registrar_empleado).

Así un analista de crédito queda disponible sin el administrador de la base: empleado,
usuario ANALISTA ligado y `POST /coredb/creditos/analistas`. La API no lee
`core.empleado`: la respuesta repite lo que la base guardó con las mismas reglas.
"""

import uuid

from sqlalchemy.orm import Session

from COREDB.database import llamar
from COREDB.errores import ErrorCoreDb
from COREDB.transacciones import con_reintentos

# Los mensajes de estas reglas no llevan valores de entrada: se devuelven tal cual.
REGLAS = {
    "BNA-EMPLEADO-DUPLICADO": ("EMPLEADO_DUPLICADO", 409),
    "BNA-USUARIO-EMPLEADO": ("USUARIO_NO_ADMITIDO", 409),
    "BNA-USUARIO": ("USUARIO_NO_ENCONTRADO", 404),
    "BNA-AGENCIA": ("AGENCIA_NO_ENCONTRADA", 422),
    "BNA-EMPLEADO-DATOS": ("DATOS_INVALIDOS", 422),
}


def _traducir(exc: ErrorCoreDb) -> ErrorCoreDb:
    # Dos altas simultáneas con el mismo código: la segunda choca con la restricción única.
    if exc.code == "REGISTRO_DUPLICADO" and getattr(exc, "restriccion", None) in {"PRIMARY", "uk_empleado_1"}:
        return ErrorCoreDb("EMPLEADO_DUPLICADO", "El código de empleado ya existe.", 409)
    if exc.code in REGLAS:
        codigo, estado = REGLAS[exc.code]
        texto = exc.message.split(":", 1)[-1].strip()
        return ErrorCoreDb(codigo, texto[:1].upper() + texto[1:] + ".", estado)
    return exc


def registrar(
    db: Session,
    *,
    codigo_empleado: str,
    nombre_completo: str,
    cargo: str,
    id_agencia: str | None,
    id_usuario: uuid.UUID | None,
    actor: str,
) -> uuid.UUID:
    id_empleado = uuid.uuid4()
    try:
        con_reintentos(
            db,
            lambda: llamar(
                db, "core.registrar_empleado",
                id_empleado, codigo_empleado, nombre_completo, cargo, id_agencia, id_usuario, actor,
            ),
            nombre="registrar_empleado",
        )
    except ErrorCoreDb as exc:
        raise _traducir(exc) from None
    return id_empleado
