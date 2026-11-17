
import httpx

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.config import SERVICIOS

router = APIRouter(prefix="/api", tags=["Integración"])

CABECERAS_PERMITIDAS = {
    "authorization",
    "content-type",
    "accept",
    "idempotency-key",
    "x-correlation-id",
}


@router.api_route(
    "/{modulo}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def enrutar_solicitud(
    modulo: str,
    path: str,
    request: Request,
):
    destino = SERVICIOS.get(modulo.lower())

    if not destino:
        raise HTTPException(
            status_code=404,
            detail="Módulo no registrado en el BNA",
        )

    url = f"{destino.rstrip('/')}/{path}"

    cabeceras = {
        nombre: valor
        for nombre, valor in request.headers.items()
        if nombre.lower() in CABECERAS_PERMITIDAS
    }

    cabeceras.setdefault(
        "X-Correlation-ID",
        "bna-request",
    )

    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=False,
        ) as client:
            respuesta = await client.request(
                method=request.method,
                url=url,
                params=list(
                    request.query_params.multi_items()
                ),
                content=await request.body(),
                headers=cabeceras,
            )

        cabeceras_respuesta = {}

        if "content-type" in respuesta.headers:
            cabeceras_respuesta["content-type"] = (
                respuesta.headers["content-type"]
            )

        return Response(
            content=respuesta.content,
            status_code=respuesta.status_code,
            headers=cabeceras_respuesta,
        )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Tiempo de espera agotado en el servicio destino",
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="No se pudo conectar con el servicio destino",
        )
