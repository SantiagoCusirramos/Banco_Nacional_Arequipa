"""Cuentas de ahorro — RF-COR-03, RF-COR-04, RF-COR-18
(acciones VER/CREAR/MODIFICAR_CUENTA)."""

import secrets
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from CORE.exceptions import ConflictError, NotFoundError, ValidationError
from CORE.models import (
    Agencia,
    Cliente,
    ClienteCuenta,
    CuentaAhorro,
    ProductoAhorro,
)
from CORE.services import auditoria
from CORE.utils.ids import new_uuid7
from CORE.utils.money import D

ESTADOS_MODIFICABLES = ("ACTIVA", "INACTIVA", "BLOQUEADA", "EMBARGO")
REGIMENES = ("LIBRE", "PROGRAMADO", "INFANTIL", "CTS", "A_PLAZO")
ROLES_TITULAR = ("TITULAR", "MANCOMUNADO", "APODERADO", "TUTOR", "BENEFICIARIO")


def generar_num_cuenta() -> str:
    """Número de cuenta de 14 dígitos: 20 + YYMMDD + 6 aleatorios."""
    hoy = datetime.now()
    return f"20{yymmdd(hoy)}{secrets.randbelow(10**6):06d}"


def yymmdd(fecha: datetime) -> str:
    return f"{fecha.year % 100:02d}{fecha.month:02d}{fecha.day:02d}"


def obtener_cuenta(db: Session, num_cuenta: str) -> CuentaAhorro:
    cuenta = db.get(CuentaAhorro, num_cuenta)
    if cuenta is None:
        raise NotFoundError("CUENTA_NO_ENCONTRADA", f"Cuenta {num_cuenta} no existe.")
    return cuenta


def cuentas_del_cliente(db: Session, id_cliente: str) -> list[CuentaAhorro]:
    return (
        db.query(CuentaAhorro)
        .join(ClienteCuenta, ClienteCuenta.num_cuenta == CuentaAhorro.num_cuenta)
        .filter(ClienteCuenta.id_cliente == id_cliente)
        .all()
    )


def abrir_cuenta(
    db: Session,
    *,
    id_cliente: str,
    id_producto_ahorro: str,
    id_agencia: str,
    regimen: str = "LIBRE",
    titulares: list[dict] | None = None,
    actor: str = "sistema",
    correlation_id: str | None = None,
) -> CuentaAhorro:
    """RF-COR-03: abre cuenta vinculada a uno o más clientes, con moneda
    y producto, inicializada en saldo cero. RGN-16: una cuenta
    mancomunada registra todos sus titulares."""
    if db.get(Cliente, id_cliente) is None:
        raise NotFoundError("CLIENTE_NO_ENCONTRADO", f"Cliente {id_cliente} no existe.")
    producto = db.get(ProductoAhorro, id_producto_ahorro)
    if producto is None or not producto.activo:
        raise NotFoundError(
            "PRODUCTO_NO_ENCONTRADO",
            f"Producto de ahorro {id_producto_ahorro} inexistente o inactivo.",
        )
    if db.get(Agencia, id_agencia) is None:
        raise NotFoundError("AGENCIA_NO_ENCONTRADA", f"Agencia {id_agencia} no existe.")
    if regimen not in REGIMENES:
        raise ValidationError(
            "REGIMEN_INVALIDO",
            f"Régimen {regimen} no admitido. Opciones: {', '.join(REGIMENES)}.",
        )

    vinculos = titulares or [{"id_cliente": id_cliente, "rol_titular": "TITULAR"}]
    roles = {v.get("rol_titular", "TITULAR") for v in vinculos}
    if "MANCOMUNADO" in roles and len(vinculos) < 2:
        raise ValidationError(
            "CUENTA_MANCOMUNADA_INCOMPLETA",
            "Una cuenta mancomunada requiere al menos dos titulares (RGN-16).",
        )

    cuenta = None
    for _ in range(5):
        num = generar_num_cuenta()
        if db.get(CuentaAhorro, num) is not None:
            continue
        cuenta = CuentaAhorro(
            num_cuenta=num,
            moneda=producto.moneda,
            regimen=regimen,
            saldo_contable=D("0"),
            saldo_disponible=D("0"),
            saldo_retenido=D("0"),
            estado_cuenta="ACTIVA",
            fecha_apertura=datetime.now(),
            id_agencia=id_agencia,
            id_producto_ahorro=id_producto_ahorro,
        )
        db.add(cuenta)
        try:
            db.flush()
            break
        except IntegrityError:
            db.rollback()
            cuenta = None
    if cuenta is None:
        raise ConflictError("NUM_CUENTA_AGOTADO", "No se pudo generar un número de cuenta único.")

    for v in vinculos:
        rol = v.get("rol_titular", "TITULAR")
        if rol not in ROLES_TITULAR:
            raise ValidationError(
                "ROL_TITULAR_INVALIDO",
                f"Rol {rol} no admitido. Opciones: {', '.join(ROLES_TITULAR)}.",
            )
        db.add(
            ClienteCuenta(
                num_cuenta=cuenta.num_cuenta,
                id_cliente=v["id_cliente"],
                rol_titular=rol,
                fecha_vinculacion=datetime.now(),
            )
        )

    auditoria.registrar_evento(
        db,
        modulo="CORE",
        entidad="cuenta_ahorro",
        id_entidad=cuenta.num_cuenta,
        accion="CREAR_CUENTA",
        actor=actor,
        detalle={
            "id_cliente": id_cliente,
            "producto": id_producto_ahorro,
            "moneda": producto.moneda,
            "regimen": regimen,
            "titulares": len(vinculos),
        },
        correlation_id=correlation_id,
    )
    db.commit()
    return cuenta


def modificar_cuenta(
    db: Session,
    num_cuenta: str,
    *,
    estado_cuenta: str | None = None,
    actor: str = "sistema",
    correlation_id: str | None = None,
) -> CuentaAhorro:
    """RF-COR-18: expone y actualiza el estado de la cuenta
    (activa, bloqueada, observada/inactiva, embargo)."""
    cuenta = obtener_cuenta(db, num_cuenta)
    if estado_cuenta is not None:
        if estado_cuenta not in ESTADOS_MODIFICABLES:
            raise ValidationError(
                "ESTADO_CUENTA_INVALIDO",
                f"Estado {estado_cuenta} no admitido. "
                f"Opciones: {', '.join(ESTADOS_MODIFICABLES)}.",
            )
        anterior = cuenta.estado_cuenta
        cuenta.estado_cuenta = estado_cuenta
        auditoria.registrar_evento(
            db,
            modulo="CORE",
            entidad="cuenta_ahorro",
            id_entidad=num_cuenta,
            accion="MODIFICAR_CUENTA",
            actor=actor,
            detalle={"estado_anterior": anterior, "estado_nuevo": estado_cuenta},
            correlation_id=correlation_id,
        )
        db.commit()
    return cuenta


def resumen_cuenta(db: Session, num_cuenta: str) -> dict:
    """RF-COR-04: saldo real y disponible en tiempo real."""
    cuenta = obtener_cuenta(db, num_cuenta)
    titulares = (
        db.query(ClienteCuenta).filter(ClienteCuenta.num_cuenta == num_cuenta).all()
    )
    return {
        "num_cuenta": cuenta.num_cuenta,
        "moneda": cuenta.moneda,
        "regimen": cuenta.regimen,
        "estado_cuenta": cuenta.estado_cuenta,
        "saldo_contable": cuenta.saldo_contable,
        "saldo_disponible": cuenta.saldo_disponible,
        "saldo_retenido": cuenta.saldo_retenido,
        "fecha_apertura": cuenta.fecha_apertura,
        "id_producto_ahorro": cuenta.id_producto_ahorro,
        "id_agencia": cuenta.id_agencia,
        "titulares": [
            {"id_cliente": t.id_cliente, "rol_titular": t.rol_titular}
            for t in titulares
        ],
    }
