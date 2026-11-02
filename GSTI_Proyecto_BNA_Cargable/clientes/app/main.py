"""Módulo de CLIENTES del BNA: registra clientes y comprueba su identidad. Sin base de datos propia.

  /clientes/*  operaciones de negocio (JSON, las invoca el Bus)
  /panel/*     panel web y laboratorio de pruebas
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from shared.comun import configurar_logging, instalar_manejadores, respuesta_error

from . import conexiones, negocio, panel, rutas_negocio

configurar_logging()
RAIZ = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await conexiones.cerrar()


app = FastAPI(title="Módulo de Clientes (BNA)", version="1.0", lifespan=lifespan,
              description="Operaciones: registrar cliente, validar por documento, validar por biometría. "
                          "Las rutas /clientes/* exigen X-Service-Token (las invoca el Bus).")
instalar_manejadores(app)


@app.exception_handler(RequestValidationError)
async def _validacion(request: Request, e: RequestValidationError):
    """Igual que el manejador común, pero un REGISTRO inválido también deja constancia en el Core."""
    if request.url.path == "/clientes/registrar":
        try:
            await negocio.auditar_payload_invalido(await request.json())
        except ValueError:
            pass
    detalle = [{"campo": ".".join(str(p) for p in err["loc"][1:]) or "cuerpo", "mensaje": err["msg"]} for err in e.errors()[:10]]
    return respuesta_error(422, "DATOS_INVALIDOS", "Los datos enviados no son válidos", detalle=detalle)


app.state.templates = Jinja2Templates(directory=str(RAIZ / "templates"))
app.mount("/static", StaticFiles(directory=str(RAIZ / "static")), name="static")
UI_COMUN = next(p for p in (RAIZ / "shared" / "ui", RAIZ.parent / "shared" / "ui") if p.exists())
app.mount("/static-base", StaticFiles(directory=str(UI_COMUN)), name="static-base")
app.include_router(rutas_negocio.router)
app.include_router(panel.router)


@app.get("/", include_in_schema=False)
def inicio():
    return RedirectResponse("/panel")


@app.get("/salud", tags=["Estado"])
def salud():
    return {"servicio": "clientes", "estado": "ok"}
