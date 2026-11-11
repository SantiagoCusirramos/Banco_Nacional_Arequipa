#!/usr/bin/env bash
# Todas las suites del repositorio, en contenedores: no hace falta Python ni Node
# en esta máquina. Uso: ./bna test
#
# Una suite "conocida" tiene una falla ya reportada en un issue de su responsable:
# se ejecuta y se informa, pero no hace fallar la orden.
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

PYTEST="python -m pytest -p no:cacheprovider -q -o addopts="
resumen=()
fallas=0

# correr NOMBRE bloqueante|conocida:<issue> orden...
correr() {
  local nombre="$1" clase="$2" inicio=$SECONDS
  shift 2
  echo
  echo "══ $nombre"
  if "$@"; then
    resumen+=("pasa     $nombre ($((SECONDS - inicio)) s)")
  elif [ "$clase" = bloqueante ]; then
    resumen+=("FALLA    $nombre")
    fallas=$((fallas + 1))
  else
    resumen+=("conocida $nombre: falla ya reportada en el issue #${clase#conocida:}")
  fi
}

en_backend() { docker run --rm bna/backend:local $PYTEST "$@"; }

correr "Imágenes" bloqueante docker compose build -q
correr "CORE legado" bloqueante en_backend
correr "CUENTAS" bloqueante en_backend CUENTAS/tests
correr "SOL" bloqueante docker run --rm bna/sol:local $PYTEST SOL/tests
correr "Seguridad" bloqueante docker run --rm bna/seguridad:local $PYTEST seguridad/tests
correr "COREDB, unitarias" bloqueante \
  docker run --rm bna/coredb:local sh -c "cd COREDB && $PYTEST"
correr "COREDB contra MySQL" bloqueante \
  env COREDB_IMAGEN_PRUEBAS=bna/coredb:local backend/COREDB/scripts/pruebas_integracion.sh
correr "Base integrada, despliegue" bloqueante database/pruebas/mysql/prueba_despliegue.sh
correr "Frontend, imagen de pruebas" bloqueante \
  docker build -q --target pruebas -f docker/frontend/Dockerfile -t bna/frontend-pruebas:local frontend
correr "Frontend, lint" bloqueante docker run --rm bna/frontend-pruebas:local npm run lint
correr "Frontend, pruebas" conocida:31 docker run --rm bna/frontend-pruebas:local npm test

if [ -z "$(docker compose ps -q 2>/dev/null)" ]; then
  correr "Producto, arranque" bloqueante ./bna up
fi
correr "Producto, flujo de extremo a extremo" bloqueante ./bna smoke

echo
echo "══ Resumen"
printf '  %s\n' "${resumen[@]}"
if [ "$fallas" -gt 0 ]; then
  echo "$fallas suites fallaron." >&2
  exit 1
fi
