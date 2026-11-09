"""Routers de usuarios, roles, permisos, auditoría y reportes.

Exigen token y permiso. El actor sale siempre del token: el campo `actor` del
cuerpo se ignora. No hay acción VER_USUARIO en el catálogo, por eso consultar
usuarios exige CREAR_USUARIO.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from CORE.dependencies import db_session, requiere_permiso
from CORE.models import UsuarioSistema
from CORE.schemas.usuarios import (
    AuditoriaEventoRespuesta,
    AuditoriaFiltros,
    AsientoReporteRespuesta,
    CatalogoPermisosRespuesta,
    CuadreContableRespuesta,
    MovimientoReporteRespuesta,
    PermisoAsignar,
    ReporteFechas,
    RolAsignar,
    UsuarioCrear,
    UsuarioRespuesta,
)
from CORE.services import rbac, reportessvc, usuariossvc

usuarios_router = APIRouter(prefix="/usuarios", tags=["Usuarios"])
permisos_router = APIRouter(prefix="/permisos", tags=["Permisos"])
auditoria_router = APIRouter(
    prefix="/auditoria", tags=["Auditoria"],
    dependencies=[Depends(requiere_permiso("VER_AUDITORIA"))],
)
reportes_router = APIRouter(
    prefix="/reportes", tags=["Reportes"],
    dependencies=[Depends(requiere_permiso("GENERAR_REPORTES"))],
)


# ------------------------------------------------------------------ usuarios
@usuarios_router.get(
    "", response_model=list[UsuarioRespuesta],
    dependencies=[Depends(requiere_permiso("CREAR_USUARIO"))],
)
def listar_usuarios(
    activo: bool | None = Query(default=None),
    rol: str | None = Query(default=None),
    limite: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(db_session),
):
    usuarios = usuariossvc.listar_usuarios(
        db, activo=activo, rol=rol, limite=limite, offset=offset
    )
    return [UsuarioRespuesta(**usuariossvc.vista_publica(u)) for u in usuarios]


@usuarios_router.get(
    "/{id_usuario}", response_model=UsuarioRespuesta,
    dependencies=[Depends(requiere_permiso("CREAR_USUARIO"))],
)
def ver_usuario(id_usuario: str, db: Session = Depends(db_session)):
    return UsuarioRespuesta(**usuariossvc.vista_publica(usuariossvc.obtener_usuario(db, id_usuario)))


@usuarios_router.post("", response_model=UsuarioRespuesta, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    payload: UsuarioCrear,
    db: Session = Depends(db_session),
    usuario_actual: UsuarioSistema = Depends(requiere_permiso("CREAR_USUARIO")),
):
    usuario = usuariossvc.crear_usuario(
        db,
        username=payload.username,
        nombre=payload.nombre,
        password=payload.password,
        rol=payload.rol,
        id_empleado=payload.id_empleado,
        activo=payload.activo,
        actor=usuario_actual.username,
        correlation_id=payload.correlation_id,
    )
    return UsuarioRespuesta(**usuariossvc.vista_publica(usuario))


@usuarios_router.post("/{id_usuario}/rol", response_model=UsuarioRespuesta)
def asignar_rol(
    id_usuario: str,
    payload: RolAsignar,
    db: Session = Depends(db_session),
    usuario_actual: UsuarioSistema = Depends(requiere_permiso("ASIGNAR_ROLES")),
):
    usuario = usuariossvc.asignar_rol(
        db,
        id_usuario,
        nuevo_rol=payload.rol,
        actor=usuario_actual.username,
        correlation_id=payload.correlation_id,
    )
    return UsuarioRespuesta(**usuariossvc.vista_publica(usuario))


# ------------------------------------------------------------------ permisos
@permisos_router.get(
    "", response_model=CatalogoPermisosRespuesta,
    dependencies=[Depends(requiere_permiso("GESTIONAR_PERMISOS"))],
)
def ver_catalogo():
    cat = rbac.obtener_catalogo()
    return CatalogoPermisosRespuesta(**cat)


@permisos_router.get(
    "/rol/{rol}", response_model=list[str],
    dependencies=[Depends(requiere_permiso("GESTIONAR_PERMISOS"))],
)
def acciones_del_rol(rol: str):
    return rbac.acciones_de_rol(rol)


@permisos_router.post("/asignar")
def asignar_permiso(
    payload: PermisoAsignar,
    usuario_actual: UsuarioSistema = Depends(requiere_permiso("GESTIONAR_PERMISOS")),
):
    return rbac.asignar_accion(payload.rol, payload.accion, actor=usuario_actual.username)


@permisos_router.post("/revocar")
def revocar_permiso(
    payload: PermisoAsignar,
    usuario_actual: UsuarioSistema = Depends(requiere_permiso("GESTIONAR_PERMISOS")),
):
    return rbac.revocar_accion(payload.rol, payload.accion, actor=usuario_actual.username)


# ------------------------------------------------------------------ auditoria
@auditoria_router.get("", response_model=list[AuditoriaEventoRespuesta])
def ver_auditoria(
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    modulo: str | None = Query(default=None),
    accion: str | None = Query(default=None),
    actor: str | None = Query(default=None),
    correlation_id: str | None = Query(default=None),
    limite: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(db_session),
):
    eventos = reportessvc.reporte_auditoria(
        db,
        desde=desde,
        hasta=hasta,
        modulo=modulo,
        accion=accion,
        actor=actor,
        correlation_id=correlation_id,
        limite=limite,
        offset=offset,
    )
    return [AuditoriaEventoRespuesta(**e) for e in eventos]


# ------------------------------------------------------------------ reportes
@reportes_router.get("/cuadre-contable", response_model=CuadreContableRespuesta)
def cuadre_contable(
    fecha: date | None = Query(default=None), db: Session = Depends(db_session)
):
    return CuadreContableRespuesta(**reportessvc.reporte_cuadre_contable(db, fecha))


@reportes_router.get("/asientos", response_model=list[AsientoReporteRespuesta])
def asientos(
    desde: date = Query(...),
    hasta: date = Query(...),
    estado: str | None = Query(default=None),
    limite: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(db_session),
):
    filas = reportessvc.reporte_asientos(
        db, desde=desde, hasta=hasta, estado=estado, limite=limite, offset=offset
    )
    return [AsientoReporteRespuesta(**f) for f in filas]


@reportes_router.get("/movimientos", response_model=list[MovimientoReporteRespuesta])
def movimientos(
    num_cuenta: str | None = Query(default=None),
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    limite: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(db_session),
):
    filas = reportessvc.reporte_movimientos(
        db, num_cuenta=num_cuenta, desde=desde, hasta=hasta, limite=limite, offset=offset
    )
    return [MovimientoReporteRespuesta(**f) for f in filas]


@reportes_router.get("/historial-cliente/{id_cliente}")
def historial_cliente(id_cliente: str, db: Session = Depends(db_session)):
    return reportessvc.reporte_historial_cliente(db, id_cliente=id_cliente)
