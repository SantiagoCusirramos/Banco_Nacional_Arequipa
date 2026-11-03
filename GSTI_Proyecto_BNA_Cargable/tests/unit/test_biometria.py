"""Biometría real: huellas con NBIS (imágenes sintéticas incluidas) y comparación facial por coseno."""
import io
import os
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from shared.biometria import plantillas as bio

HUELLAS = Path(__file__).resolve().parents[2] / "datos_prueba" / "huellas"


def leer(nombre: str) -> bytes:
    return (HUELLAS / nombre).read_bytes()


# ------------------------------------------------------------------ huellas
def test_huella_misma_vs_distinta():
    a, _ = bio.extraer_plantilla_huella(leer("huella_A.png"))
    a2, _ = bio.extraer_plantilla_huella(leer("huella_A_variante.png"))
    b, _ = bio.extraer_plantilla_huella(leer("huella_B.png"))
    mismo, p_mismo = bio.comparar_huellas(a, a2)
    otro, p_otro = bio.comparar_huellas(a, b)
    assert mismo and p_mismo >= bio.FINGER_MATCH_THRESHOLD
    assert not otro and p_otro < bio.FINGER_MATCH_THRESHOLD
    assert p_mismo > 3 * max(p_otro, 1)


def test_plantilla_huella_es_iso_19794_2_en_base64():
    import base64

    b64, metricas = bio.extraer_plantilla_huella(leer("huella_A.png"))
    crudo = base64.b64decode(b64, validate=True)
    assert crudo[:4] == b"FMR\x00"
    assert metricas["minucias"] >= bio.FINGER_MIN_MINUTIAE and metricas["calidad_nfiq2"] >= bio.FINGER_MIN_NFIQ2


def test_la_igualdad_de_base64_no_es_el_criterio():
    """Dos capturas del mismo dedo dan plantillas DISTINTAS en bytes y aun así coinciden biométricamente."""
    a, _ = bio.extraer_plantilla_huella(leer("huella_A.png"))
    a2, _ = bio.extraer_plantilla_huella(leer("huella_A_variante.png"))
    assert a != a2 and bio.comparar_huellas(a, a2)[0]


def test_imagen_sin_huella_se_rechaza():
    ruido = Image.fromarray((np.random.default_rng(1).random((300, 300)) * 255).astype("uint8"))
    buf = io.BytesIO(); ruido.save(buf, "PNG")
    with pytest.raises(bio.BiometriaError) as e:
        bio.extraer_plantilla_huella(buf.getvalue())
    assert e.value.codigo == "HUELLA_SIN_CARACTERISTICAS"
    # Ruido suavizado, imagen en blanco y degradado: tampoco son huellas.
    from PIL import ImageFilter

    suave = ruido.filter(ImageFilter.GaussianBlur(2)); b1 = io.BytesIO(); suave.save(b1, "PNG")
    blanco = io.BytesIO(); Image.new("L", (300, 300), 255).save(blanco, "PNG")
    grad = io.BytesIO(); Image.fromarray(np.tile(np.linspace(0, 255, 300), (300, 1)).astype("uint8")).save(grad, "PNG")
    for imagen in (b1.getvalue(), blanco.getvalue(), grad.getvalue()):
        with pytest.raises(bio.BiometriaError):
            bio.extraer_plantilla_huella(imagen)


@pytest.mark.parametrize("datos,codigo", [
    (b"", "IMAGEN_INVALIDA"),
    (b"esto no es una imagen", "IMAGEN_INVALIDA"),
    (b"GIF89a" + b"\x00" * 50, "IMAGEN_INVALIDA"),
])
def test_imagenes_invalidas(datos, codigo):
    with pytest.raises(bio.BiometriaError) as e:
        bio.extraer_plantilla_huella(datos)
    assert e.value.codigo == codigo


def test_formato_distinto_de_jpg_png_se_rechaza():
    buf = io.BytesIO(); Image.new("RGB", (200, 200), "white").save(buf, "BMP")
    with pytest.raises(bio.BiometriaError) as e:
        bio.abrir_imagen(buf.getvalue())
    assert e.value.codigo == "IMAGEN_INVALIDA"


def test_imagen_demasiado_pequena_o_grande():
    chica = io.BytesIO(); Image.new("RGB", (20, 20)).save(chica, "PNG")
    with pytest.raises(bio.BiometriaError):
        bio.abrir_imagen(chica.getvalue())
    with pytest.raises(bio.BiometriaError) as e:
        bio.abrir_imagen(b"\x00" * (bio.MAX_IMAGE_BYTES + 1))
    assert e.value.codigo == "IMAGEN_MUY_GRANDE"


@pytest.mark.parametrize("texto", ["!!!no-base64!!!", "AAAA", ""])
def test_plantilla_huella_invalida(texto):
    a, _ = bio.extraer_plantilla_huella(leer("huella_A.png"))
    with pytest.raises(bio.BiometriaError) as e:
        bio.comparar_huellas(a, texto)
    assert e.value.codigo == "PLANTILLA_INVALIDA"


# ------------------------------------------------------------------ rostro (comparación)
def vector(semilla: int):
    return list(np.random.default_rng(semilla).normal(0, 1, 512))


def test_facial_mismo_vector_coincide():
    v = vector(1)
    coincide, d = bio.comparar_facial(v, v)
    assert coincide and d == pytest.approx(0.0, abs=1e-9)


def test_facial_pequena_variacion_coincide():
    v = np.array(vector(1))
    ruido = v + np.random.default_rng(9).normal(0, 0.3, 512)
    coincide, d = bio.comparar_facial(list(v), list(ruido))
    assert coincide and 0 < d < bio.FACE_DISTANCE_THRESHOLD


def test_facial_vectores_distintos_no_coinciden():
    coincide, d = bio.comparar_facial(vector(1), vector(2))
    assert not coincide and d > bio.FACE_DISTANCE_THRESHOLD


@pytest.mark.parametrize("malo", [[0.0] * 512, [1.0] * 100, [float("nan")] * 512])
def test_facial_embedding_invalido(malo):
    with pytest.raises(bio.BiometriaError) as e:
        bio.comparar_facial(vector(1), malo)
    assert e.value.codigo == "PLANTILLA_INVALIDA"


# ------------------------------------------------------------------ rostro (extracción; requiere los pesos del modelo)
HAY_MODELO = (Path(os.getenv("DEEPFACE_HOME", str(Path.home()))) / ".deepface" / "weights" / "arcface_weights.h5").exists()


@pytest.mark.skipif(not HAY_MODELO, reason="No están los pesos de ArcFace (DEEPFACE_HOME)")
def test_imagen_sin_rostro_se_rechaza():
    ruido = Image.fromarray((np.random.default_rng(0).random((300, 300, 3)) * 255).astype("uint8"))
    buf = io.BytesIO(); ruido.save(buf, "JPEG")
    with pytest.raises(bio.BiometriaError) as e:
        bio.extraer_embedding_facial(buf.getvalue())
    assert e.value.codigo == "ROSTRO_NO_DETECTADO"
