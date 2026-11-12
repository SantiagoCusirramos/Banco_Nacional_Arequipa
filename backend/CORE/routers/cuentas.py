"""Routers de cuentas — VER/CREAR/MODIFICAR_CUENTA.

Exigen token y permiso. El actor sale siempre del token: el campo `actor` del
cuerpo se ignora.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from CORE.dependencies import db_session, requiere_permiso
from CORE.models import UsuarioSistema
from CORE.schemas.cuentas import (
    CuentaCrear,
    CuentaModificar,
    CuentaRespuesta,
    TitularRespuesta,
)
from CORE.services import cuentassvc

router = APIRouter(prefix="/cuentas", tags=["Cuentas"])


def _a_respuesta(resumen: dict) -> CuentaRespuesta:
    return CuentaRespuesta(
        num_cuenta=resumen["num_cuenta"],
        moneda=resumen["moneda"],
        regimen=resumen["regimen"],
        estado_cuenta=resumen["estado_cuenta"],
        saldo_contable=resumen["saldo_contable"],
        saldo_disponible=resumen["saldo_disponible"],
        saldo_retenido=resumen["saldo_retenido"],
        fecha_apertura=resumen["fecha_apertura"],
        id_agencia=resumen["id_agencia"],
        id_producto_ahorro=resumen["id_producto_ahorro"],
        titulares=[TitularRespuesta(**t) for t in resumen["titulares"]],
    )


@router.get(
    "/cliente/{id_cliente}", response_model=list[CuentaRespuesta],
    dependencies=[Depends(requiere_permiso("VER_CUENTA"))],
)
def cuentas_del_cliente(id_cliente: str, db: Session = Depends(db_session)):
    cuentas = cuentassvc.cuentas_del_cliente(db, id_cliente)
    return [_a_respuesta(cuentassvc.resumen_cuenta(db, c.num_cuenta)) for c in cuentas]


@router.get(
    "/{num_cuenta}", response_model=CuentaRespuesta,
    dependencies=[Depends(requiere_permiso("VER_CUENTA"))],
)
def ver_cuenta(num_cuenta: str, db: Session = Depends(db_session)):
    return _a_respuesta(cuentassvc.resumen_cuenta(db, num_cuenta))


@router.post("", response_model=CuentaRespuesta, status_code=status.HTTP_201_CREATED)
def crear_cuenta(
    payload: CuentaCrear,
    db: Session = Depends(db_session),
    usuario: UsuarioSistema = Depends(requiere_permiso("CREAR_CUENTA")),
):
    titulares = [t.model_dump() for t in payload.titulares] if payload.titulares else None
    cuenta = cuentassvc.abrir_cuenta(
        db,
        id_cliente=payload.id_cliente,
        id_producto_ahorro=payload.id_producto_ahorro,
        id_agencia=payload.id_agencia,
        regimen=payload.regimen,
        titulares=titulares,
        actor=usuario.username,
        correlation_id=payload.correlation_id,
    )
    return _a_respuesta(cuentassvc.resumen_cuenta(db, cuenta.num_cuenta))


@router.patch("/{num_cuenta}", response_model=CuentaRespuesta)
def modificar_cuenta(
    num_cuenta: str,
    payload: CuentaModificar,
    db: Session = Depends(db_session),
    usuario: UsuarioSistema = Depends(requiere_permiso("MODIFICAR_CUENTA")),
):
    cuenta = cuentassvc.modificar_cuenta(
        db,
        num_cuenta,
        estado_cuenta=payload.estado_cuenta,
        actor=usuario.username,
        correlation_id=payload.correlation_id,
    )
    return _a_respuesta(cuentassvc.resumen_cuenta(db, cuenta.num_cuenta))
