#!/usr/bin/env bash
# Levanta la base con los datos de desarrollo en un volumen nuevo, ejecuta las
# pruebas de COREDB y elimina el contenedor y el volumen. Las claves son aleatorias
# y de esta ejecución.
#
# Uso, desde cualquier carpeta: backend/COREDB/scripts/pruebas_integracion.sh [argumentos de pytest]
set -euo pipefail

BACKEND="$(cd "$(dirname "$0")/../.." && pwd)"
RAIZ="$(cd "$BACKEND/.." && pwd)"
ENTORNO="$(mktemp)"
PROYECTO="coredb-pruebas-$$"
PUERTO="${COREDB_PUERTO_PRUEBAS:-3327}"
PYTHON="${PYTHON:-python}"

compose() {
  docker compose -p "$PROYECTO" -f "$RAIZ/docker-compose.coredb.yml" \
    -f "$RAIZ/docker-compose.coredb.dev.yml" --env-file "$ENTORNO" "$@"
}
limpiar() { compose down -v >/dev/null 2>&1 || true; rm -f "$ENTORNO"; }
trap limpiar EXIT

chmod 600 "$ENTORNO"
cat > "$ENTORNO" <<VARS
CORE_DB_ROOT_PASSWORD=$(openssl rand -hex 16)
CORE_DB_APP_PASSWORD=$(openssl rand -hex 16)
CORE_DB_ADMIN_PASSWORD=$(openssl rand -hex 16)
CORE_DB_SEGURIDAD_PASSWORD=$(openssl rand -hex 16)
CORE_DB_PORT=$PUERTO
VARS

compose up -d --wait >/dev/null
set -a
. "$ENTORNO"
set +a
cd "$BACKEND/COREDB"
COREDB_INTEGRACION=1 CORE_DB_HOST=127.0.0.1 PYTHONDONTWRITEBYTECODE=1 \
  "$PYTHON" -m pytest -p no:cacheprovider -q "$@"
