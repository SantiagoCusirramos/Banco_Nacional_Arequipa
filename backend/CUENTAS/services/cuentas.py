from CUENTAS.core_client import CoreClient
from CUENTAS.exceptions import CuentasError
from CUENTAS.schemas.cuentas import AbrirCuentaIn, OperacionIn, TransferenciaIn

ACTOR = "cuentas"


def abrir_cuenta(core: CoreClient, datos: AbrirCuentaIn, correlation_id: str):
    # RN-CTA-002: mancomunada necesita al menos 2 titulares
    titulares = datos.titulares or []
    if any(t.rol_titular == "MANCOMUNADO" for t in titulares) and len(titulares) < 2:
        raise CuentasError("ERR-CTA-MANCOMUNADA-SIN-COTITULARES",
                           "Una cuenta mancomunada requiere al menos 2 titulares", 400)
    payload = datos.model_dump(mode="json")
    payload.update(actor=ACTOR, correlation_id=correlation_id)
    return core.crear_cuenta(payload, correlation_id)


def ver_cuenta(core: CoreClient, num_cuenta: str, correlation_id: str):
    return core.ver_cuenta(num_cuenta, correlation_id)


def cuentas_del_cliente(core: CoreClient, id_cliente: str, correlation_id: str):
    return core.cuentas_del_cliente(id_cliente, correlation_id)


def operar(core: CoreClient, tipo: str, datos: OperacionIn, id_canal: str,
           idempotency_key: str, correlation_id: str):
    payload = datos.model_dump(mode="json")
    payload.update(tipo_operacion=tipo, id_canal=id_canal, idempotency_key=idempotency_key,
                   actor=ACTOR, correlation_id=correlation_id)
    return core.registrar_movimiento(payload, idempotency_key, correlation_id)


def transferir(core: CoreClient, datos: TransferenciaIn, id_canal: str,
               idempotency_key: str, correlation_id: str):
    if datos.num_cuenta_origen == datos.num_cuenta_destino:
        raise CuentasError("ERR-CTA-CUENTAS-IGUALES",
                           "La cuenta origen y destino no pueden ser la misma", 400)
    payload = datos.model_dump(mode="json")
    payload.update(id_canal=id_canal, idempotency_key=idempotency_key,
                   actor=ACTOR, correlation_id=correlation_id)
    return core.transferir(payload, idempotency_key, correlation_id)
