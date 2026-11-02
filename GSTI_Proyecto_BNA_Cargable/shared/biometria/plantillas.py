"""Extracción y comparación de plantillas biométricas REALES.

- Rostro:  DeepFace + ArcFace -> embedding de 512 números; comparación por distancia coseno.
- Huella:  nbis-py (NBIS) -> minucias -> plantilla ISO/IEC 19794-2:2005 en Base64; comparación Bozorth3.

La MISMA configuración (modelo, detector, PPI, umbrales) se usa al registrar y al validar porque
ambos servicios importan este módulo. TensorFlow se importa solo cuando se extrae un rostro.
"""
import base64
import binascii
import io
import math
import os
import threading

import numpy as np
from PIL import Image, UnidentifiedImageError

# DeepFace usa Keras 2 (paquete tf-keras); debe fijarse antes de importar TensorFlow.
os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

from shared.esquemas import DIM_EMBEDDING, FORMATO_FACIAL, FORMATO_HUELLA

# ---- Configuración (variables de entorno, con valores por defecto documentados) ----
FACE_MODEL = "ArcFace"
FACE_DETECTOR = os.getenv("FACE_DETECTOR_BACKEND", "opencv")
# Distancia coseno máxima para aceptar (umbral de DeepFace para ArcFace + coseno = 0.68).
FACE_DISTANCE_THRESHOLD = float(os.getenv("FACE_COSINE_DISTANCE_THRESHOLD", "0.68"))
FINGER_PPI = float(os.getenv("FINGERPRINT_PPI", "500"))
FINGER_MIN_QUALITY = float(os.getenv("FINGERPRINT_MIN_QUALITY", "0.0"))
FINGER_MIN_MINUTIAE = int(os.getenv("FINGERPRINT_MIN_MINUTIAE", "15"))
# Puertas de calidad: una imagen de ruido también produce "minucias", por eso no basta con contarlas.
# NFIQ2 (ISO/IEC 29794-4, 0-100): el ruido puntúa ~29 y las huellas sintéticas incluidas 52-61.
FINGER_MIN_NFIQ2 = int(os.getenv("FINGERPRINT_MIN_NFIQ2", "35"))
# Fiabilidad media de las minucias (0-1): ruido ~0.19, huellas sintéticas >= 0.48.
FINGER_MIN_RELIABILITY = float(os.getenv("FINGERPRINT_MIN_RELIABILITY", "0.25"))
# Puntaje Bozorth3 mínimo para aceptar (la documentación de nbis-py indica que >50 es coincidencia probable).
FINGER_MATCH_THRESHOLD = int(os.getenv("FINGERPRINT_MATCH_THRESHOLD", "50"))
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_MB", "5")) * 1024 * 1024

# Se guardan junto a cada plantilla para detectar incompatibilidades si algún día cambian.
ALGORITMO_FACIAL = f"deepface-{FACE_MODEL}-{FACE_DETECTOR}-align"
ALGORITMO_HUELLA = f"nbis-py-bozorth3-ppi{int(FINGER_PPI)}"
VERSION_PLANTILLAS = "1"

_lock_tf = threading.Lock()
_extractor_nbis = None


class BiometriaError(Exception):
    def __init__(self, codigo: str, mensaje: str, status: int = 422):
        super().__init__(mensaje)
        self.codigo, self.mensaje, self.status = codigo, mensaje, status


# ---------------------------------------------------------------- imágenes
def abrir_imagen(datos: bytes) -> Image.Image:
    """Valida tamaño y formato (solo JPG/PNG reales, no se confía en la extensión)."""
    if not datos:
        raise BiometriaError("IMAGEN_INVALIDA", "El archivo está vacío")
    if len(datos) > MAX_IMAGE_BYTES:
        raise BiometriaError("IMAGEN_MUY_GRANDE", f"La imagen supera {MAX_IMAGE_BYTES // (1024 * 1024)} MB", 413)
    try:
        img = Image.open(io.BytesIO(datos))
        formato = img.format
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise BiometriaError("IMAGEN_INVALIDA", "El archivo no es una imagen JPG o PNG válida")
    if formato not in ("JPEG", "PNG"):
        raise BiometriaError("IMAGEN_INVALIDA", "Solo se aceptan imágenes JPG o PNG")
    if min(img.size) < 64 or max(img.size) > 4096:
        raise BiometriaError("IMAGEN_INVALIDA", "Las dimensiones deben estar entre 64 y 4096 píxeles")
    return img


# ---------------------------------------------------------------- rostro
def extraer_embedding_facial(datos: bytes) -> list[float]:
    img = abrir_imagen(datos).convert("RGB")
    bgr = np.asarray(img)[:, :, ::-1].copy()  # DeepFace espera BGR cuando recibe un arreglo
    with _lock_tf:  # un modelo en memoria, una extracción a la vez
        from deepface import DeepFace

        try:
            rostros = DeepFace.represent(
                img_path=bgr, model_name=FACE_MODEL, detector_backend=FACE_DETECTOR,
                enforce_detection=True, align=True,
            )
        except ValueError as e:
            if "Face could not be detected" in str(e):
                raise BiometriaError("ROSTRO_NO_DETECTADO", "No se detectó ningún rostro en la imagen")
            raise BiometriaError("MODELO_NO_DISPONIBLE", "No se pudo cargar el modelo facial", 500)
    if len(rostros) != 1:
        raise BiometriaError("MULTIPLES_ROSTROS", "La imagen debe contener exactamente un rostro")
    emb = [float(x) for x in rostros[0]["embedding"]]
    if len(emb) != DIM_EMBEDDING:
        raise BiometriaError("MODELO_NO_DISPONIBLE", "El modelo devolvió un embedding inesperado", 500)
    return emb


def validar_embedding(emb: list[float]) -> np.ndarray:
    v = np.asarray(emb, dtype=np.float64)
    if v.shape != (DIM_EMBEDDING,) or not np.all(np.isfinite(v)) or float(np.linalg.norm(v)) == 0.0:
        raise BiometriaError("PLANTILLA_INVALIDA", "El embedding facial no es válido")
    return v


def distancia_coseno(a: list[float], b: list[float]) -> float:
    va, vb = validar_embedding(a), validar_embedding(b)
    return float(1.0 - np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb)))


def comparar_facial(almacenado: list[float], recibido: list[float]) -> tuple[bool, float]:
    d = distancia_coseno(almacenado, recibido)
    return d <= FACE_DISTANCE_THRESHOLD, d


# ---------------------------------------------------------------- huella
def _nbis():
    global _extractor_nbis
    if _extractor_nbis is None:
        import nbis

        _extractor_nbis = nbis.new_nbis_extractor(nbis.NbisExtractorSettings(
            min_quality=FINGER_MIN_QUALITY, get_center=False, check_fingerprint=False,
            compute_nfiq2=True, ppi=FINGER_PPI,
        ))
    return _extractor_nbis


def extraer_plantilla_huella(datos: bytes) -> tuple[str, dict]:
    """Imagen -> (plantilla ISO 19794-2:2005 en Base64, {"minucias": n, "calidad_nfiq2": q}).

    Se rechaza la imagen si no supera las puertas de calidad (minucias, NFIQ2 y fiabilidad media).
    """
    img = abrir_imagen(datos).convert("L")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    motivo = None
    try:
        minucias = _nbis().extract_minutiae(buf.getvalue())
        lista = minucias.get()
        cantidad = len(lista)
        calidad = minucias.quality()
        nfiq2 = int(getattr(calidad, "score", calidad))
        fiabilidad = sum(x.reliability() for x in lista) / cantidad if cantidad else 0.0
        if cantidad < FINGER_MIN_MINUTIAE:
            motivo = f"solo {cantidad} minucias (mínimo {FINGER_MIN_MINUTIAE})"
        elif nfiq2 < FINGER_MIN_NFIQ2:
            motivo = f"calidad NFIQ2 {nfiq2} (mínimo {FINGER_MIN_NFIQ2})"
        elif fiabilidad < FINGER_MIN_RELIABILITY:
            motivo = f"fiabilidad media {fiabilidad:.2f} (mínimo {FINGER_MIN_RELIABILITY})"
        else:
            iso = bytes(minucias.to_iso_19794_2_2005())
    except Exception:  # NBIS no pudo procesar la imagen (p. ej. Nfiq2ComputeFailed)
        motivo = "NBIS no pudo extraer características de la imagen"
    if motivo:
        raise BiometriaError("HUELLA_SIN_CARACTERISTICAS", f"La imagen no parece una huella utilizable: {motivo}")
    return base64.b64encode(iso).decode("ascii"), {"minucias": cantidad, "calidad_nfiq2": nfiq2}


def _cargar_iso(b64: str):
    try:
        crudo = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError):
        raise BiometriaError("PLANTILLA_INVALIDA", "El template de huella no es Base64 válido")
    if not crudo.startswith(b"FMR\x00") or len(crudo) > 48_000:
        raise BiometriaError("PLANTILLA_INVALIDA", "El template de huella no es ISO/IEC 19794-2:2005")
    try:
        return _nbis().load_iso_19794_2_2005(crudo)
    except Exception:
        raise BiometriaError("PLANTILLA_INVALIDA", "El template de huella no se pudo interpretar")


def comparar_huellas(almacenada_b64: str, recibida_b64: str) -> tuple[bool, int]:
    a, b = _cargar_iso(almacenada_b64), _cargar_iso(recibida_b64)
    puntaje = int(a.compare(b))
    return puntaje >= FINGER_MATCH_THRESHOLD, puntaje
