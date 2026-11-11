# Imagen de un servicio Python del backend. El contexto de construcción es backend/.
#   REQUISITOS  archivo de requisitos del servicio
# El servicio que corre lo decide `command` en compose.yaml o en el manifiesto.
ARG PYTHON_IMAGE=python:3.11-slim@sha256:07d4824036af339fa1b6ef769cc99d9c10a141769538b52b3b597c84f7a7b535
FROM ${PYTHON_IMAGE}

ARG REQUISITOS=requirements.txt
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY ${REQUISITOS} /tmp/requisitos.txt
# /datos es para el servicio que guarda un archivo (Seguridad, en un volumen).
RUN pip install --no-cache-dir -r /tmp/requisitos.txt \
    && useradd --uid 10001 --create-home bna \
    && mkdir /datos && chown bna:bna /datos

# backend/.dockerignore deja fuera los .env.
COPY . .
# El CORE legado guarda su catálogo de permisos en CORE/data/rbac.json y lo
# reescribe al asignar un permiso: es lo único del código que el servicio puede escribir.
RUN chown -R bna:bna CORE/data
USER bna
