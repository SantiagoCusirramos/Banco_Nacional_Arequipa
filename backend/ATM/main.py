import os
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ATM.api import montar_en, montar_pantalla
from ATM.config import settings
from ATM.core_client import CoreClient
from ATM.dependencies import get_core_client
from ATM.exceptions import AtmError

app = FastAPI(
    title="BNA - Modulo ATM (Cajero Automatico)",
    description="Modulo de Cajero Automatico. Opera sobre TARJETAS y CUENTAS a traves del Bus de Servicios.",
    version="0.1.0",
)

ORIGENES = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=ORIGENES, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

montar_en(app)


@app.get("/health")
def health():
    return {"status": "healthy", "modulo": "atm"}


@app.get("/ready")
def ready(core: CoreClient = Depends(get_core_client)):
    """Listo para atender solo si TARJETAS y CUENTAS responden por el Bus."""
    try:
        core._request("GET", "/bus/tarjetas/health", sin_cuerpo=True)
        core._request("GET", "/bus/cuentas/health", sin_cuerpo=True)
    except AtmError:
        return JSONResponse(status_code=503, content={"status": "not_ready", "tarjetas_o_cuentas": "no disponible"})
    return {"status": "ready", "tarjetas": "disponible", "cuentas": "disponible"}


montar_pantalla(app)  # al final: / sirve la pantalla sin tapar /health ni /api
