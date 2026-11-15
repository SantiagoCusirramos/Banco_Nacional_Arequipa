"""API del módulo 13 Desembolso (Línea de Créditos). Puerto 8016 en el producto.

    uvicorn DESEMBOLSO.main:app --port 8016      (desde backend/)
"""
from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from dataclasses import dataclass

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .api.rutas import api, salud
from .config import Config
from .core.correlacion import MiddlewareCorrelacion
from .core.errores import registrar_manejadores
from .core.registro import configurar_registros
from .integraciones.modulos import Modulos
from .persistencia.repositorio import crear_fabrica, crear_motor
from .servicios.auditoria import Auditor
from .servicios.operacion import Conciliador, Despachador, Operacion, Recuperador
from .servicios.ordenes import ServicioOrdenes
from .servicios.reversiones import ServicioReversiones

configurar_registros()
log = logging.getLogger("desembolso")


@dataclass
class Servicios:
    motor: Engine
    fabrica: sessionmaker[Session]
    modulos: Modulos
    auditor: Auditor
    ordenes: ServicioOrdenes
    reversiones: ServicioReversiones
    recuperador: Recuperador
    despachador: Despachador
    conciliador: Conciliador
    operacion: Operacion


def construir_servicios(config: Config, transportes: dict[str, httpx.BaseTransport] | None = None) -> Servicios:
    motor = crear_motor(config.database_url)
    fabrica = crear_fabrica(motor)
    modulos = Modulos(config, transportes)
    auditor = Auditor(fabrica, modulos.seguridad)
    ordenes = ServicioOrdenes(config, fabrica, modulos, auditor)
    reversiones = ServicioReversiones(config, fabrica, modulos, auditor, ordenes)
    return Servicios(
        motor=motor, fabrica=fabrica, modulos=modulos, auditor=auditor, ordenes=ordenes, reversiones=reversiones,
        recuperador=Recuperador(config, fabrica, ordenes, reversiones),
        despachador=Despachador(config, fabrica, modulos, auditor),
        conciliador=Conciliador(fabrica, modulos, auditor),
        operacion=Operacion(config, fabrica, modulos),
    )


class Trabajos:
    """Hilos del recuperador y del despachador; seguros con varias instancias (SKIP LOCKED y UPDATE condicional)."""

    def __init__(self, config: Config, srv: Servicios):
        self._detener = threading.Event()
        self._hilos = [
            threading.Thread(target=self._bucle, args=("recuperador", srv.recuperador.ejecutar,
                                                       config.recuperacion_intervalo_seg), daemon=True),
            threading.Thread(target=self._bucle, args=("despachador", srv.despachador.ejecutar,
                                                       config.entrega_intervalo_seg), daemon=True),
        ]

    def _bucle(self, nombre: str, tarea, intervalo: float) -> None:
        while not self._detener.wait(intervalo):
            try:
                resultado = tarea()
                if any(v for k, v in resultado.items() if k not in ("revisadas", "enviados")):
                    log.info("%s: %s", nombre, resultado)
            except Exception:  # noqa: BLE001 - el bucle no debe morir por una falla puntual
                log.exception("Falla en el trabajo %s", nombre)

    def iniciar(self) -> None:
        for hilo in self._hilos:
            hilo.start()

    def detener(self) -> None:
        self._detener.set()
        for hilo in self._hilos:
            hilo.join(timeout=5)


def crear_app(config: Config | None = None, transportes: dict[str, httpx.BaseTransport] | None = None) -> FastAPI:
    config = config or Config()
    srv = construir_servicios(config, transportes)

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI):
        trabajos = Trabajos(config, srv) if config.trabajos_habilitados else None
        if trabajos:
            trabajos.iniciar()
        yield
        if trabajos:
            trabajos.detener()
        srv.modulos.cerrar()
        srv.motor.dispose()

    app = FastAPI(
        title="BNA · Desembolso de créditos",
        version="2.0.0",
        description="Servicio SRV-CR-04 (módulo 13): prepara, valida, ejecuta y sigue el desembolso de una aprobación "
                    "de Evaluación (CR-INT-04). Abona por CUENTAS (CR-INT-05), entrega a Cobranza la obligación con el "
                    "calendario de Solicitud sin cambios (CR-INT-06) y avisa a Evaluación que la aprobación se usó. "
                    "El personal entra con su token de COREDB. Montos como texto decimal (\"500.00\").",
        lifespan=ciclo_de_vida,
    )
    app.state.config = config
    app.state.servicios = srv
    app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in config.cors_origenes.split(",")],
                       allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Correlation-ID"])
    app.add_middleware(MiddlewareCorrelacion)
    registrar_manejadores(app)
    app.include_router(api)
    app.include_router(salud)
    return app


app = crear_app()
