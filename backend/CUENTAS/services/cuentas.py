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
    return core.cuentas_de_cliente(id_cliente, correlation_id, authorization)


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
    resultado = {"uuid_debito": r["uuid_debito"], "uuid_abono": r["uuid_abono"],
                 "replay": bool(r.get("repetido"))}
    # Solo lecturas, después de la llamada que mueve el dinero: si alguna falla, la
    # transferencia sigue registrada y el dato queda en None.
    resultado.update(_comprobante(core, resultado, correlation_id, authorization))
    return resultado


def _leer(funcion, *args):
    try:
        return funcion(*args) or {}
    except (CuentasError, ValueError):  # ValueError: COREDB respondió algo que no es JSON
        return {}


def _comprobante(core: CoreClient, transferencia: dict, correlation_id: str,
                 authorization: str | None) -> dict:
    debito = _leer(core.ver_movimiento, transferencia["uuid_debito"], correlation_id, authorization)
    abono = _leer(core.ver_movimiento, transferencia["uuid_abono"], correlation_id, authorization)
    origen, destino = debito.get("num_cuenta"), abono.get("num_cuenta")
    cuenta_origen = _leer(core.ver_cuenta, origen, correlation_id, authorization) if origen else {}
    titular = None
    if destino:
        try:
            titular = _titular(core, core.ver_cuenta(destino, correlation_id, authorization),
                               correlation_id, authorization)
        except (CuentasError, ValueError):
            titular = None
    return {
        "num_cuenta_origen": origen,
        "num_cuenta_destino": destino,
        "monto": debito.get("monto"),
        "moneda": debito.get("moneda"),
        "fecha_hora": debito.get("fecha_hora"),
        "estado": debito.get("estado_transaccion"),
        "saldo_disponible_origen": cuenta_origen.get("saldo_disponible"),
        "titular_destino": titular,
    }


def enmascarar_nombre(*partes: str | None) -> str:
    """Dos letras de cada palabra y tres asteriscos (una letra y uno si la palabra es corta)."""
    palabras = " ".join(p for p in partes if p).split()
    return " ".join(p[:2] + "***" if len(p) > 2 else p[:1] + "*" for p in palabras)


def _titular(core: CoreClient, cuenta: dict, correlation_id: str,
             authorization: str | None) -> str:
    nombres = []
    for cod in cuenta.get("titulares") or []:
        c = core.ver_cliente(cod, correlation_id, authorization)
        nombres.append(enmascarar_nombre(c.get("nombres"), c.get("apellido_paterno"),
                                         c.get("apellido_materno")))
    if not nombres:
        raise CuentasError("ERR-CTA-SIN-TITULAR", "La cuenta no tiene titulares registrados", 502)
    return " y ".join(nombres)


def destino(core: CoreClient, num_cuenta: str, correlation_id: str,
            authorization: str | None = None):
    cuenta = core.ver_cuenta(num_cuenta, correlation_id, authorization)
    return {"num_cuenta": cuenta["num_cuenta"], "moneda": cuenta["moneda"],
            "estado_cuenta": cuenta["estado_cuenta"],
            "titular": _titular(core, cuenta, correlation_id, authorization)}


def listar_movimientos(core: CoreClient, num_cuenta: str, correlation_id: str,
                       authorization: str | None = None):
    return core.listar_movimientos(num_cuenta, correlation_id, authorization)


def ver_movimiento(core: CoreClient, uuid_transaccion: str, correlation_id: str,
                   authorization: str | None = None):
    return core.ver_movimiento(uuid_transaccion, correlation_id, authorization)
