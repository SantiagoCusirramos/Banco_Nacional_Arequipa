from fastapi import APIRouter, Depends, Request

from CUENTAS.core_client import CoreClient
from CUENTAS.dependencies import ContextoOperacion, contexto_operacion, correlation_id, get_core_client
from CUENTAS.respuestas import exito
from CUENTAS.schemas.cuentas import (
    AbrirCuentaIn, CuentaOut, MovimientoOut, OperacionIn, TransferenciaIn, TransferenciaOut,
)
from CUENTAS.services import cuentas as svc

router = APIRouter(prefix="/api/v1/cuentas", tags=["Cuentas"])


def _msg_replay(replay: bool) -> str:
    if replay:
        return "Operacion ya procesada antes (idempotencia), se devuelve el resultado original"
    return "Operacion ejecutada satisfactoriamente"


@router.post("/apertura", status_code=201)
def abrir_cuenta(request: Request, datos: AbrirCuentaIn, core: CoreClient = Depends(get_core_client),
                 cid: str = Depends(correlation_id)):
    cuenta = CuentaOut(**svc.abrir_cuenta(core, datos, cid))
    return exito(request, cuenta.model_dump(mode="json"), 201, "Cuenta de ahorros creada")


@router.get("/consolidada/{id_cliente}")
def cuentas_del_cliente(request: Request, id_cliente: str, core: CoreClient = Depends(get_core_client),
                        cid: str = Depends(correlation_id)):
    cuentas = [CuentaOut(**c).model_dump(mode="json") for c in svc.cuentas_del_cliente(core, id_cliente, cid)]
    return exito(request, cuentas)


@router.get("/{num_cuenta}")
def ver_cuenta(request: Request, num_cuenta: str, core: CoreClient = Depends(get_core_client),
               cid: str = Depends(correlation_id)):
    cuenta = CuentaOut(**svc.ver_cuenta(core, num_cuenta, cid))
    return exito(request, cuenta.model_dump(mode="json"))


@router.post("/deposito", status_code=201)
def depositar(request: Request, datos: OperacionIn, core: CoreClient = Depends(get_core_client),
              ctx: ContextoOperacion = Depends(contexto_operacion)):
    mov = MovimientoOut(**svc.operar(core, "DEPOSITO", datos, ctx.id_canal, ctx.idempotency_key, ctx.cid))
    return exito(request, mov.model_dump(mode="json"), 201, _msg_replay(mov.replay))


@router.post("/retiro", status_code=201)
def retirar(request: Request, datos: OperacionIn, core: CoreClient = Depends(get_core_client),
            ctx: ContextoOperacion = Depends(contexto_operacion)):
    mov = MovimientoOut(**svc.operar(core, "RETIRO", datos, ctx.id_canal, ctx.idempotency_key, ctx.cid))
    return exito(request, mov.model_dump(mode="json"), 201, _msg_replay(mov.replay))


@router.post("/transferencia", status_code=201)
def transferir(request: Request, datos: TransferenciaIn, core: CoreClient = Depends(get_core_client),
               ctx: ContextoOperacion = Depends(contexto_operacion)):
    res = TransferenciaOut(**svc.transferir(core, datos, ctx.id_canal, ctx.idempotency_key, ctx.cid))
    return exito(request, res.model_dump(mode="json"), 201, _msg_replay(res.replay))
