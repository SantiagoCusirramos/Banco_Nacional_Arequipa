from uuid import UUID, uuid4

from CUENTAS.core_client import CoreClient
from CUENTAS.exceptions import CuentasError
from CUENTAS.schemas.cuentas import AbrirCuentaIn, OperacionIn, TransferenciaIn


def _uuid(valor: str) -> str:
    # COREDB exige UUID en correlation_id
    try:
        return str(UUID(valor))
    except ValueError:
        return str(uuid4())


def _glosa(tipo: str, id_canal: str) -> str:
    return f"{tipo.capitalize()} por canal {id_canal}"


def abrir_cuenta(core: CoreClient, datos: AbrirCuentaIn, correlation_id: str,
                 authorization: str | None = None):
    ids = [t.id_cliente for t in datos.titulares or []]
    # RN-CTA-002: mancomunada necesita al menos 2 titulares
    if datos.regimen.startswith("MANCOMUNADA") and len(ids) < 2:
        raise CuentasError("ERR-CTA-MANCOMUNADA-SIN-COTITULARES",
                           "Una cuenta mancomunada requiere al menos 2 titulares", 400)
    if datos.regimen == "INDIVIDUAL" and len(ids) != 1:
        raise CuentasError("ERR-CTA-REGIMEN-INVALIDO",
                           "Una cuenta individual tiene un solo titular", 400)
    payload = {
        "num_cuenta": datos.num_cuenta,
        "cci": datos.cci,
        "moneda": datos.moneda,
        "regimen": datos.regimen,
        "id_agencia": datos.id_agencia,
        "titulares": ids,
    }
    return core.crear_cuenta(payload, correlation_id, authorization)


def ver_cuenta(core: CoreClient, num_cuenta: str, correlation_id: str,
               authorization: str | None = None):
    return core.ver_cuenta(num_cuenta, correlation_id, authorization)


def cuentas_del_cliente(core: CoreClient, id_cliente: str, correlation_id: str,
                        authorization: str | None = None):
    # COREDB no tiene todavia una ruta que liste las cuentas de un cliente
    raise CuentasError("ERR-CTA-NO-IMPLEMENTADO",
                       "COREDB aun no ofrece la consulta de cuentas por cliente", 501)


def operar(core: CoreClient, tipo: str, datos: OperacionIn, id_canal: str,
           idempotency_key: str, correlation_id: str, authorization: str | None = None):
    payload = {
        "num_cuenta": datos.num_cuenta,
        "tipo": tipo,
        "monto": format(datos.monto, ".2f"),
        "glosa": datos.glosa or _glosa(tipo, id_canal),
        "id_canal": id_canal,
        "idempotency_key": idempotency_key,
        "correlation_id": _uuid(correlation_id),
    }
    r = core.registrar_movimiento(payload, idempotency_key, correlation_id, authorization)
    return {"uuid_transaccion": r["uuid_transaccion"], "replay": bool(r.get("repetido"))}


def transferir(core: CoreClient, datos: TransferenciaIn, id_canal: str,
               idempotency_key: str, correlation_id: str, authorization: str | None = None):
    if datos.num_cuenta_origen == datos.num_cuenta_destino:
        raise CuentasError("ERR-CTA-CUENTAS-IGUALES",
                           "La cuenta origen y destino no pueden ser la misma", 400)
    payload = {
        "origen": datos.num_cuenta_origen,
        "destino": datos.num_cuenta_destino,
        "monto": format(datos.monto, ".2f"),
        "glosa": datos.glosa or _glosa("transferencia", id_canal),
        "id_canal": id_canal,
        "idempotency_key": idempotency_key,
        "correlation_id": _uuid(correlation_id),
    }
    r = core.transferir(payload, idempotency_key, correlation_id, authorization)
    return {"uuid_debito": r["uuid_debito"], "uuid_abono": r["uuid_abono"],
            "replay": bool(r.get("repetido"))}


def listar_movimientos(core: CoreClient, num_cuenta: str, correlation_id: str,
                       authorization: str | None = None):
    return core.listar_movimientos(num_cuenta, correlation_id, authorization)


def ver_movimiento(core: CoreClient, uuid_transaccion: str, correlation_id: str,
                   authorization: str | None = None):
    return core.ver_movimiento(uuid_transaccion, correlation_id, authorization)
