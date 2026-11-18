"""CR-INT-01: las dos rutas que consume Solicitud de Crédito (SOL).

Siguen la propuesta v2 de SOL (Documents/solicitud-credito/CONTRATOS_HTTP_V2.md y
backend/SOL/integrations.py): el cuerpo es el objeto o la lista sin sobre ITIL-02,
un 404 significa "no hay referencia" y el token es de servicio, no de una persona.
Configuración de SOL para usarlas, cuando haya Bus:
    SOL_CAP_SEARCH_PATH=/cap/references/search   (POST; el texto buscado va en el cuerpo)
    SOL_CAP_REFERENCE_PATH=/cap/references/{idCliente}
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from CAPTACION.core_client import CoreDb
from CAPTACION.dependencies import get_core, servicio_sol
from CAPTACION.errores import CaptacionError
from CAPTACION.schemas import ReferenciasBuscar
from CAPTACION.services import captacion as svc

router = APIRouter(prefix="/cap", tags=["CR-INT-01 (Solicitud de Crédito)"], dependencies=[Depends(servicio_sol)])


# POST y no GET: el texto buscado suele ser un documento, y en la consulta quedaría en los
# registros de acceso del Bus y de cada servicio por el que pasa (P-1).
@router.post("/references/search", summary="Búsqueda acotada de referencias (hasta 50)")
def buscar(request: Request, datos: ReferenciasBuscar, core: CoreDb = Depends(get_core)) -> list[dict]:
    try:
        return svc.buscar_referencias(core, datos.search, datos.limit, request.state.uuid_transaccion)
    except CaptacionError as exc:
        raise HTTPException(503, "Búsqueda no disponible.") from exc


@router.get("/references/{id_cliente}", summary="Referencia vigente de un cliente")
def referencia(request: Request, id_cliente: str = Path(max_length=36), core: CoreDb = Depends(get_core)) -> dict:
    try:
        datos = svc.referencia(core, id_cliente, request.state.uuid_transaccion)
    except CaptacionError as exc:
        # SOL trata 503 como dependencia caída y reintenta; no se le envían detalles internos.
        raise HTTPException(503, "Referencia no disponible.") from exc
    if datos is None:
        raise HTTPException(404, "Referencia no encontrada.")
    return datos
