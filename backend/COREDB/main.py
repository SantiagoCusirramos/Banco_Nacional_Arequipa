"""API de la base integrada, aparte de la API de `CORE`.

Uso, desde backend/: uvicorn COREDB.main:app --port 8012
Exige un JWT propio (ver README.md). Sin TLS: no exponer fuera de la máquina.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from COREDB import tokens
from COREDB.database import verificar_configuracion
from COREDB.errores import registrar_manejadores
from COREDB.routers import (
    auditoria, auth, autorizaciones, catalogos, clientes, creditos_cobranza, creditos_desembolso,
    creditos_evaluacion, cuentas, empleados, movimientos, salud, tarjetas, usuarios,
)


@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    tokens.verificar_clave()
    verificar_configuracion()
    yield


app = FastAPI(
    title="BNA - API de la base integrada",
    description=(
        "Escribe por los procedimientos de la base. Exige `Authorization: Bearer <token>`, "
        "que entrega POST /coredb/auth/login, salvo en /coredb/salud."
    ),
    version="0.2.0",
    lifespan=_ciclo_de_vida,
)
registrar_manejadores(app)
app.include_router(salud.router)
app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(empleados.router)
app.include_router(clientes.router)
app.include_router(movimientos.router)
app.include_router(cuentas.router)
app.include_router(tarjetas.router)
app.include_router(autorizaciones.router)
app.include_router(creditos_evaluacion.router)
app.include_router(creditos_desembolso.router)
# Después de evaluación y desembolso: sus rutas fijas van antes que /coredb/creditos/{cod_credito}.
app.include_router(creditos_cobranza.router)
app.include_router(catalogos.router)
app.include_router(auditoria.router)
