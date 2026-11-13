import secrets
from datetime import date
from uuid import UUID, uuid4, uuid5

from TARJETAS.core_client import CoreClient
from TARJETAS.exceptions import TarjetasError
from TARJETAS.schemas.tarjetas import BloqueoIn, EmisionIn, EstadoIn

# Espacio de nombres fijo de los ids de emision. No cambiarlo: una llave ya usada daria otro id.
_ESPACIO_EMISION = UUID("2f6c1b7e-5a43-4d9e-9a1c-7b3e8f0d4c21")


def _uuid(valor: str) -> str:
    # COREDB exige UUID en correlation_id
    try:
        return str(UUID(valor))
    except ValueError:
        return str(uuid4())


def _id_tarjeta(valor: str) -> str:
    try:
        return str(UUID(valor))
    except ValueError:
        raise TarjetasError("ERR-TAR-ID-INVALIDO", "El identificador de la tarjeta debe ser un UUID", 400)


def _en_cuatro_anios(desde: date) -> date:
    try:
        return desde.replace(year=desde.year + 4)
    except ValueError:  # 29 de febrero
        return desde.replace(year=desde.year + 4, day=28)


def tarjetas_del_cliente(core: CoreClient, cod_cliente: str, correlation_id: str,
                         authorization: str | None = None):
    return core.tarjetas_de_cliente(cod_cliente.upper(), _uuid(correlation_id), authorization)


def ver_tarjeta(core: CoreClient, id_tarjeta: str, correlation_id: str, authorization: str | None = None):
    return core.ver_tarjeta(_id_tarjeta(id_tarjeta), _uuid(correlation_id), authorization)


def id_de_emision(idempotency_key: str) -> str:
    """La misma llave da siempre el mismo id de tarjeta (UUIDv5): repetir la emisión choca
    con la tarjeta ya emitida en vez de emitir otra."""
    return str(uuid5(_ESPACIO_EMISION, idempotency_key))


def _misma_emision(tarjeta: dict, datos: EmisionIn) -> bool:
    # Solo se comparan los datos que fija quien llama: la fecha por omisión cambia de un día a otro.
    return (
        tarjeta["cod_cliente"] == datos.cod_cliente.upper()
        # COREDB devuelve la cuenta principal, la de la emisión. Sin ella no se da por repetida.
        and tarjeta.get("num_cuenta") == datos.num_cuenta
        and tarjeta["bin"] == datos.bin
        and (datos.ultimos4 is None or tarjeta["ultimos4"] == datos.ultimos4)
        and (datos.fecha_emision is None or tarjeta["fecha_emision"] == datos.fecha_emision.isoformat())
        and (datos.fecha_vencimiento is None or tarjeta["fecha_vencimiento"] == datos.fecha_vencimiento.isoformat())
    )


def emitir(core: CoreClient, datos: EmisionIn, idempotency_key: str, correlation_id: str,
           authorization: str | None = None) -> tuple[dict, bool]:
    """Emite la tarjeta y dice si ya se había emitido antes con la misma llave."""
    emision = datos.fecha_emision or date.today()
    vencimiento = datos.fecha_vencimiento or _en_cuatro_anios(emision)
    if vencimiento <= emision:
        raise TarjetasError("ERR-TAR-VIGENCIA-INVALIDA",
                            "La fecha de vencimiento debe ser posterior a la de emisión", 400)
    id_tarjeta = id_de_emision(idempotency_key)
    payload = {
        "id_tarjeta": id_tarjeta,
        # El PAN no pasa por este servicio: COREDB recibe un token en su lugar.
        "pan_token": secrets.token_hex(16),
        "bin": datos.bin,
        "ultimos4": datos.ultimos4 or f"{secrets.randbelow(10_000):04d}",
        "fecha_emision": emision.isoformat(),
        "fecha_vencimiento": vencimiento.isoformat(),
        "cod_cliente": datos.cod_cliente.upper(),
        "num_cuenta": datos.num_cuenta,
    }
    try:
        return core.emitir_tarjeta(payload, _uuid(correlation_id), authorization), False
    except TarjetasError as error:
        if error.code != "REGISTRO_DUPLICADO":
            raise
    # Ya existe una tarjeta con ese id: es una repeticion, o la llave se uso para otra emision.
    tarjeta = core.ver_tarjeta(id_tarjeta, _uuid(correlation_id), authorization)
    if not _misma_emision(tarjeta, datos):
        raise TarjetasError("ERR-TAR-IDEMPOTENCIA",
                            "La llave de idempotencia ya se usó para emitir otra tarjeta", 409)
    return tarjeta, True


def cambiar_estado(core: CoreClient, id_tarjeta: str, datos: EstadoIn, correlation_id: str,
                   authorization: str | None = None):
    payload = {"estado": datos.estado}
    if datos.motivo:
        payload["motivo"] = datos.motivo
    return core.cambiar_estado(_id_tarjeta(id_tarjeta), payload, _uuid(correlation_id), authorization)


def bloquear(core: CoreClient, id_tarjeta: str, datos: BloqueoIn, correlation_id: str,
             authorization: str | None = None):
    return cambiar_estado(core, id_tarjeta, EstadoIn(estado="BLOQUEADA", motivo=datos.motivo),
                          correlation_id, authorization)
