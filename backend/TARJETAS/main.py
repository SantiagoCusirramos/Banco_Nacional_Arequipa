import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from TARJETAS.api import montar_en
from TARJETAS.core_client import CoreClient
from TARJETAS.dependencies import get_core_client
from TARJETAS.exceptions import TarjetasError

app = FastAPI(
    title="BNA - Modulo de Tarjetas",
    description="Modulo de Tarjetas de debito. Persistencia a traves de COREDB.",
    version="0.1.0",
)

ORIGENES = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if o.strip()]

app.add_middleware(CORSMiddleware, allow_origins=ORIGENES, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

montar_en(app)


@app.get("/health")
def health():
    return {"status": "healthy", "modulo": "tarjetas"}


@app.get("/ready")
def ready(core: CoreClient = Depends(get_core_client)):
    """Listo para atender solo si COREDB responde: sin COREDB no hay nada que hacer."""
    try:
        core.salud()
    except TarjetasError:
        return JSONResponse(status_code=503, content={"status": "not_ready", "coredb": "no disponible"})
    return {"status": "ready", "coredb": "disponible"}
