"""API de la base integrada, aparte de la API de `CORE`.

Uso, desde backend/: uvicorn COREDB.main:app --port 8012
Solo para uso local: no tiene autenticación (ver README.md).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from COREDB.database import verificar_configuracion
from COREDB.errores import registrar_manejadores
from COREDB.routers import catalogos, cuentas, movimientos, salud, tarjetas, usuarios


@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    verificar_configuracion()
    yield


app = FastAPI(
    title="BNA - API de la base integrada",
    description="Escribe por los procedimientos de la base. Uso local: sin autenticación.",
    version="0.1.0",
    lifespan=_ciclo_de_vida,
)
registrar_manejadores(app)
app.include_router(salud.router)
app.include_router(usuarios.router)
app.include_router(movimientos.router)
app.include_router(cuentas.router)
app.include_router(tarjetas.router)
app.include_router(catalogos.router)
