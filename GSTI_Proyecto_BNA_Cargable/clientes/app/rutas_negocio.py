"""Operaciones OFICIALES del módulo de Clientes (JSON). El Bus las invoca con X-Service-Token = CLIENTES_TOKEN.

SEPARADAS de las rutas del panel (/panel/*): el panel entra por el Bus y llega aquí, sin ciclos de llamadas.
"""
from fastapi import APIRouter, Depends, Request

from shared.comun import requerir_token
from shared.esquemas import DatosCliente, ValidarBiometriaIn, ValidarDocumentoIn

from . import config, negocio

router = APIRouter(prefix="/clientes", tags=["Operaciones de negocio"], dependencies=[Depends(requerir_token(config.CLIENTES_TOKEN))])


@router.post("/registrar", status_code=201, summary="1. Registrar cliente")
async def registrar(datos: DatosCliente):
    return await negocio.registrar(datos)


@router.post("/validar-documento", summary="2. Validar cliente por documento")
async def validar_documento(datos: ValidarDocumentoIn):
    return await negocio.validar_documento(datos)


@router.post("/validar-biometria", summary="3. Validar cliente por biometría (facial o dactilar)")
async def validar_biometria(datos: ValidarBiometriaIn):
    return await negocio.validar_biometria(datos)
