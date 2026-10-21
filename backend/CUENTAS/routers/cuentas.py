from fastapi import APIRouter, Depends, status

from CUENTAS.core_client import CoreClient
from CUENTAS.dependencies import correlation_id, get_core_client, idempotency_key
from CUENTAS.schemas.cuentas import (
    AbrirCuentaIn, CuentaOut, MovimientoOut, OperacionIn, TransferenciaIn, TransferenciaOut,
)
from CUENTAS.services import cuentas as svc

router = APIRouter(prefix="/cuentas", tags=["Cuentas"])


@router.post("", response_model=CuentaOut, status_code=status.HTTP_201_CREATED)
def abrir_cuenta(datos: AbrirCuentaIn, core: CoreClient = Depends(get_core_client),
                 cid: str = Depends(correlation_id)):
    return svc.abrir_cuenta(core, datos, cid)


@router.get("/cliente/{id_cliente}", response_model=list[CuentaOut])
def cuentas_del_cliente(id_cliente: str, core: CoreClient = Depends(get_core_client),
                        cid: str = Depends(correlation_id)):
    return svc.cuentas_del_cliente(core, id_cliente, cid)


@router.get("/{num_cuenta}", response_model=CuentaOut)
def ver_cuenta(num_cuenta: str, core: CoreClient = Depends(get_core_client),
               cid: str = Depends(correlation_id)):
    return svc.ver_cuenta(core, num_cuenta, cid)


@router.post("/{num_cuenta}/depositos", response_model=MovimientoOut,
             status_code=status.HTTP_201_CREATED)
def depositar(num_cuenta: str, datos: OperacionIn, core: CoreClient = Depends(get_core_client),
              cid: str = Depends(correlation_id), key: str = Depends(idempotency_key)):
    return svc.operar(core, "DEPOSITO", num_cuenta, datos, key, cid)


@router.post("/{num_cuenta}/retiros", response_model=MovimientoOut,
             status_code=status.HTTP_201_CREATED)
def retirar(num_cuenta: str, datos: OperacionIn, core: CoreClient = Depends(get_core_client),
            cid: str = Depends(correlation_id), key: str = Depends(idempotency_key)):
    return svc.operar(core, "RETIRO", num_cuenta, datos, key, cid)


@router.post("/{num_cuenta}/transferencias", response_model=TransferenciaOut,
             status_code=status.HTTP_201_CREATED)
def transferir(num_cuenta: str, datos: TransferenciaIn, core: CoreClient = Depends(get_core_client),
               cid: str = Depends(correlation_id), key: str = Depends(idempotency_key)):
    return svc.transferir(core, num_cuenta, datos, key, cid)
