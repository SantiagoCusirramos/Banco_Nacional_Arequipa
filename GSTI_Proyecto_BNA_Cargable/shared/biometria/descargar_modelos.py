"""Descarga (con verificación SHA-256) los archivos del modelo facial para que NINGÚN contenedor los baje al arrancar.

Se ejecuta durante `docker build`. También sirve para uso local:
    DEEPFACE_HOME=./modelos python -m shared.biometria.descargar_modelos
Deja los archivos en $DEEPFACE_HOME/.deepface/weights, que es donde DeepFace los busca.
"""
import hashlib
import os
import sys
import urllib.request
from pathlib import Path

ARCHIVOS = [
    ("arcface_weights.h5", "https://github.com/serengil/deepface_models/releases/download/v1.0/arcface_weights.h5",
     "6336979c0c602cae08d1122a66f4dfb862d059bbcd8ef80306aef2b2249b0c93"),
    ("haarcascade_frontalface_default.xml", "https://raw.githubusercontent.com/opencv/opencv/4.9.0/data/haarcascades/haarcascade_frontalface_default.xml",
     "0f7d4527844eb514d4a4948e822da90fbb16a34a0bbbbc6adc6498747a5aafb0"),
    ("haarcascade_eye.xml", "https://raw.githubusercontent.com/opencv/opencv/4.9.0/data/haarcascades/haarcascade_eye.xml",
     "71cc64fc305a355dc60067880f6fbbd43dd155bd63ee3844661a1bda34b2fd8c"),
]


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def main() -> None:
    destino = Path(os.environ.get("DEEPFACE_HOME", str(Path.home()))) / ".deepface" / "weights"
    destino.mkdir(parents=True, exist_ok=True)
    for nombre, url, esperado in ARCHIVOS:
        ruta = destino / nombre
        if not (ruta.exists() and sha256(ruta) == esperado):
            print(f"Descargando {nombre} ...", flush=True)
            urllib.request.urlretrieve(url, ruta)
        if sha256(ruta) != esperado:
            sys.exit(f"ERROR: la suma SHA-256 de {nombre} no coincide; el archivo descargado no es el esperado")
        print(f"OK {nombre}")


if __name__ == "__main__":
    main()
