from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from CORE.api import montar_en
from CORE.config import verificar_configuracion


@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    verificar_configuracion()
    yield


app = FastAPI(
    title="BNA - Backend",
    description="Backend del Banco Nacional de Arequipa",
    version="0.1.0",
    lifespan=_ciclo_de_vida,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

montar_en(app)


@app.get("/")
def root():
    return {
        "proyecto": "BNA",
        "status": "ok",
        "version": "0.1.0",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
