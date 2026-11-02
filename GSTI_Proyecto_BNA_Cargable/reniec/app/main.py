"""RENIEC SIMULADO: servicio externo e independiente del banco, con su propia BD (SQLite).

- /interno/*  : API para el módulo de Clientes (token de servicio).
- /, /admin*  : interfaz y API administrativas (usuario y clave por variables de entorno).
RENIEC no llama a ningún otro servicio.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from shared.comun import configurar_logging, instalar_manejadores

from . import admin, interno
from .db import iniciar_bd

configurar_logging()
RAIZ = Path(__file__).resolve().parent.parent  # carpeta reniec/ (o /app en Docker)


@asynccontextmanager
async def lifespan(app: FastAPI):
    iniciar_bd()
    if os.getenv("PRECARGAR_MODELO_FACIAL", "false").lower() == "true":  # evita la demora en la primera carga facial
        from deepface import DeepFace
        DeepFace.build_model(model_name="ArcFace", task="facial_recognition")
    yield


app = FastAPI(title="RENIEC simulado (BNA)", version="1.0", lifespan=lifespan,
              description="Servicio externo SIMULADO. /interno/* requiere X-Service-Token; la administración requiere HTTP Basic.")
instalar_manejadores(app)
app.state.templates = Jinja2Templates(directory=str(RAIZ / "templates"))
app.mount("/static", StaticFiles(directory=str(RAIZ / "static")), name="static")
# CSS común a las dos interfaces: shared/ui (en Docker queda en /app/shared/ui)
UI_COMUN = next(p for p in (RAIZ / "shared" / "ui", RAIZ.parent / "shared" / "ui") if p.exists())
app.mount("/static-base", StaticFiles(directory=str(UI_COMUN)), name="static-base")
app.include_router(interno.router)
app.include_router(admin.router)


@app.get("/salud", tags=["Estado"])
def salud():
    return {"servicio": "reniec-simulado", "estado": "ok"}
