#!/usr/bin/env bash
# Pruebas de integración del CORE legado contra un MySQL real con el esquema `bna`.
# Levanta solo `db-aux` de compose.yaml en un proyecto propio, con claves aleatorias
# de esta ejecución y un volumen nuevo; corre CORE/tests/integracion en un contenedor
# de la imagen del backend, dentro de la red de esa base, y elimina contenedor y
# volumen al terminar. No usa ni toca el producto levantado (proyecto `bna`).
#
# Uso, desde cualquier carpeta: backend/CORE/scripts/pruebas_integracion.sh [argumentos de pytest]
# CORE_IMAGEN_PRUEBAS elige la imagen (por omisión bna/backend:local): prueba el
# código que está en ella.
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/../../.." && pwd)"
IMAGEN="${CORE_IMAGEN_PRUEBAS:-bna/backend:local}"
PROYECTO="bna-prueba-core-legado-$$"
TEMPORAL="$(mktemp -d)"

compose() { docker compose -p "$PROYECTO" --project-directory "$RAIZ" -f "$RAIZ/compose.yaml" --env-file "$TEMPORAL/.env" "$@"; }
limpiar() { compose down -v --remove-orphans >/dev/null 2>&1 || true; rm -rf "$TEMPORAL"; }
trap limpiar EXIT

# .env propio: las variables de .env.example, con valores aleatorios nuevos.
cp "$RAIZ/.env.example" "$TEMPORAL/.env.example"
"$RAIZ/scripts/generar_env.sh" "$TEMPORAL" >/dev/null
valor() { grep -E "^$1=" "$TEMPORAL/.env" | tail -n 1 | cut -d= -f2-; }

compose up -d --wait db-aux >/dev/null
docker run --rm --network "${PROYECTO}_default" \
  -e BNA_INTEGRACION_MYSQL=1 -e DB_HOST=db-aux -e DB_PORT=3306 -e DB_NAME=bna \
  -e DB_USER=bna_user -e DB_PASSWORD="$(valor LEGADO_DB_PASSWORD)" \
  -e SECRET_KEY="$(valor LEGADO_SECRET_KEY)" \
  "$IMAGEN" python -m pytest -p no:cacheprovider -q -o addopts= CORE/tests/integracion "$@"
