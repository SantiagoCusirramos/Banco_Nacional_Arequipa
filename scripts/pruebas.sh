#!/usr/bin/env bash
# Todas las suites del repositorio, en contenedores: no hace falta Python ni Node
# en esta máquina. Uso: ./bna test
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

if [ -z "$(docker compose ps -q 2>/dev/null)" ]; then
  correr "Producto, arranque" ./bna up
fi
correr "Producto, flujo de extremo a extremo" ./bna smoke

echo
echo "══ Resumen"
printf '  %s\n' "${resumen[@]}"
if [ "$fallas" -gt 0 ]; then
  echo "$fallas suites fallaron." >&2
  exit 1
fi
