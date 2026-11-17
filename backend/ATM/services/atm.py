"""Lógica de negocio del módulo ATM."""

from decimal import Decimal
from uuid import UUID
from ATM.core_client import CoreClient
from ATM.exceptions import AtmError
from ATM.errores import validar_monto, validar_resultado_dispensacion, traducir
from ATM.schemas.atm import (
    AutorizarIn, AutorizacionOut, ConfirmarIn, ExtornarIn, SaldoOut, ValidarPinIn, ValidarPinOut,
)


def _uuid_valido(valor: str) -> str:
    try:
        return str(UUID(valor))
    except ValueError:
        raise AtmError("ERR-ATM-ID-INVALIDO", "Identificador debe ser UUID", 400)


async def validar_pin(core: CoreClient, datos: ValidarPinIn,
                      correlation_id: str, authorization: str | None) -> ValidarPinOut:
    """Valida el PIN llamando a TARJETAS por el Bus."""
    _uuid_valido(datos.id_tarjeta)
    resp = core.validar_pin(
        id_tarjeta=datos.id_tarjeta,
        pin=datos.pin,
        id_terminal=datos.id_terminal,
        correlation_id=correlation_id,
        authorization=authorization,
    )
    return ValidarPinOut(**resp)


async def autorizar_retiro(core: CoreClient, datos: AutorizarIn,
                           idempotency_key: str, correlation_id: str,
                           authorization: str | None) -> AutorizacionOut:
    """Autoriza un retiro (retención de saldo) llamando a TARJETAS por el Bus.
    La idempotencia la maneja TARJETAS con la cabecera X-Idempotency-Key."""
    _uuid_valido(datos.id_tarjeta)
    _uuid_valido(datos.uuid_transaccion)

    # Validar monto y moneda (los topes los aplica TARJETAS)
    es_valido, codigo = validar_monto(datos.monto, datos.moneda)
    if not es_valido:
        raise AtmError(codigo, "Monto inválido: debe ser múltiplo de 10", 400)

    resp = core.autorizar(
        id_tarjeta=datos.id_tarjeta,
        num_cuenta=datos.num_cuenta,
        moneda=datos.moneda,
        monto=datos.monto,
        id_canal=datos.id_canal,
        id_terminal=datos.id_terminal,
        uuid_transaccion=datos.uuid_transaccion,
        correlation_id=correlation_id,
        authorization=authorization,
        idempotency_key=idempotency_key,
    )
    return AutorizacionOut(**resp)


async def confirmar_dispensacion(core: CoreClient, datos: ConfirmarIn,
                                 idempotency_key: str, correlation_id: str,
                                 authorization: str | None) -> AutorizacionOut:
    """Confirma la dispensación (o fallo) llamando a TARJETAS por el Bus."""
    _uuid_valido(datos.uuid_autorizacion)

    es_valido, codigo = validar_resultado_dispensacion(datos.resultado)
    if not es_valido:
        raise AtmError(codigo, "Resultado de dispensación inválido", 400)

    if datos.resultado == "NO_DISPENSADO":
        # El dinero no salió: se libera la retención en vez de debitar.
        resp = core.extornar(
            uuid_autorizacion=datos.uuid_autorizacion,
            motivo="NO_DISPENSADO",
            correlation_id=correlation_id,
            authorization=authorization,
        )
        return AutorizacionOut(**resp)

    resp = core.confirmar(
        uuid_autorizacion=datos.uuid_autorizacion,
        id_canal=datos.id_canal,
        id_terminal=datos.id_terminal,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        authorization=authorization,
    )
    return AutorizacionOut(**resp)


async def extornar_autorizacion(core: CoreClient, datos: ExtornarIn,
                                correlation_id: str, authorization: str | None) -> AutorizacionOut:
    """Extorna una autorización (libera saldo retenido y tope) llamando a TARJETAS por el Bus."""
    _uuid_valido(datos.uuid_autorizacion)

    resp = core.extornar(
        uuid_autorizacion=datos.uuid_autorizacion,
        motivo=datos.motivo,
        correlation_id=correlation_id,
        authorization=authorization,
    )
    return AutorizacionOut(**resp)


async def consultar_saldo(core: CoreClient, id_tarjeta: str,
                          correlation_id: str, authorization: str | None) -> SaldoOut:
    """Consulta el saldo de las cuentas asociadas a la tarjeta.
    Primero obtiene el cod_cliente de la tarjeta, luego consulta cuentas consolidadas."""
    _uuid_valido(id_tarjeta)

    # Obtener datos de la tarjeta (incluye cod_cliente)
    tarjeta = core.obtener_cliente_de_tarjeta(
        id_tarjeta=id_tarjeta,
        correlation_id=correlation_id,
        authorization=authorization,
    )
    cod_cliente = tarjeta.get("cod_cliente")
    if not cod_cliente:
        raise AtmError("ERR-ATM-TARJETA-SIN-CLIENTE", "La tarjeta no tiene cliente asociado", 400)

    # Consultar cuentas consolidadas del cliente
    resp = core.consultar_saldo(
        cod_cliente=cod_cliente,
        correlation_id=correlation_id,
        authorization=authorization,
    )
    return SaldoOut(**resp)


async def consultar_movimientos(core: CoreClient, num_cuenta: str,
                                correlation_id: str, authorization: str | None) -> list[dict]:
    """Consulta los movimientos de una cuenta."""
    if not num_cuenta:
        raise AtmError("ERR-ATM-CUENTA-REQUERIDA", "Se requiere num_cuenta", 400)

    resp = core.consultar_movimientos(
        num_cuenta=num_cuenta,
        correlation_id=correlation_id,
        authorization=authorization,
    )
    return resp