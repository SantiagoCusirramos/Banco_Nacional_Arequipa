#!/usr/bin/env bash
# Construye y publica las 4 imágenes en Docker Hub (usuario edmaster1214, etiqueta latest).
# Requiere Docker en ejecución y haber hecho:  docker login -u edmaster1214
# Uso (desde la raíz del repositorio):  bash scripts/publicar_imagenes.sh
set -euo pipefail
cd "$(dirname "$0")/.."
export DOCKERHUB_USER=edmaster1214 BNA_TAG=latest
# nbis-py solo existe para Linux x86_64: en equipos con chip ARM (Mac M1/M2, etc.) las imágenes se emulan como amd64.
export BNA_PLATFORM=linux/amd64
docker compose build core bus reniec clientes
docker compose push core bus reniec clientes
echo "Imágenes publicadas: edmaster1214/bna-{core,bus,reniec,clientes}:latest"
