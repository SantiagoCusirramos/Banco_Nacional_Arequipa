# Contexto de construcción: la RAÍZ del proyecto (ver docker-compose.yml)
FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app HOME=/tmp \
    DEEPFACE_HOME=/models TF_USE_LEGACY_KERAS=1 TF_CPP_MIN_LOG_LEVEL=2
WORKDIR /app

# --- Capas pesadas, idénticas en RENIEC y Clientes (Docker las reutiliza) ---
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY shared/requirements-bio.txt ./requirements-bio.txt
RUN pip install --no-cache-dir -r requirements-bio.txt
COPY shared/__init__.py ./shared/__init__.py
COPY shared/biometria/__init__.py shared/biometria/descargar_modelos.py ./shared/biometria/
# Modelos descargados UNA vez al construir la imagen (con SHA-256): el contenedor no baja nada al arrancar.
RUN python -m shared.biometria.descargar_modelos \
 && python -c "from deepface import DeepFace; DeepFace.build_model(model_name='ArcFace', task='facial_recognition'); print('ArcFace cargado sin red')"

# --- Capas propias del servicio ---
COPY clientes/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/biometria/plantillas.py ./shared/biometria/plantillas.py
COPY shared/comun.py shared/esquemas.py ./shared/
COPY shared/ui ./shared/ui
COPY clientes/app ./app
COPY clientes/templates ./templates
COPY clientes/static ./static

USER 10001
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s --start-period=90s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/salud', timeout=4).status == 200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
