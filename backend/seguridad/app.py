"""Seguridad (módulo 9), sin base propia: uvicorn seguridad.app:app --port 8013 (desde backend/).

Al arrancar valida la configuración y, si SEGURIDAD_SELLADO_SEG > 0, sella la bitácora de COREDB
cada ese número de segundos en un hilo aparte.
"""
from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from . import auditoria
from .api import VERSION, router
from .auth import Verificador
from .comun import ErrorSeg, correlacion_actual, fijar_correlacion, restaurar_correlacion
from .config import Config
from .coredb import ClienteCoreDb

log = logging.getLogger("seguridad")


@dataclass
class Contexto:
    config: Config
    coredb: ClienteCoreDb
    verificador: Verificador
    _parar: threading.Event = field(default_factory=threading.Event)

    @classmethod
    def desde_config(cls, config: Config) -> "Contexto":
        coredb = ClienteCoreDb(config.coredb_url, config.servicio_usuario, config.servicio_secreto,
                               timeout=config.timeout_seg, bus_token=config.bus_token)
        return cls(config, coredb, Verificador(coredb))

    def sellar_periodicamente(self) -> None:
        while not self._parar.wait(self.config.sellado_seg):
            token = fijar_correlacion(f"sellado-{correlacion_actual()}")
            try:
                sello = auditoria.sellar(self.coredb, self.config.clave, self.config.sellado_antiguedad_seg)
                if sello:
                    log.info("Bitácora sellada hasta el evento %s.", sello["hasta_evento"])
            except ErrorSeg as exc:  # COREDB caído o un sello simultáneo: el siguiente lo intenta
                log.warning("No se pudo sellar la bitácora: %s %s.", exc.codigo, exc.mensaje)
            except Exception:  # noqa: BLE001 - el hilo no debe morir
                log.exception("Error al sellar la bitácora.")
            finally:
                restaurar_correlacion(token)

    def cerrar(self) -> None:
        self._parar.set()
        self.coredb.cerrar()


def crear_app(contexto: Contexto | None = None) -> FastAPI:
    @asynccontextmanager
    async def ciclo(app: FastAPI):
        ctx = contexto or Contexto.desde_config(Config.desde_entorno())
        app.state.ctx = ctx
        if ctx.config.sellado_seg > 0:
            threading.Thread(target=ctx.sellar_periodicamente, name="sellado", daemon=True).start()
        try:
            yield
        finally:
            ctx.cerrar()

    app = FastAPI(title="BNA · Seguridad", version=VERSION, lifespan=ciclo,
                  description="Sin base propia: guarda en la base integrada por COREDB, a través del Bus.")

    @app.middleware("http")
    async def _correlacion(request: Request, call_next):
        token = fijar_correlacion(request.headers.get("X-Correlation-ID") or correlacion_actual())
        try:
            return await call_next(request)
        finally:
            restaurar_correlacion(token)

    @app.exception_handler(ErrorSeg)
    async def _error(request: Request, exc: ErrorSeg):
        cabeceras = {"WWW-Authenticate": "Bearer"} if exc.estado == 401 else None
        return JSONResponse(status_code=exc.estado, content={"error": {"code": exc.codigo, "message": exc.mensaje}},
                            headers=cabeceras)

    @app.exception_handler(RequestValidationError)
    async def _validacion(request: Request, exc: RequestValidationError):
        # Sin los valores recibidos: pueden incluir contraseñas o códigos.
        return JSONResponse(status_code=422, content={"detail": [
            {"loc": list(e["loc"]), "type": e["type"]} for e in exc.errors()]})

    app.include_router(router)

    @app.get("/", include_in_schema=False)
    def consola():
        return FileResponse(Path(__file__).parent / "static" / "index.html")

    return app


app = crear_app()
