
import hmac

from fastapi import FastAPI, Header, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.config import API_KEY
from app.router import router
from app.integration import router_integracion

app = FastAPI(
    title="BNA - Bus de Servicios",
    description=(
        "API Gateway de integración del "
        "Banco Nacional de Arequipa"
    ),
    version="1.0.0",
)


def verificar_api_key(
    x_api_key: str = Header(default=""),
):
    if not hmac.compare_digest(x_api_key, API_KEY):
        raise HTTPException(
            status_code=401,
            detail="Credenciales inválidas",
        )


@app.get("/health", tags=["Sistema"])
def health():
    return {
        "banco": "BNA",
        "modulo": "Bus de Servicios",
        "estado": "operativo",
    }


app.include_router(
    router,
    dependencies=[Depends(verificar_api_key)],
)


@app.exception_handler(HTTPException)
async def manejar_error(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "sistema": "BNA",
            "error": exc.detail,
            "codigo": exc.status_code,
        },
        headers=getattr(exc, "headers", None),
    )


# Integracion oficial BNA
app.include_router(router_integracion)
