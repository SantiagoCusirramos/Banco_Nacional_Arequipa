"""Rutas REST /api/v1 del modulo de Desembolso."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy import text

from ..core.seguridad import AUDITOR, EJECUTAR, LEER, SUPERVISOR, Usuario
from ..dominio.estados import INCIERTOS
from . import esquemas as e
from .dependencias import clave_idempotencia, requiere, servicios, usuario_actual

api = APIRouter(prefix="/api/v1")
salud = APIRouter(tags=["Operación"])

LECTOR = requiere(LEER)
EJECUTOR = requiere(EJECUTAR)
SUPERVISION = requiere(LEER, roles={SUPERVISOR, AUDITOR})
SOLO_SUPERVISOR = requiere(EJECUTAR, roles={SUPERVISOR})


@api.get("/sesion", response_model=e.Sesion, tags=["Sesión"])
def sesion(request: Request, usuario: Usuario = Depends(usuario_actual)):
    return {"usuario": usuario.id, "nombre": usuario.nombre, "rol": usuario.rol, "permisos": sorted(usuario.permisos),
            "agencia_id": usuario.agencia_id, "agencia_nombre": usuario.agencia_nombre,
            "reversion_habilitada": request.app.state.config.reversion_habilitada}


@api.get("/creditos-habilitados", response_model=list[e.CreditoHabilitado], tags=["CU-01 Créditos"])
def creditos_habilitados(documento: str | None = Query(None, max_length=15), credito_id: str | None = Query(None, max_length=36),
                         usuario: Usuario = Depends(LECTOR), srv=Depends(servicios)):
    return srv.ordenes.creditos_habilitados(usuario, documento, credito_id)


@api.post("/ordenes", response_model=e.OrdenDetalle, status_code=201, tags=["CU-02/03 Órdenes"])
def preparar(cuerpo: e.PrepararOrden, response: Response, clave: str = Depends(clave_idempotencia),
             usuario: Usuario = Depends(EJECUTOR), srv=Depends(servicios)):
    orden_id, repetida = srv.ordenes.preparar(usuario, cuerpo.aprobacion_id, clave)
    if repetida:
        response.status_code = 200
        response.headers["Idempotent-Replay"] = "true"
    return srv.ordenes.detalle(usuario, orden_id)


@api.get("/ordenes", response_model=e.PaginaOrdenes, tags=["CU-04 Consultas"])
def listar(texto: str | None = Query(None, max_length=40), estado: str | None = None, desde: str | None = None,
           hasta: str | None = None, pagina: int = Query(1, ge=1), tamano: int = Query(20, ge=1, le=100),
           usuario: Usuario = Depends(LECTOR), srv=Depends(servicios)):
    return srv.ordenes.listar(texto, estado, desde, hasta, pagina, tamano)


@api.get("/ordenes/{orden_id}", response_model=e.OrdenDetalle, tags=["CU-04 Consultas"])
def detalle(orden_id: str, usuario: Usuario = Depends(LECTOR), srv=Depends(servicios)):
    return srv.ordenes.detalle(usuario, orden_id)


@api.post("/ordenes/{orden_id}/identidad", response_model=e.OrdenDetalle, tags=["CU-02/03 Órdenes"])
def validar_identidad(orden_id: str, cuerpo: e.ValidarIdentidad, usuario: Usuario = Depends(EJECUTOR),
                      srv=Depends(servicios)):
    srv.ordenes.validar_identidad(usuario, orden_id, cuerpo.metodo, cuerpo.numero_documento)
    return srv.ordenes.detalle(usuario, orden_id)


@api.get("/ordenes/{orden_id}/cuentas-elegibles", response_model=list[e.CuentaElegible], tags=["CU-02/03 Órdenes"])
def cuentas_elegibles(orden_id: str, usuario: Usuario = Depends(EJECUTOR), srv=Depends(servicios)):
    return srv.ordenes.cuentas_elegibles(usuario, orden_id)


@api.put("/ordenes/{orden_id}/cuenta-destino", response_model=e.OrdenDetalle, tags=["CU-02/03 Órdenes"])
def seleccionar_cuenta(orden_id: str, cuerpo: e.SeleccionarCuenta, usuario: Usuario = Depends(EJECUTOR),
                       srv=Depends(servicios)):
    srv.ordenes.seleccionar_cuenta(usuario, orden_id, cuerpo.cuenta_id, cuerpo.version)
    return srv.ordenes.detalle(usuario, orden_id)


@api.post("/ordenes/{orden_id}/confirmacion", response_model=e.OrdenDetalle, tags=["CU-02/03 Órdenes"],
          responses={202: {"description": "Resultado financiero incierto: la orden queda POR_VERIFICAR"}})
def confirmar(orden_id: str, cuerpo: e.Confirmar, response: Response, clave: str = Depends(clave_idempotencia),
              usuario: Usuario = Depends(EJECUTOR), srv=Depends(servicios)):
    srv.ordenes.confirmar(usuario, orden_id, clave, cuerpo.version)
    datos = srv.ordenes.detalle(usuario, orden_id)
    if datos["estado"] in INCIERTOS:
        response.status_code = 202
    return datos


@api.post("/ordenes/{orden_id}/verificacion", response_model=e.OrdenDetalle, tags=["CU-04 Consultas"])
def verificar(orden_id: str, usuario: Usuario = Depends(LECTOR), srv=Depends(servicios)):
    srv.ordenes.verificar(usuario, orden_id)
    return srv.ordenes.detalle(usuario, orden_id)


@api.get("/ordenes/{orden_id}/constancia", response_model=e.Constancia, tags=["CU-04 Consultas"])
def constancia(orden_id: str, usuario: Usuario = Depends(LECTOR), srv=Depends(servicios)):
    return srv.ordenes.constancia(usuario, orden_id)


@api.get("/ordenes/{orden_id}/auditoria", tags=["CU-04 Consultas"])
def auditoria(orden_id: str, usuario: Usuario = Depends(SUPERVISION), srv=Depends(servicios)):
    return srv.ordenes.auditoria(orden_id)


@api.get("/operacion/resumen", tags=["CU-05 Operación"])
def resumen_operativo(usuario: Usuario = Depends(SUPERVISION), srv=Depends(servicios)):
    return srv.operacion.resumen()


@api.post("/operacion/recuperacion", tags=["CU-05 Operación"])
def ejecutar_recuperacion(usuario: Usuario = Depends(SOLO_SUPERVISOR), srv=Depends(servicios)):
    return srv.recuperador.ejecutar(actor=usuario.id)


@api.post("/operacion/entregas", tags=["CU-05 Operación"])
def ejecutar_entregas(usuario: Usuario = Depends(SOLO_SUPERVISOR), srv=Depends(servicios)):
    return srv.despachador.ejecutar()


@api.post("/operacion/entregas/{evento_id}/reintento", tags=["CU-05 Operación"])
def reintentar_entrega(evento_id: str, usuario: Usuario = Depends(SOLO_SUPERVISOR), srv=Depends(servicios)):
    return srv.despachador.reintentar(usuario, evento_id)


@api.post("/conciliaciones", tags=["CU-06 Conciliación"])
def conciliar(cuerpo: e.Conciliar, usuario: Usuario = Depends(SUPERVISION), srv=Depends(servicios)):
    return srv.conciliador.conciliar(usuario, cuerpo.fecha, cuerpo.moneda)


@api.post("/ordenes/{orden_id}/reversiones", response_model=e.ReversionSalida, status_code=201, tags=["CU-07 Reversión"])
def solicitar_reversion(orden_id: str, cuerpo: e.SolicitarReversion, clave: str = Depends(clave_idempotencia),
                        usuario: Usuario = Depends(EJECUTOR), srv=Depends(servicios)):
    return srv.reversiones.solicitar(usuario, orden_id, cuerpo.motivo, cuerpo.origen, clave)


@api.post("/reversiones/{reversion_id}/decision", response_model=e.ReversionSalida, tags=["CU-07 Reversión"])
def decidir_reversion(reversion_id: str, cuerpo: e.DecisionReversion, usuario: Usuario = Depends(SOLO_SUPERVISOR),
                      srv=Depends(servicios)):
    return srv.reversiones.decidir(usuario, reversion_id, cuerpo.aprobar, cuerpo.motivo)


@api.get("/reversiones", response_model=list[e.ReversionSalida], tags=["CU-07 Reversión"])
def listar_reversiones(estado: str | None = None, usuario: Usuario = Depends(LECTOR), srv=Depends(servicios)):
    return srv.reversiones.listar(estado)


@salud.get("/health/live")
def vivo():
    return {"estado": "ok"}


@salud.get("/health/ready")
def listo(request: Request, response: Response, srv=Depends(servicios)):
    componentes = {}
    try:
        with srv.fabrica() as s:
            s.execute(text("SELECT 1 FROM des_orden LIMIT 1"))
        componentes["mysql"] = "ok"
    except Exception as exc:  # noqa: BLE001 - se informa cualquier falla de conexion
        componentes["mysql"] = f"error: {type(exc).__name__}"
    componentes["coredb"] = "ok" if srv.modulos.coredb_disponible() else "no disponible"
    listo_ = componentes["mysql"] == "ok"
    response.status_code = 200 if listo_ else 503
    return {"estado": "ok" if listo_ else "degradado", "componentes": componentes}


@salud.get("/metrics", response_class=PlainTextResponse)
def metricas(srv=Depends(servicios)):
    return srv.operacion.metricas()
