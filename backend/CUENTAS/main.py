from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # Añadido middleware CORS para permitir peticiones desde el frontend

from CUENTAS.api import montar_en

app = FastAPI(
    title="BNA - Modulo de Cuentas",
    description="Modulo de Cuentas (linea Ahorros). Persistencia a traves de CORE.",
    version="0.2.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

montar_en(app)


@app.get("/health")
def health():
    return {"status": "healthy", "modulo": "cuentas"}
