#!/usr/bin/env bash
# Pruebas de Desembolso contra la base integrada (bna-core-db, con sus datos de desarrollo) y
# COREDB reales, en contenedores nuevos: no hace falta Python ni MySQL en esta máquina. El
# administrador y los usuarios de servicio svc-desembolso y svc-evaluacion (este registra los
# expedientes que luego se aprueban) se crean con los scripts de arranque de COREDB, como en
# compose. Al terminar elimina los contenedores, sus volúmenes y la red. Las claves son
# aleatorias y de esta ejecución.
#
# Uso, desde cualquier carpeta: backend/DESEMBOLSO/scripts/pruebas_integracion.sh [argumentos de pytest]
#   DESEMBOLSO_IMAGEN_PRUEBAS  imagen que corre las pruebas (bna/backend:local)
#   DESEMBOLSO_IMAGEN_COREDB   imagen de COREDB (bna/coredb:local)
set -euo pipefail

BACKEND="$(cd "$(dirname "$0")/../.." && pwd)"
RAIZ="$(cd "$BACKEND/.." && pwd)"
IMAGEN="${DESEMBOLSO_IMAGEN_PRUEBAS:-bna/backend:local}"
IMAGEN_COREDB="${DESEMBOLSO_IMAGEN_COREDB:-bna/coredb:local}"
PROYECTO="desembolso-pruebas-$$"
RED="${PROYECTO}_default"
COREDB="${PROYECTO}-coredb"
PUERTO="${DESEMBOLSO_PUERTO_PRUEBAS:-3329}"
ENTORNO="$(mktemp)"

compose() {
  docker compose -p "$PROYECTO" -f "$RAIZ/docker-compose.coredb.yml" \
    -f "$RAIZ/docker-compose.coredb.dev.yml" --env-file "$ENTORNO" "$@"
}
limpiar() {
  # -v: el contenedor de COREDB no deja volúmenes anónimos.
  docker rm -fv "$COREDB" >/dev/null 2>&1 || true
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
DESEMBOLSO_COREDB_SECRETO=$(openssl rand -hex 24)
EVALUACION_COREDB_SECRETO=$(openssl rand -hex 24)
VARS

compose up -d --wait >/dev/null
set -a
. "$ENTORNO"
set +a

con_coredb() {
  docker run --rm --network "$RED" -e CORE_DB_HOST=bna-core-db -e CORE_DB_PORT=3306 \
    -e CORE_DB_APP_USER=bna_app_user -e CORE_DB_APP_PASSWORD -e CORE_DB_JWT_CLAVE "$@"
}

docker run -d --name "$COREDB" --network "$RED" -e CORE_DB_HOST=bna-core-db -e CORE_DB_PORT=3306 \
  -e CORE_DB_APP_USER=bna_app_user -e CORE_DB_APP_PASSWORD -e CORE_DB_JWT_CLAVE \
  "$IMAGEN_COREDB" uvicorn COREDB.main:app --host 0.0.0.0 --port 8012 >/dev/null

con_coredb -e CORE_DB_ADMIN_INICIAL_PASSWORD="$BNA_ADMIN_PASSWORD" "$IMAGEN_COREDB" \
  python -m COREDB.scripts.crear_administrador --username admin --nombre "Administrador de pruebas" --si-falta
con_coredb -e CORE_DB_SERVICIO_SECRETO="$DESEMBOLSO_COREDB_SECRETO" "$IMAGEN_COREDB" \
  python -m COREDB.scripts.crear_servicio --modulo DESEMBOLSO --username svc-desembolso --nombre Desembolso
con_coredb -e CORE_DB_SERVICIO_SECRETO="$EVALUACION_COREDB_SECRETO" "$IMAGEN_COREDB" \
  python -m COREDB.scripts.crear_servicio --modulo EVALUACION --username svc-evaluacion --nombre Evaluación

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

docker run --rm --network "$RED" \
  -e DESEMBOLSO_TEST_COREDB="http://$COREDB:8012" \
  -e DESEMBOLSO_TEST_ADMIN_USUARIO=admin \
  -e DESEMBOLSO_TEST_ADMIN_PASSWORD="$BNA_ADMIN_PASSWORD" \
  -e DESEMBOLSO_TEST_SERVICIO_USUARIO=svc-desembolso \
  -e DESEMBOLSO_TEST_SERVICIO_SECRETO="$DESEMBOLSO_COREDB_SECRETO" \
  -e DESEMBOLSO_TEST_EVALUACION_USUARIO=svc-evaluacion \
  -e DESEMBOLSO_TEST_EVALUACION_SECRETO="$EVALUACION_COREDB_SECRETO" \
  -e DESEMBOLSO_TEST_DB_HOST=bna-core-db \
  -e DESEMBOLSO_TEST_DB_ADMIN_PASSWORD="$CORE_DB_ADMIN_PASSWORD" \
  "$IMAGEN" python -m pytest -p no:cacheprovider -q -o addopts= DESEMBOLSO/tests "$@"
