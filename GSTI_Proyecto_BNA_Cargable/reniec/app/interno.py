"""API INTERNA de RENIEC. Solo el módulo de Clientes la consume (X-Service-Token = RENIEC_SERVICE_TOKEN).

Las respuestas no entregan datos personales: solo estados.
"""
import json
import logging
import unicodedata
from datetime import date
from typing import Literal, Optional, Union

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from shared.biometria import plantillas as bio
from shared.comun import ApiError, enmascarar_doc, requerir_token
from shared.esquemas import FORMATO_FACIAL, FORMATO_HUELLA

from . import models as m
from .config import RENIEC_SERVICE_TOKEN
from .db import SessionLocal

log = logging.getLogger("reniec")
router = APIRouter(prefix="/interno", tags=["Interno (solo Clientes)"], dependencies=[Depends(requerir_token(RENIEC_SERVICE_TOKEN))])


def normalizar(texto: str) -> str:
    """'  María  ELENA ' -> 'maria elena' (sin tildes, minúsculas, espacios simples)."""
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
    return " ".join(sin_tildes.casefold().split())


class ValidarDniIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    numero_documento: str = Field(pattern=r"^\d{8}$")
    fecha_nacimiento: date
    nombres: Optional[str] = Field(default=None, max_length=100)
    apellidos: Optional[str] = Field(default=None, max_length=100)


@router.post("/validar-dni")
def validar_dni(v: ValidarDniIn):
    """Estados: DNI_VALIDO | DNI_NO_ENCONTRADO | DATOS_NO_COINCIDEN."""
    with SessionLocal() as db:
        c = db.get(m.Ciudadano, v.numero_documento)
    if c is None:
        return {"estado": "DNI_NO_ENCONTRADO"}
    discrepantes = []
    if c.fecha_nacimiento != v.fecha_nacimiento:
        discrepantes.append("fecha_nacimiento")
    if v.nombres is not None and normalizar(c.nombres) != normalizar(v.nombres):
        discrepantes.append("nombres")
    if v.apellidos is not None and normalizar(c.apellidos) != normalizar(v.apellidos):
        discrepantes.append("apellidos")
    if discrepantes:
        return {"estado": "DATOS_NO_COINCIDEN", "campos": discrepantes}
    return {"estado": "DNI_VALIDO"}


class CompararIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    numero_documento: str = Field(pattern=r"^\d{8}$")
    tipo_biometria: Literal["FACIAL", "HUELLA"]
    formato: Literal["ARCFACE_EMBEDDING", "ISO_19794_2_2005"]
    codificacion: Optional[Literal["base64"]] = None
    template: Union[list[float], str]


@router.post("/comparar-biometria")
def comparar_biometria(p: CompararIn):
    """Comparación 1:1 contra la plantilla registrada del DNI.

    Estados: COINCIDE | NO_COINCIDE | DNI_NO_ENCONTRADO | SIN_PLANTILLA.
    Un resultado negativo es una respuesta normal (HTTP 200); los errores técnicos son 4xx/5xx.
    """
    esperado = FORMATO_FACIAL if p.tipo_biometria == "FACIAL" else FORMATO_HUELLA
    if p.formato != esperado:
        raise ApiError(422, "FORMATO_NO_SOPORTADO", f"Para {p.tipo_biometria} el formato debe ser {esperado}")

    with SessionLocal() as db:
        if db.get(m.Ciudadano, p.numero_documento) is None:
            return {"estado": "DNI_NO_ENCONTRADO"}
        fila = db.scalar(select(m.PlantillaBiometrica).where(
            m.PlantillaBiometrica.numero_documento == p.numero_documento, m.PlantillaBiometrica.tipo_biometria == p.tipo_biometria))
    if fila is None:
        return {"estado": "SIN_PLANTILLA"}

    algoritmo_actual = bio.ALGORITMO_FACIAL if p.tipo_biometria == "FACIAL" else bio.ALGORITMO_HUELLA
    if fila.algoritmo != algoritmo_actual or fila.version != bio.VERSION_PLANTILLAS:
        raise ApiError(409, "PLANTILLA_INCOMPATIBLE", "La plantilla registrada se creó con otra configuración; vuelva a registrarla")

    try:
        if p.tipo_biometria == "FACIAL":
            if not isinstance(p.template, list):
                raise bio.BiometriaError("PLANTILLA_INVALIDA", "El template facial debe ser una lista de números")
            coincide, medida = bio.comparar_facial(json.loads(fila.plantilla), p.template)
            detalle = f"distancia={medida:.4f} umbral<={bio.FACE_DISTANCE_THRESHOLD}"
        else:
            if p.codificacion != "base64" or not isinstance(p.template, str):
                raise bio.BiometriaError("PLANTILLA_INVALIDA", "El template de huella debe ser una cadena Base64")
            coincide, medida = bio.comparar_huellas(fila.plantilla, p.template)
            detalle = f"puntaje={medida} umbral>={bio.FINGER_MATCH_THRESHOLD}"
    except bio.BiometriaError as e:
        raise ApiError(e.status, e.codigo, e.mensaje)

    # Solo metadatos: documento enmascarado y la medida numérica. Nunca la plantilla.
    log.info("comparacion %s dni=%s %s coincide=%s", p.tipo_biometria, enmascarar_doc(p.numero_documento), detalle, coincide)
    return {"estado": "COINCIDE" if coincide else "NO_COINCIDE"}
