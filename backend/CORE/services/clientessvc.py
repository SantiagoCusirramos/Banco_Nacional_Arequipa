"""Maestro de clientes — RF-COR-01 / RF-COR-02 (acciones VER/CREAR/
MODIFICAR_CLIENTE).

RGN-05: un mismo documento de identidad no puede corresponder a dos
clientes; el alta duplicada devuelve el identificador existente.
"""

from datetime import date, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from CORE.exceptions import ConflictError, NotFoundError
from CORE.models import Cliente, TipoDocumento
from CORE.services import auditoria
from CORE.utils.ids import new_uuid7


def buscar_por_documento(
    db: Session, cod_tipo_documento: str, numero_documento: str
) -> Cliente | None:
    return (
        db.query(Cliente)
        .filter(
            Cliente.cod_tipo_documento == cod_tipo_documento,
            Cliente.numero_documento == numero_documento,
        )
        .first()
    )


def obtener_cliente(db: Session, id_cliente: str) -> Cliente:
    cliente = db.get(Cliente, id_cliente)
    if cliente is None:
        raise NotFoundError("CLIENTE_NO_ENCONTRADO", f"Cliente {id_cliente} no existe.")
    return cliente


def listar_clientes(
    db: Session, *, documento: str | None = None, estado: str | None = None,
    limite: int = 50, offset: int = 0,
) -> list[Cliente]:
    q = db.query(Cliente)
    if documento:
        q = q.filter(Cliente.numero_documento.contains(documento))
    if estado:
        q = q.filter(Cliente.estado_cliente == estado)
    return q.order_by(Cliente.fecha_registro.desc()).offset(offset).limit(limite).all()


def crear_cliente(
    db: Session,
    *,
    cod_tipo_documento: str,
    numero_documento: str,
    nombres: str,
    apellido_paterno: str,
    apellido_materno: str | None = None,
    fecha_nacimiento: date | None = None,
    numero_celular: str,
    correo_electronico: str | None = None,
    actor: str = "sistema",
    correlation_id: str | None = None,
) -> tuple[Cliente, bool]:
    """Alta de cliente. Devuelve (cliente, duplicado).

    RF-COR-02: si el documento ya existe se devuelve el cliente existente
    con `duplicado=True` y SIN crear uno nuevo (RGN-05).
    """
    if db.get(TipoDocumento, cod_tipo_documento) is None:
        raise NotFoundError(
            "TIPO_DOCUMENTO_NO_ENCONTRADO",
            f"Tipo de documento {cod_tipo_documento} no existe en el catálogo.",
        )

    existente = buscar_por_documento(db, cod_tipo_documento, numero_documento)
    if existente is not None:
        auditoria.registrar_evento(
            db,
            modulo="CORE",
            entidad="cliente",
            id_entidad=existente.id_cliente,
            accion="CREAR_CLIENTE_DUPLICADO",
            actor=actor,
            detalle={
                "cod_tipo_documento": cod_tipo_documento,
                "numero_documento": numero_documento,
                "resultado": "DEVUELTO_EXISTENTE",
            },
            correlation_id=correlation_id,
        )
        db.commit()
        return existente, True

    cliente = Cliente(
        id_cliente=new_uuid7(),
        cod_tipo_documento=cod_tipo_documento,
        numero_documento=numero_documento,
        nombres=nombres,
        apellido_paterno=apellido_paterno,
        apellido_materno=apellido_materno,
        fecha_nacimiento=fecha_nacimiento,
        numero_celular=numero_celular,
        correo_electronico=correo_electronico,
        estado_cliente="ACTIVO",
        fecha_registro=datetime.now(),
    )
    db.add(cliente)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "CLIENTE_DUPLICADO",
            "Ya existe un cliente con ese documento o correo.",
        ) from exc

    auditoria.registrar_evento(
        db,
        modulo="CORE",
        entidad="cliente",
        id_entidad=cliente.id_cliente,
        accion="CREAR_CLIENTE",
        actor=actor,
        detalle={
            "cod_tipo_documento": cod_tipo_documento,
            "numero_documento": numero_documento,
            "resultado": "CREADO",
        },
        correlation_id=correlation_id,
    )
    db.commit()
    return cliente, False


def modificar_cliente(
    db: Session,
    id_cliente: str,
    *,
    numero_celular: str | None = None,
    correo_electronico: str | None = None,
    estado_cliente: str | None = None,
    nombres: str | None = None,
    apellido_paterno: str | None = None,
    apellido_materno: str | None = None,
    actor: str = "sistema",
    correlation_id: str | None = None,
) -> Cliente:
    """Actualización parcial de datos del cliente (RF-COR-01)."""
    cliente = obtener_cliente(db, id_cliente)
    cambios: dict = {}

    campos = {
        "numero_celular": numero_celular,
        "correo_electronico": correo_electronico,
        "estado_cliente": estado_cliente,
        "nombres": nombres,
        "apellido_paterno": apellido_paterno,
        "apellido_materno": apellido_materno,
    }
    for campo, valor in campos.items():
        if valor is not None and getattr(cliente, campo) != valor:
            cambios[campo] = {"anterior": getattr(cliente, campo), "nuevo": valor}
            setattr(cliente, campo, valor)

    if cambios:
        auditoria.registrar_evento(
            db,
            modulo="CORE",
            entidad="cliente",
            id_entidad=cliente.id_cliente,
            accion="MODIFICAR_CLIENTE",
            actor=actor,
            detalle={"cambios": cambios},
            correlation_id=correlation_id,
        )
        db.commit()
    return cliente
