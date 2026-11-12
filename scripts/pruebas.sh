#!/usr/bin/env bash
# Todas las suites del repositorio, en contenedores: no hace falta Python ni Node
# en esta máquina. Al terminar no deja contenedores ni volúmenes que no existieran
# antes. Uso: ./bna test
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

PYTEST="python -m pytest -p no:cacheprovider -q -o addopts="
resumen=()
fallas=0

# correr NOMBRE orden...
correr() {
  local nombre="$1" inicio=$SECONDS
  shift
  echo
  echo "══ $nombre"
  if "$@"; then
    resumen+=("pasa   $nombre ($((SECONDS - inicio)) s)")
  else
    resumen+=("FALLA  $nombre")
    fallas=$((fallas + 1))
  fi
}

en_backend() { docker run --rm bna/backend:local $PYTEST "$@"; }

# compose.yaml exige las variables de .env incluso para construir.
scripts/generar_env.sh "$RAIZ" || exit 1

# Si el producto no tenía contenedores ni volúmenes al empezar, los que haya al
# terminar los creó esta corrida: se eliminan, también si se interrumpe. Si ya
# existía, sus datos no se tocan.
proyecto="$(docker compose config 2>/dev/null | sed -n 's/^name: //p' | head -n 1)"
limpiar_al_salir=0
if [ -n "$proyecto" ] && [ -z "$(docker compose ps -aq 2>/dev/null)" ] \
  && [ -z "$(docker volume ls -q --filter "label=com.docker.compose.project=$proyecto")" ]; then
  limpiar_al_salir=1
fi

limpiar() {
  [ "$limpiar_al_salir" = 1 ] || return 0
  [ -n "$(docker compose ps -aq 2>/dev/null)" ] || return 0
  echo
  if [ "$fallas" -gt 0 ]; then
    echo "══ Estado y registros de los servicios"
    docker compose ps -a || true
    docker compose logs --tail=80 || true
    echo
  fi
  echo "══ Limpieza: se eliminan los contenedores y volúmenes de esta corrida"
  docker compose down -v --remove-orphans || true
}
trap limpiar EXIT
trap 'exit 130' INT TERM
correr "Imágenes" docker compose build -q
correr "CORE legado" en_backend
correr "CUENTAS" en_backend CUENTAS/tests
correr "SOL" docker run --rm bna/sol:local $PYTEST SOL/tests
correr "Seguridad" docker run --rm bna/seguridad:local $PYTEST seguridad/tests
correr "COREDB, unitarias" \
  docker run --rm bna/coredb:local sh -c "cd COREDB && $PYTEST"
correr "COREDB contra MySQL" \
  env COREDB_IMAGEN_PRUEBAS=bna/coredb:local backend/COREDB/scripts/pruebas_integracion.sh
correr "Base integrada, despliegue" database/pruebas/mysql/prueba_despliegue.sh
correr "Frontend, imagen de pruebas" \
  docker build -q --target pruebas -f docker/frontend/Dockerfile -t bna/frontend-pruebas:local frontend
correr "Frontend, lint" docker run --rm bna/frontend-pruebas:local npm run lint
correr "Frontend, pruebas" docker run --rm bna/frontend-pruebas:local npm test

# Siempre: si el producto ya está levantado, recrea los servicios cuya imagen cambió.
correr "Producto, arranque" ./bna up
correr "Producto, flujo de extremo a extremo" ./bna smoke

echo
echo "══ Resumen"
printf '  %s\n' "${resumen[@]}"
if [ "$fallas" -gt 0 ]; then
  echo "$fallas suites fallaron." >&2
  exit 1
fi
