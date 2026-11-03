"""Core bancario SIMULADO: único dueño de los datos bancarios y de los registros de solicitudes.

Solo el mini-Bus lo invoca (rutas /interno/*, protegidas con CORE_TOKEN). No guarda biometría.
"""
from contextlib import asynccontextmanager
from datetime import date
from typing import Literal, Optional

from fastapi import Depends, FastAPI, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from shared.comun import ApiError, configurar_logging, entorno, instalar_manejadores, requerir_token
from shared.esquemas import DatosCliente

from . import models as m
from .db import SessionLocal, ahora_utc, engine, iniciar_bd

configurar_logging()
CORE_TOKEN = entorno("CORE_TOKEN")
interno = [Depends(requerir_token(CORE_TOKEN))]


@asynccontextmanager
async def lifespan(_: FastAPI):
    iniciar_bd()
    yield


app = FastAPI(title="Core bancario simulado (BNA)", version="1.0", lifespan=lifespan,
              description="API INTERNA. Solo debe ser invocada por el mini-Bus de Servicios con la cabecera X-Service-Token.")
instalar_manejadores(app)


# ------------------------------------------------------------------ esquemas
class RegistroCoreIn(DatosCliente):
    verificado_reniec: bool = False  # lo informa Clientes; solo sirve para el resultado de auditoría


class AuditoriaRegistroIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    modulo_origen: str = Field(max_length=30)
    tipo_documento: str = Field(max_length=20)
    numero_documento: str = Field(max_length=40)
    resultado: str = Field(max_length=80)


class ValidarDocumentoCoreIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    modulo_origen: str = Field(max_length=30)
    tipo_documento: Literal["DNI", "PASAPORTE", "PTP"]
    numero_documento: str = Field(max_length=20)
    fecha_nacimiento: date
    identidad: str = Field(max_length=40, description="Estado de identidad calculado por Clientes")
    consultar: bool = True


class ValidarBiometriaCoreIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    modulo_origen: str = Field(max_length=30)
    numero_documento: str = Field(max_length=20)
    tipo_validacion: Literal["FACIAL", "HUELLA"]
    resultado_biometrico: str = Field(max_length=40)
    consultar: bool = True


# ------------------------------------------------------------------ utilidades
def _iso(dt) -> str:
    return dt.isoformat() + "Z"


def _buscar_cliente(db, tipo: str, numero: str) -> Optional[m.Cliente]:
    return db.scalar(
        select(m.Cliente).join(m.TipoDocumento, m.Cliente.tipo_documento_id == m.TipoDocumento.id)
        .where(m.TipoDocumento.codigo == tipo, m.Cliente.numero_documento == numero)
    )


def _registrar_solicitud_registro(db, modulo, tipo, numero, resultado) -> None:
    db.add(m.SolicitudRegistro(modulo_origen=modulo[:30], tipo_documento=tipo[:20], numero_documento=numero[:40],
                               fecha_solicitud=ahora_utc(), resultado=resultado[:80]))


# ------------------------------------------------------------------ salud
@app.get("/salud", tags=["Estado"])
def salud():
    with engine.connect() as con:
        con.execute(text("SELECT 1"))
    return {"servicio": "core-simulado", "estado": "ok"}


# ------------------------------------------------------------------ registro
@app.post("/interno/registrar-cliente", status_code=201, dependencies=interno, tags=["Interno"])
def registrar_cliente(d: RegistroCoreIn):
    """Registra al cliente en una transacción y deja siempre constancia de la solicitud."""
    with SessionLocal() as db:
        tipo = db.scalar(select(m.TipoDocumento).where(m.TipoDocumento.codigo == d.tipo_documento))
        if tipo is None:
            _registrar_solicitud_registro(db, d.modulo_origen, d.tipo_documento, d.numero_documento, "RECHAZADO_TIPO_DOCUMENTO")
            db.commit()
            raise ApiError(422, "TIPO_DOCUMENTO_INVALIDO", "Tipo de documento no soportado")

        duplicado = _buscar_cliente(db, d.tipo_documento, d.numero_documento) is not None
        if not duplicado:
            try:
                cliente = m.Cliente(
                    tipo_documento_id=tipo.id, numero_documento=d.numero_documento, nombres=d.nombres, apellidos=d.apellidos,
                    fecha_nacimiento=d.fecha_nacimiento, ingreso_mensual=d.ingreso_mensual, direccion=d.direccion,
                    correo=d.correo, telefono=d.telefono, fecha_registro=ahora_utc(),
                )
                db.add(cliente)
                db.flush()  # si otro hilo insertó el mismo documento, la restricción única falla aquí
                _registrar_solicitud_registro(db, d.modulo_origen, d.tipo_documento, d.numero_documento,
                                              "REGISTRADO" if d.verificado_reniec else "REGISTRADO_SIN_RENIEC")
                db.commit()  # cliente + auditoría en UNA transacción
                return {"correcto": True, "cliente_id": cliente.id}
            except IntegrityError:
                db.rollback()

        # Rechazo por duplicado: el intento igual queda registrado (transacción aparte).
        _registrar_solicitud_registro(db, d.modulo_origen, d.tipo_documento, d.numero_documento, "RECHAZADO_CLIENTE_DUPLICADO")
        db.commit()
    raise ApiError(409, "CLIENTE_DUPLICADO", "El cliente ya está registrado")


@app.post("/interno/auditar-registro", status_code=201, dependencies=interno, tags=["Interno"])
def auditar_registro(a: AuditoriaRegistroIn):
    """Deja constancia de un registro rechazado ANTES de llegar al Core (datos inválidos, RENIEC, etc.)."""
    with SessionLocal() as db:
        _registrar_solicitud_registro(db, a.modulo_origen, a.tipo_documento, a.numero_documento, a.resultado)
        db.commit()
    return {"correcto": True}


# ------------------------------------------------------------------ validación
@app.post("/interno/validar-documento", dependencies=interno, tags=["Interno"])
def validar_documento(v: ValidarDocumentoCoreIn):
    """Consulta (opcional) si la persona es cliente y registra la solicitud en una sola operación."""
    registrado, fecha_coincide, cliente_out = False, None, None
    resultado = v.identidad
    with SessionLocal() as db:
        if v.consultar:
            c = _buscar_cliente(db, v.tipo_documento, v.numero_documento)
            registrado = c is not None
            if registrado:
                fecha_coincide = c.fecha_nacimiento == v.fecha_nacimiento
                if fecha_coincide:  # datos personales solo si la fecha coincide con la registrada
                    cliente_out = {"id": c.id, "nombres": c.nombres, "apellidos": c.apellidos}
            resultado = f"{v.identidad}|{'REGISTRADO' if registrado else 'NO_REGISTRADO'}"
            if registrado and not fecha_coincide:
                resultado += "|FECHA_NO_COINCIDE"
        db.add(m.SolicitudValidacion(modulo_origen=v.modulo_origen[:30], tipo_documento=v.tipo_documento,
                                     numero_documento=v.numero_documento[:40], tipo_validacion="DOCUMENTO",
                                     fecha_solicitud=ahora_utc(), resultado=resultado[:80]))
        db.commit()
    return {"registrado": registrado, "fecha_coincide": fecha_coincide, "cliente": cliente_out}


@app.post("/interno/validar-biometria", dependencies=interno, tags=["Interno"])
def validar_biometria(v: ValidarBiometriaCoreIn):
    """Registra la solicitud biométrica y, si RENIEC confirmó la identidad, consulta si es cliente."""
    registrado, cliente_out = False, None
    resultado = v.resultado_biometrico
    with SessionLocal() as db:
        if v.consultar:
            c = _buscar_cliente(db, "DNI", v.numero_documento)
            registrado = c is not None
            if registrado:
                cliente_out = {"id": c.id, "nombres": c.nombres, "apellidos": c.apellidos}
            resultado = f"{v.resultado_biometrico}|{'REGISTRADO' if registrado else 'NO_REGISTRADO'}"
        db.add(m.SolicitudValidacion(modulo_origen=v.modulo_origen[:30], tipo_documento="DNI",
                                     numero_documento=v.numero_documento[:40], tipo_validacion=v.tipo_validacion,
                                     fecha_solicitud=ahora_utc(), resultado=resultado[:80]))
        db.commit()
    return {"registrado": registrado, "cliente": cliente_out}


# ------------------------------------------------------------------ consultas para el panel de Clientes
@app.get("/interno/solicitudes-registro", dependencies=interno, tags=["Interno"])
def listar_solicitudes_registro(limite: int = Query(100, ge=1, le=500), orden: Literal["recientes", "antiguas"] = "recientes"):
    with SessionLocal() as db:
        q = select(m.SolicitudRegistro).order_by(m.SolicitudRegistro.id.desc() if orden == "recientes" else m.SolicitudRegistro.id.asc()).limit(limite)
        return [{"id": s.id, "modulo_origen": s.modulo_origen, "tipo_documento": s.tipo_documento,
                 "numero_documento": s.numero_documento, "fecha_solicitud": _iso(s.fecha_solicitud), "resultado": s.resultado}
                for s in db.scalars(q)]


@app.get("/interno/solicitudes-validacion", dependencies=interno, tags=["Interno"])
def listar_solicitudes_validacion(limite: int = Query(100, ge=1, le=500), orden: Literal["recientes", "antiguas"] = "recientes"):
    with SessionLocal() as db:
        q = select(m.SolicitudValidacion).order_by(m.SolicitudValidacion.id.desc() if orden == "recientes" else m.SolicitudValidacion.id.asc()).limit(limite)
        return [{"id": s.id, "modulo_origen": s.modulo_origen, "tipo_documento": s.tipo_documento,
                 "numero_documento": s.numero_documento, "tipo_validacion": s.tipo_validacion,
                 "fecha_solicitud": _iso(s.fecha_solicitud), "resultado": s.resultado}
                for s in db.scalars(q)]
