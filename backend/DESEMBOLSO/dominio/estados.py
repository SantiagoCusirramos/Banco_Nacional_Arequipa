"""Estados de la orden y transiciones validas (las mismas que impone trg_des_orden_bu)."""
from enum import StrEnum


class Estado(StrEnum):
    PREPARADA = "PREPARADA"
    VALIDADA = "VALIDADA"
    EN_PROCESO = "EN_PROCESO"
    POR_VERIFICAR = "POR_VERIFICAR"
    CONFIRMADA = "CONFIRMADA"
    RECHAZADA = "RECHAZADA"
    REVERTIDA = "REVERTIDA"


TRANSICIONES: dict[Estado, set[Estado]] = {
    Estado.PREPARADA: {Estado.VALIDADA, Estado.RECHAZADA},
    Estado.VALIDADA: {Estado.PREPARADA, Estado.EN_PROCESO, Estado.RECHAZADA},
    Estado.EN_PROCESO: {Estado.CONFIRMADA, Estado.RECHAZADA, Estado.POR_VERIFICAR},
    Estado.POR_VERIFICAR: {Estado.CONFIRMADA, Estado.RECHAZADA},
    Estado.CONFIRMADA: {Estado.REVERTIDA},
    Estado.RECHAZADA: set(),
    Estado.REVERTIDA: set(),
}

EDITABLES = {Estado.PREPARADA, Estado.VALIDADA}
INCIERTOS = {Estado.EN_PROCESO, Estado.POR_VERIFICAR}
CON_RESULTADO_FINANCIERO = {Estado.CONFIRMADA, Estado.REVERTIDA}
EJECUTADOS = INCIERTOS | CON_RESULTADO_FINANCIERO | {Estado.RECHAZADA}


def puede_transitar(origen: str, destino: str) -> bool:
    return Estado(destino) in TRANSICIONES[Estado(origen)]


class TipoValidacion(StrEnum):
    APROBACION = "APROBACION"
    IDENTIDAD = "IDENTIDAD"
    CUENTA = "CUENTA"
    AUTORIZACION = "AUTORIZACION"
    ANTIFRAUDE = "ANTIFRAUDE"


REQUERIDAS_PARA_VALIDAR = (TipoValidacion.APROBACION, TipoValidacion.IDENTIDAD, TipoValidacion.CUENTA)
