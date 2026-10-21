from fastapi import FastAPI

from CUENTAS.api import montar_en

app = FastAPI(
    title="BNA - Modulo de Cuentas",
    description="Modulo de Cuentas (linea Ahorros). Persistencia a traves de CORE.",
    version="0.1.0",
)

montar_en(app)


@app.get("/health")
def health():
    return {"status": "healthy", "modulo": "cuentas"}
