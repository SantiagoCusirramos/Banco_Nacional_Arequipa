from fastapi import APIRouter, Depends, Request

from TARJETAS.core_client import CoreClient
from TARJETAS.dependencies import autorizacion, correlation_id, get_core_client, idempotency_key
from TARJETAS.respuestas import exito
from TARJETAS.schemas.tarjetas import BloqueoIn, EmisionIn, EstadoIn, TarjetaOut
from TARJETAS.services import tarjetas as svc

router = APIRouter(prefix="/api/v1/tarjetas", tags=["Tarjetas"])


def _salida(tarjeta: dict) -> dict:
    return TarjetaOut(**tarjeta).model_dump(mode="json")


@router.get("/cliente/{cod_cliente}")
def tarjetas_del_cliente(request: Request, cod_cliente: str, core: CoreClient = Depends(get_core_client),
                         cid: str = Depends(correlation_id), token: str = Depends(autorizacion)):
    tarjetas = [_salida(t) for t in svc.tarjetas_del_cliente(core, cod_cliente, cid, token)]
    return exito(request, tarjetas)


@router.post("/emision", status_code=201)
def emitir(request: Request, datos: EmisionIn, core: CoreClient = Depends(get_core_client),
           cid: str = Depends(correlation_id), token: str = Depends(autorizacion),
           key: str = Depends(idempotency_key)):
    tarjeta, repetida = svc.emitir(core, datos, key, cid, token)
    if repetida:
        mensaje = "Emision ya procesada antes (idempotencia), se devuelve la tarjeta original"
    else:
        mensaje = "Tarjeta emitida, pendiente de activación"
    return exito(request, _salida(tarjeta), 201, mensaje)


@router.get("/{id_tarjeta}")
def ver_tarjeta(request: Request, id_tarjeta: str, core: CoreClient = Depends(get_core_client),
                cid: str = Depends(correlation_id), token: str = Depends(autorizacion)):
    return exito(request, _salida(svc.ver_tarjeta(core, id_tarjeta, cid, token)))


@router.post("/{id_tarjeta}/bloqueo")
def bloquear(request: Request, id_tarjeta: str, datos: BloqueoIn, core: CoreClient = Depends(get_core_client),
             cid: str = Depends(correlation_id), token: str = Depends(autorizacion)):
    tarjeta = _salida(svc.bloquear(core, id_tarjeta, datos, cid, token))
    return exito(request, tarjeta, message="Tarjeta bloqueada")


@router.post("/{id_tarjeta}/estado")
def cambiar_estado(request: Request, id_tarjeta: str, datos: EstadoIn, core: CoreClient = Depends(get_core_client),
                   cid: str = Depends(correlation_id), token: str = Depends(autorizacion)):
    tarjeta = _salida(svc.cambiar_estado(core, id_tarjeta, datos, cid, token))
    return exito(request, tarjeta, message=f"Tarjeta en estado {tarjeta['estado_tarjeta']}")
