"""CR-INT-01: las dos rutas que consume Solicitud de Crédito (SOL).

Siguen la propuesta v2 de SOL (Documents/solicitud-credito/CONTRATOS_HTTP_V2.md y
backend/SOL/integrations.py): el cuerpo es el objeto o la lista sin sobre ITIL-02,
un 404 significa "no hay referencia" y el token es de servicio, no de una persona.
Configuración de SOL para usarlas, cuando haya Bus:
    SOL_CAP_SEARCH_PATH=/cap/references
    SOL_CAP_REFERENCE_PATH=/cap/references/{idCliente}
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from sqlalchemy.orm import Session

from CAPTACION.core_client import CoreDb
from CAPTACION.database import db_session
from CAPTACION.dependencies import get_core, servicio_sol
from CAPTACION.errores import CaptacionError
from CAPTACION.services import captacion as svc

router = APIRouter(prefix="/cap", tags=["CR-INT-01 (Solicitud de Crédito)"], dependencies=[Depends(servicio_sol)])


@router.get("/references", summary="Búsqueda acotada de referencias (hasta 50)")
def buscar(search: str = Query(default="", max_length=100), limit: int = Query(default=50, ge=1, le=50),
           db: Session = Depends(db_session)) -> list[dict]:
    return svc.buscar_referencias(db, search, limit)


@router.get("/references/{id_cliente}", summary="Referencia vigente de un cliente")
def referencia(request: Request, id_cliente: str = Path(max_length=36), db: Session = Depends(db_session),
               core: CoreDb = Depends(get_core)) -> dict:
    try:
        datos = svc.referencia(db, core, id_cliente, request.state.uuid_transaccion)
    except CaptacionError as exc:
        # SOL trata 503 como dependencia caída y reintenta; no se le envían detalles internos.
        raise HTTPException(503, "Referencia no disponible.") from exc
    if datos is None:
        raise HTTPException(404, "Referencia no encontrada.")
    return datos
