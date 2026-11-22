"""Lógica de negocio del módulo ATM."""

from decimal import Decimal
from uuid import UUID, uuid4
from ATM.core_client import CoreClient
from ATM.exceptions import AtmError
from ATM.errores import validar_monto, validar_resultado_dispensacion, traducir
from ATM.schemas.atm import (
    AutorizarIn, AutorizacionOut, ConfirmarIn, CuentaSaldoOut, ExtornarIn, SaldoOut, ValidarPinIn,
    ValidarPinOut,
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

    # Consultar cuentas consolidadas del cliente: CUENTAS devuelve una lista con todas sus cuentas.
    cuentas = core.consultar_saldo(
        cod_cliente=cod_cliente,
        correlation_id=correlation_id,
        authorization=authorization,
    )
    if not isinstance(cuentas, list):
        raise AtmError("ERR-ATM-RESPUESTA_INVALIDA", "CUENTAS devolvió una respuesta inesperada", 502)
    # El cajero solo opera la cuenta vinculada a la tarjeta (la base rechaza las demás con
    # ERR-TAR-008); TARJETAS la devuelve en num_cuenta.
    num_cuenta = tarjeta.get("num_cuenta")
    return SaldoOut(
        lista_cuentas=[
            CuentaSaldoOut(
                id_cuenta=c["num_cuenta"],
                num_cuenta_enmascarado="****" + c["num_cuenta"][-4:],
                moneda=c["moneda"],
                saldo_disponible=str(c["saldo_disponible"]),
            )
            for c in cuentas if num_cuenta and c.get("num_cuenta") == num_cuenta
        ],
        uuid_consulta=str(uuid4()),
    )


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

# Mismo mensaje si el documento no existe o si los dígitos no coinciden: el cajero no dice qué
# documentos tienen tarjeta. El PIN (tres intentos) sigue siendo lo que autoriza.
NO_RECONOCIDA = ("ERR-ATM-TARJETA-NO-RECONOCIDA",
                 "No reconocimos la tarjeta. Revisa el documento y los 4 últimos dígitos.", 404)
_PREFERENCIA = {"ACTIVA": 0, "BLOQUEADA": 1, "RETENIDA": 1}


def identificar_tarjeta(core, datos, cid: str, token: str):
    """La tarjeta del titular con ese documento exacto y esos 4 últimos dígitos (la activa si
    hay más de una). Con el token del operador que abrió el cajero."""
    from ATM.exceptions import AtmError
    from ATM.schemas.atm import IdentificarOut

    documento = datos.documento.upper()
    clientes = {s.get("cod_cliente") for s in core.buscar_por_documento(documento, token, cid)
                if isinstance(s, dict) and str(s.get("numero_documento", "")).upper() == documento and s.get("cod_cliente")}
    candidatas = []
    for cod in sorted(clientes):
        for t in core.tarjetas_del_cliente(cod, token, cid):
            if isinstance(t, dict) and t.get("ultimos4") == datos.ultimos4 and t.get("id_tarjeta"):
                candidatas.append(t)
    if not candidatas:
        raise AtmError(*NO_RECONOCIDA)
    elegida = min(candidatas, key=lambda t: _PREFERENCIA.get(t.get("estado_tarjeta"), 2))
    return IdentificarOut(id_tarjeta=elegida["id_tarjeta"], ultimos4=elegida["ultimos4"])
