"""Interfaz y API ADMINISTRATIVAS de RENIEC (HTTP Basic). No es una API pública del banco."""
import json
import logging
from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select

from shared.biometria import plantillas as bio
from shared.comun import ApiError, enmascarar_doc, requerir_basic
from shared.esquemas import FORMATO_FACIAL, FORMATO_HUELLA

from . import models as m
from .config import RENIEC_ADMIN_PASSWORD, RENIEC_ADMIN_USER
from .db import SessionLocal, ahora_utc

log = logging.getLogger("reniec.admin")
exigir_admin = requerir_basic(RENIEC_ADMIN_USER, RENIEC_ADMIN_PASSWORD, "RENIEC simulado")


router = APIRouter(dependencies=[Depends(exigir_admin)], tags=["Administración (HTML + API)"])


class CiudadanoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    numero_documento: str = Field(pattern=r"^\d{8}$")
    nombres: str = Field(min_length=1, max_length=100)
    apellidos: str = Field(min_length=1, max_length=100)
    fecha_nacimiento: date
    genero: Literal["M", "F"]

    @field_validator("nombres", "apellidos")
    @classmethod
    def _limpiar(cls, v: str):
        v = " ".join(v.split())
        if not v:
            raise ValueError("No puede estar vacío")
        return v

    @field_validator("fecha_nacimiento")
    @classmethod
    def _rango(cls, v: date):
        if v < date(1900, 1, 1) or v > date.today():
            raise ValueError("La fecha de nacimiento está fuera de rango")
        return v


def _fila(c: m.Ciudadano, tipos: set[str]) -> dict:
    return {"numero_documento": c.numero_documento, "nombres": c.nombres, "apellidos": c.apellidos,
            "fecha_nacimiento": c.fecha_nacimiento.isoformat(), "genero": c.genero,
            "tiene_facial": "FACIAL" in tipos, "tiene_huella": "HUELLA" in tipos}


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
def pagina(request: Request):
    return request.app.state.templates.TemplateResponse(request, "admin.html")


@router.get("/admin/api/ciudadanos")
def listar(q: str = "", limite: int = 500):
    with SessionLocal() as db:
        consulta = select(m.Ciudadano).order_by(m.Ciudadano.numero_documento).limit(min(max(limite, 1), 500))
        if q.strip():
            patron = f"%{q.strip()}%"
            consulta = consulta.where(m.Ciudadano.numero_documento.like(patron) | m.Ciudadano.nombres.ilike(patron) | m.Ciudadano.apellidos.ilike(patron))
        ciudadanos = list(db.scalars(consulta))
        tipos: dict[str, set[str]] = {}
        for dni, tipo in db.execute(select(m.PlantillaBiometrica.numero_documento, m.PlantillaBiometrica.tipo_biometria)):
            tipos.setdefault(dni, set()).add(tipo)
        total = db.scalar(select(func.count()).select_from(m.Ciudadano))
    return {"total": total, "ciudadanos": [_fila(c, tipos.get(c.numero_documento, set())) for c in ciudadanos]}


@router.post("/admin/api/ciudadanos", status_code=201)
def crear(c: CiudadanoIn):
    with SessionLocal() as db:
        if db.get(m.Ciudadano, c.numero_documento):
            raise ApiError(409, "CIUDADANO_DUPLICADO", "Ya existe un ciudadano con ese DNI")
        db.add(m.Ciudadano(**c.model_dump()))
        db.commit()
    return {"correcto": True, "numero_documento": c.numero_documento}


@router.delete("/admin/api/ciudadanos/{dni}")
def eliminar(dni: str):
    with SessionLocal() as db:
        c = db.get(m.Ciudadano, dni)
        if c is None:
            raise ApiError(404, "CIUDADANO_NO_ENCONTRADO", "No existe un ciudadano con ese DNI")
        db.query(m.PlantillaBiometrica).filter_by(numero_documento=dni).delete()
        db.delete(c)
        db.commit()
    return {"correcto": True}


@router.post("/admin/api/ciudadanos/{dni}/biometria/{tipo}")
def cargar_biometria(dni: str, tipo: Literal["facial", "huella"], archivo: UploadFile = File(...)):
    """Imagen JPG/PNG -> plantilla (mismo componente compartido que usa la validación). La imagen NO se guarda."""
    with SessionLocal() as db:
        if db.get(m.Ciudadano, dni) is None:
            raise ApiError(404, "CIUDADANO_NO_ENCONTRADO", "No existe un ciudadano con ese DNI")
    datos = archivo.file.read(bio.MAX_IMAGE_BYTES + 1)  # lectura acotada
    try:
        if tipo == "facial":
            embedding = bio.extraer_embedding_facial(datos)
            fila = ("FACIAL", FORMATO_FACIAL, json.dumps(embedding), bio.ALGORITMO_FACIAL)
            resumen = {"dimensiones": len(embedding)}
        else:
            b64, metricas = bio.extraer_plantilla_huella(datos)
            fila = ("HUELLA", FORMATO_HUELLA, b64, bio.ALGORITMO_HUELLA)
            resumen = metricas
    except bio.BiometriaError as e:
        raise ApiError(e.status, e.codigo, e.mensaje)
    finally:
        del datos

    with SessionLocal() as db:
        existente = db.scalar(select(m.PlantillaBiometrica).where(m.PlantillaBiometrica.numero_documento == dni, m.PlantillaBiometrica.tipo_biometria == fila[0]))
        if existente is None:
            existente = m.PlantillaBiometrica(numero_documento=dni, tipo_biometria=fila[0])
            db.add(existente)
        existente.formato, existente.plantilla, existente.algoritmo = fila[1], fila[2], fila[3]
        existente.version, existente.fecha_registro = bio.VERSION_PLANTILLAS, ahora_utc()
        db.commit()
    log.info("plantilla %s registrada para dni=%s", fila[0], enmascarar_doc(dni))
    return {"correcto": True, "tipo": fila[0], "formato": fila[1], **resumen}
