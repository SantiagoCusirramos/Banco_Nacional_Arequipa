#!/usr/bin/env bash
# Pruebas de Seguridad contra la base integrada (bna-core-db, con sus datos de desarrollo) y
# COREDB reales, a través del Bus, en contenedores nuevos: no hace falta Python ni MySQL en esta
# máquina. El administrador y svc-seguridad se crean con los scripts de arranque de COREDB, como
# en compose. Al terminar elimina los contenedores, sus volúmenes y la red. Las claves son
# aleatorias y de esta ejecución.
#
# Uso, desde cualquier carpeta: backend/seguridad/scripts/pruebas_integracion.sh [argumentos de pytest]
#   SEGURIDAD_IMAGEN_PRUEBAS  imagen que corre las pruebas (bna/seguridad:local)
#   SEGURIDAD_IMAGEN_COREDB   imagen de COREDB (bna/coredb:local)
#   SEGURIDAD_IMAGEN_BUS      imagen del Bus (bna/backend:local)
set -euo pipefail

BACKEND="$(cd "$(dirname "$0")/../.." && pwd)"
RAIZ="$(cd "$BACKEND/.." && pwd)"
IMAGEN="${SEGURIDAD_IMAGEN_PRUEBAS:-bna/seguridad:local}"
IMAGEN_COREDB="${SEGURIDAD_IMAGEN_COREDB:-bna/coredb:local}"
IMAGEN_BUS="${SEGURIDAD_IMAGEN_BUS:-bna/backend:local}"
PROYECTO="seguridad-pruebas-$$"
RED="${PROYECTO}_default"
COREDB="${PROYECTO}-coredb"
BUS="${PROYECTO}-bus"
PUERTO="${SEGURIDAD_PUERTO_PRUEBAS:-3332}"
ENTORNO="$(mktemp)"

compose() {
  docker compose -p "$PROYECTO" -f "$RAIZ/docker-compose.coredb.yml" \
    -f "$RAIZ/docker-compose.coredb.dev.yml" --env-file "$ENTORNO" "$@"
}
limpiar() {
  docker rm -fv "$COREDB" "$BUS" >/dev/null 2>&1 || true
  compose down -v >/dev/null 2>&1 || true
  rm -f "$ENTORNO"
}
trap limpiar EXIT

chmod 600 "$ENTORNO"
cat > "$ENTORNO" <<VARS
CORE_DB_ROOT_PASSWORD=$(openssl rand -hex 16)
CORE_DB_APP_PASSWORD=$(openssl rand -hex 16)
CORE_DB_ADMIN_PASSWORD=$(openssl rand -hex 16)
CORE_DB_SEGURIDAD_PASSWORD=$(openssl rand -hex 16)
CORE_DB_JWT_CLAVE=$(openssl rand -hex 32)
CORE_DB_PORT=$PUERTO
BNA_ADMIN_PASSWORD=$(openssl rand -hex 16)
SEGURIDAD_COREDB_SECRETO=$(openssl rand -hex 24)
VARS

compose up -d --wait >/dev/null
set -a
. "$ENTORNO"
set +a

# COREDB con la cuenta bna_seguridad_user de la base: la usa solo el desbloqueo de tarjetas.
con_coredb() {
  docker run --rm --network "$RED" -e CORE_DB_HOST=bna-core-db -e CORE_DB_PORT=3306 \
    -e CORE_DB_APP_USER=bna_app_user -e CORE_DB_APP_PASSWORD -e CORE_DB_JWT_CLAVE "$@"
}
docker run -d --name "$COREDB" --network "$RED" -e CORE_DB_HOST=bna-core-db -e CORE_DB_PORT=3306 \
  -e CORE_DB_APP_USER=bna_app_user -e CORE_DB_APP_PASSWORD -e CORE_DB_JWT_CLAVE -e CORE_DB_SEGURIDAD_PASSWORD \
  "$IMAGEN_COREDB" uvicorn COREDB.main:app --host 0.0.0.0 --port 8012 >/dev/null

con_coredb -e CORE_DB_ADMIN_INICIAL_PASSWORD="$BNA_ADMIN_PASSWORD" "$IMAGEN_COREDB" \
  python -m COREDB.scripts.crear_administrador --username admin --nombre "Administrador de pruebas" --si-falta
con_coredb -e CORE_DB_SERVICIO_SECRETO="$SEGURIDAD_COREDB_SECRETO" "$IMAGEN_COREDB" \
  python -m COREDB.scripts.crear_servicio --modulo SEGURIDAD --username svc-seguridad --nombre Seguridad

listo=0
for _ in $(seq 1 60); do
  if docker exec "$COREDB" python -c \
    'import urllib.request as u; u.urlopen("http://127.0.0.1:8012/coredb/salud", timeout=3)' >/dev/null 2>&1; then
    listo=1
    break
  fi
  sleep 1
done
if [ "$listo" != 1 ]; then
  echo "COREDB de pruebas no arrancó:" >&2
  docker logs --tail 30 "$COREDB" >&2
  exit 1
fi

# Como en el producto: Seguridad y las pruebas llegan a COREDB a través del Bus.
. "$RAIZ/scripts/bus_de_pruebas.sh"
bus_de_pruebas_levantar "$RED" "$BUS" "$IMAGEN_BUS" "http://$COREDB:8012" SEGURIDAD

docker run --rm --network "$RED" \
  -e SEGURIDAD_TEST_COREDB="$BUS_PRUEBAS_COREDB" \
  -e SEGURIDAD_TEST_BUS_TOKEN="$BUS_PRUEBAS_TOKEN_MODULO" \
  -e SEGURIDAD_TEST_BUS_TOKEN_PRUEBAS="$BUS_PRUEBAS_TOKEN_PRUEBAS" \
  -e SEGURIDAD_TEST_ADMIN_PASSWORD="$BNA_ADMIN_PASSWORD" \
  -e SEGURIDAD_TEST_SERVICIO_SECRETO="$SEGURIDAD_COREDB_SECRETO" \
  "$IMAGEN" python -m pytest -p no:cacheprovider -q -o addopts= seguridad/tests "$@"
bus_de_pruebas_comprobar "$BUS" SEGURIDAD
