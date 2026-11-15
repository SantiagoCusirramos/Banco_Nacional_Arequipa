#!/usr/bin/env bash
# Pruebas de Desembolso contra un MySQL 8.4 nuevo, en contenedores: no hace falta Python ni MySQL
# en esta máquina. Al terminar elimina el contenedor y la red. La clave es aleatoria y de esta ejecución.
#
# Uso, desde cualquier carpeta: backend/DESEMBOLSO/scripts/pruebas_integracion.sh [argumentos de pytest]
# DESEMBOLSO_IMAGEN_PRUEBAS=<imagen> elige la imagen que corre las pruebas (bna/backend:local).
set -euo pipefail

BACKEND="$(cd "$(dirname "$0")/../.." && pwd)"
RAIZ="$(cd "$BACKEND/.." && pwd)"
IMAGEN="${DESEMBOLSO_IMAGEN_PRUEBAS:-bna/backend:local}"
# La misma versión de MySQL que db-aux.
MYSQL_IMAGEN="$(sed -n 's/^ARG MYSQL_IMAGE=//p' "$RAIZ/docker/db-aux/Dockerfile")"
RED="desembolso-pruebas-$$"
SERVIDOR="desembolso-pruebas-mysql-$$"
CLAVE="$(openssl rand -hex 16)"

limpiar() {
  docker rm -f "$SERVIDOR" >/dev/null 2>&1 || true
  docker network rm "$RED" >/dev/null 2>&1 || true
}
trap limpiar EXIT

docker network create "$RED" >/dev/null
docker run -d --name "$SERVIDOR" --network "$RED" -e MYSQL_ROOT_PASSWORD="$CLAVE" "$MYSQL_IMAGEN" >/dev/null

# Por TCP: el servidor de inicialización no escucha por TCP, así que responde cuando terminó de arrancar.
listo=0
for _ in $(seq 1 90); do
  if docker exec -e MYSQL_PWD="$CLAVE" "$SERVIDOR" mysql -uroot -h127.0.0.1 --protocol=TCP -e 'SELECT 1' >/dev/null 2>&1; then
    listo=1
    break
  fi
  sleep 2
done
if [ "$listo" != 1 ]; then
  echo "MySQL de pruebas no arrancó:" >&2
  docker logs --tail 30 "$SERVIDOR" >&2
  exit 1
fi

docker run --rm --network "$RED" \
  -e DESEMBOLSO_TEST_MYSQL="mysql+pymysql://root:$CLAVE@$SERVIDOR:3306" \
  "$IMAGEN" python -m pytest -p no:cacheprovider -q -o addopts= DESEMBOLSO/tests "$@"
