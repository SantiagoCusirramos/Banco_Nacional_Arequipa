"""Tarjetas — acciones VER/CREAR/BLOQUEAR_TARJETA.

RNF-13 / RGN-18: el PAN nunca se almacena ni se transmite en claro;
CORE solo conserva el token, el BIN y los últimos 4 dígitos. La
validación de tarjeta/clave es responsabilidad del módulo Tarjetas.
"""

import hashlib
import secrets
from datetime import date, datetime

from sqlalchemy.orm import Session

from CORE.exceptions import NotFoundError, ValidationError
from CORE.models import Cliente, TarHistorialEstado, TarTarjeta, TarTarjetaCuenta
from CORE.services import auditoria, cuentassvc
from CORE.utils.ids import new_uuid7

ESTADOS_TARJETA = ("ACTIVA", "BLOQUEADA", "VENCIDA", "ANULADA")
TIPOS_TARJETA = ("DEBITO", "CREDITO", "PREPAGO")
BIN_BNA = "004499"  # BIN de emisión del BNA (ficticio, 6 dígitos)


def _pan_ficticio() -> str:
    """Genera un PAN de 16 dígitos SOLO para derivar BIN/últimos4/token.

    El PAN se descarta inmediatamente; jamás se persiste (RNF-13).
    """
    digitos = "".join(str(secrets.randbelow(10)) for _ in range(10))
    return BIN_BNA + digitos


def listar_tarjetas(
    db: Session, *, id_cliente: str | None = None, estado: str | None = None,
    limite: int = 50, offset: int = 0,
) -> list[TarTarjeta]:
    q = db.query(TarTarjeta)
    if id_cliente:
        q = q.filter(TarTarjeta.id_cliente == id_cliente)
    if estado:
        q = q.filter(TarTarjeta.estado == estado)
    return q.order_by(TarTarjeta.fecha_creacion.desc()).offset(offset).limit(limite).all()


def obtener_tarjeta(db: Session, id_tarjeta: str) -> TarTarjeta:
    tarjeta = db.get(TarTarjeta, id_tarjeta)
    if tarjeta is None:
        raise NotFoundError("TARJETA_NO_ENCONTRADA", f"Tarjeta {id_tarjeta} no existe.")
    return tarjeta


def emitir_tarjeta(
    db: Session,
    *,
    id_cliente: str,
    num_cuenta: str,
    tipo_tarjeta: str = "DEBITO",
    anios_vigencia: int = 4,
    es_principal: bool = True,
    habilitada_atm: bool = True,
    actor: str = "sistema",
    correlation_id: str | None = None,
) -> TarTarjeta:
    """RF-TAR-01 (acción CREAR_TARJETA): emite tarjeta vinculada a una
    cuenta del cliente, con PAN tokenizado."""
    if db.get(Cliente, id_cliente) is None:
        raise NotFoundError("CLIENTE_NO_ENCONTRADO", f"Cliente {id_cliente} no existe.")
    cuenta = cuentassvc.obtener_cuenta(db, num_cuenta)
    if tipo_tarjeta not in TIPOS_TARJETA:
        raise ValidationError(
            "TIPO_TARJETA_INVALIDO",
            f"Tipo {tipo_tarjeta} no admitido. Opciones: {', '.join(TIPOS_TARJETA)}.",
        )

    # La cuenta debe estar vinculada al cliente
    from CORE.models import ClienteCuenta

    vinculo = (
        db.query(ClienteCuenta)
        .filter(
            ClienteCuenta.num_cuenta == num_cuenta,
            ClienteCuenta.id_cliente == id_cliente,
        )
        .first()
    )
    if vinculo is None:
        raise ValidationError(
            "CUENTA_NO_PERTENECE_AL_CLIENTE",
            f"El cliente {id_cliente} no es titular de la cuenta {num_cuenta}.",
        )

    pan = _pan_ficticio()
    pan_token = hashlib.sha256(pan.encode("utf-8")).hexdigest()
    hoy = date.today()
    vencimiento = date(hoy.year + anios_vigencia, hoy.month, hoy.day)

    tarjeta = TarTarjeta(
        id_tarjeta=new_uuid7(),
        pan_token=pan_token,
        bin=pan[:6],
        ultimos4=pan[-4:],
        id_cliente=id_cliente,
        tipo_tarjeta=tipo_tarjeta,
        fecha_emision=hoy,
        fecha_vencimiento=vencimiento,
        estado="ACTIVA",
        fecha_creacion=datetime.now(),
    )
    db.add(tarjeta)
    db.flush()

    db.add(
        TarTarjetaCuenta(
            id_tarjeta=tarjeta.id_tarjeta,
            num_cuenta=cuenta.num_cuenta,
            es_principal=es_principal,
            habilitada_atm=habilitada_atm,
            fecha_vinculacion=datetime.now(),
        )
    )

    auditoria.registrar_evento(
        db,
        modulo="CORE",
        entidad="tar_tarjeta",
        id_entidad=tarjeta.id_tarjeta,
        accion="CREAR_TARJETA",
        actor=actor,
        detalle={
            "id_cliente": id_cliente,
            "num_cuenta": num_cuenta,
            "tipo_tarjeta": tipo_tarjeta,
            "ultimos4": tarjeta.ultimos4,
        },
        correlation_id=correlation_id,
    )
    db.commit()
    return tarjeta


def cambiar_estado_tarjeta(
    db: Session,
    id_tarjeta: str,
    *,
    nuevo_estado: str,
    motivo: str,
    origen: str = "BANCO",
    actor: str = "sistema",
    correlation_id: str | None = None,
) -> TarTarjeta:
    """RF-TAR-06 (acción BLOQUEAR_TARJETA): bloqueo/anulación con
    historial inmutable de estados."""
    tarjeta = obtener_tarjeta(db, id_tarjeta)
    if nuevo_estado not in ESTADOS_TARJETA:
        raise ValidationError(
            "ESTADO_TARJETA_INVALIDO",
            f"Estado {nuevo_estado} no admitido. Opciones: {', '.join(ESTADOS_TARJETA)}.",
        )
    anterior = tarjeta.estado
    tarjeta.estado = nuevo_estado

    db.add(
        TarHistorialEstado(
            id_historial=new_uuid7(),
            id_tarjeta=id_tarjeta,
            estado_anterior=anterior,
            estado_nuevo=nuevo_estado,
            motivo=motivo[:120],
            origen=origen,
            fecha_hora=datetime.now(),
        )
    )
    auditoria.registrar_evento(
        db,
        modulo="CORE",
        entidad="tar_tarjeta",
        id_entidad=id_tarjeta,
        accion="BLOQUEAR_TARJETA" if nuevo_estado == "BLOQUEADA" else "CAMBIAR_ESTADO_TARJETA",
        actor=actor,
        detalle={
            "estado_anterior": anterior,
            "estado_nuevo": nuevo_estado,
            "motivo": motivo,
        },
        correlation_id=correlation_id,
    )
    db.commit()
    return tarjeta


def vista_publica(tarjeta: TarTarjeta) -> dict:
    """Vista segura: nunca expone pan_token completo ni PAN."""
    return {
        "id_tarjeta": tarjeta.id_tarjeta,
        "bin": tarjeta.bin,
        "ultimos4": tarjeta.ultimos4,
        "id_cliente": tarjeta.id_cliente,
        "tipo_tarjeta": tarjeta.tipo_tarjeta,
        "fecha_emision": tarjeta.fecha_emision,
        "fecha_vencimiento": tarjeta.fecha_vencimiento,
        "estado": tarjeta.estado,
    }
