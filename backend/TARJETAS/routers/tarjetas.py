from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request

from TARJETAS.core_client import CoreClient
from TARJETAS.dependencies import autorizacion, correlation_id, get_core_client, idempotency_key
from TARJETAS.respuestas import exito
from TARJETAS.schemas.tarjetas import (
    AutorizacionIn, AutorizacionOut, BloqueoIn, ConfirmacionIn, CredencialIn, EmisionIn, EstadoIn, ExtornoIn, TarjetaOut,
    TipoCredencial, ValidacionIn, ValidacionOut,
)
from TARJETAS.services import tarjetas as svc

router = APIRouter(prefix="/api/v1/tarjetas", tags=["Tarjetas"])

# El mismo formato que exige COREDB: un código inválido se rechaza aquí, sin llamarlo.
CodCliente = Annotated[str, Path(min_length=1, max_length=12, pattern=r"^[A-Za-z0-9]+$")]


def _salida(tarjeta: dict) -> dict:
    return TarjetaOut(**tarjeta).model_dump(mode="json")


@router.get("/cliente/{cod_cliente}")
def tarjetas_del_cliente(request: Request, cod_cliente: CodCliente, core: CoreClient = Depends(get_core_client),
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


def _autorizacion(autorizacion: dict) -> dict:
    return AutorizacionOut(**autorizacion).model_dump(mode="json")


def _mensaje_autorizacion(autorizacion: dict) -> str:
    if autorizacion["estado_autorizacion"] == "AUTORIZADA":
        return "Operación autorizada"
    if autorizacion["estado_autorizacion"] == "DISPENSADA":
        return "Operación confirmada"
    if autorizacion["estado_autorizacion"] == "EXTORNADA":
        return "Operación extornada"
    return f"Operación rechazada (código {autorizacion['codigo_respuesta']})"


@router.get("/autorizaciones/{uuid_autorizacion}")
def ver_autorizacion(request: Request, uuid_autorizacion: str, core: CoreClient = Depends(get_core_client),
                     cid: str = Depends(correlation_id), token: str = Depends(autorizacion)):
    return exito(request, _autorizacion(svc.ver_autorizacion(core, uuid_autorizacion, cid, token)))


@router.post("/autorizaciones/{uuid_autorizacion}/extorno")
def extornar(request: Request, uuid_autorizacion: str, datos: ExtornoIn, core: CoreClient = Depends(get_core_client),
             cid: str = Depends(correlation_id), token: str = Depends(autorizacion)):
    """Libera el saldo retenido y el tope del día (RN-ATM-003). Repetirlo responde lo mismo."""
    resultado = _autorizacion(svc.extornar(core, uuid_autorizacion, datos, cid, token))
    return exito(request, resultado, message=_mensaje_autorizacion(resultado))


@router.post("/autorizaciones/{uuid_autorizacion}/confirmacion")
def confirmar(request: Request, uuid_autorizacion: str, datos: ConfirmacionIn, core: CoreClient = Depends(get_core_client),
              cid: str = Depends(correlation_id), token: str = Depends(autorizacion)):
    """Confirma una autorización retenida: registra el movimiento real y pasa a DISPENSADA.
    La llave de idempotencia es obligatoria; repetirla devuelve el mismo resultado sin
    segundo débito. El canal o terminal deben coincidir con la autorización."""
    resultado = _autorizacion(svc.confirmar_autorizacion(core, uuid_autorizacion, datos, cid, token))
    return exito(request, resultado, message=_mensaje_autorizacion(resultado))


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


@router.post("/{id_tarjeta}/autorizaciones", status_code=201)
def autorizar(request: Request, id_tarjeta: str, datos: AutorizacionIn, core: CoreClient = Depends(get_core_client),
              cid: str = Depends(correlation_id), token: str = Depends(autorizacion),
              key: str = Depends(idempotency_key)):
    """Autoriza un débito con la tarjeta o registra su rechazo. Una regla que no se cumple (saldo,
    tope, tarjeta, canal) responde 201 con `aprobada: false` y el código de respuesta."""
    resultado = _autorizacion(svc.autorizar(core, id_tarjeta, datos, key, cid, token))
    return exito(request, resultado, 201, _mensaje_autorizacion(resultado))


@router.put("/{id_tarjeta}/credenciales/{tipo}")
def registrar_credencial(request: Request, id_tarjeta: str, tipo: TipoCredencial, datos: CredencialIn,
                         core: CoreClient = Depends(get_core_client), cid: str = Depends(correlation_id),
                         token: str = Depends(autorizacion)):
    svc.registrar_credencial(core, id_tarjeta, tipo, datos, cid, token)
    return exito(request, None, message="Clave registrada")


@router.post("/{id_tarjeta}/credenciales/{tipo}/validacion")
def validar_credencial(request: Request, id_tarjeta: str, tipo: TipoCredencial, datos: ValidacionIn,
                       core: CoreClient = Depends(get_core_client), cid: str = Depends(correlation_id),
                       token: str = Depends(autorizacion)):
    """Una clave equivocada responde 200 con FALLIDO; al tercer fallo seguido la tarjeta queda
    bloqueada (RN-TAR-004)."""
    resultado = ValidacionOut(**svc.validar_credencial(core, id_tarjeta, tipo, datos, cid, token))
    mensaje = "Clave correcta" if resultado.resultado == "EXITOSO" else "Clave incorrecta"
    return exito(request, resultado.model_dump(mode="json"), message=mensaje)
