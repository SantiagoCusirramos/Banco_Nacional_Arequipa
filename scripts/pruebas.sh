#!/usr/bin/env bash
# Todas las suites del repositorio, en contenedores: no hace falta Python ni Node
# en esta máquina. Uso: ./bna test
#
# Cada corrida es independiente de las demás (por ejemplo, desde otro worktree): usa su propio
# proyecto de Compose (BNA_PROYECTO; por omisión bna-prueba-<rama>-<pid>), sus propias etiquetas
# de imagen (BNA_ETIQUETA_LOCAL, por omisión el nombre del proyecto) y no publica puertos en el
# anfitrión (compose.sin-puertos.yaml): las suites y el flujo corren dentro de las redes de
# Compose. Al terminar, también si se interrumpe, elimina los contenedores, redes y volúmenes de
# su proyecto y sus etiquetas de imagen, y nada más.
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

en_backend() { docker run --rm "bna/backend:$BNA_ETIQUETA_LOCAL" $PYTEST "$@"; }

# Git Bash (Windows) convierte en rutas de Windows los argumentos que empiezan con /,
# también las rutas de dentro del contenedor (/repo, /aviso). Para los montajes se
# desactiva esa conversión y la carpeta del host se pasa ya en forma de Windows.
RAIZ_HOST="$RAIZ"
case "$(uname -s)" in MINGW*|MSYS*) RAIZ_HOST="$(cd "$RAIZ" && pwd -W)" ;; esac
docker_montado() { MSYS_NO_PATHCONV=1 docker "$@"; }

# compose.yaml exige las variables de .env incluso para construir.
scripts/generar_env.sh "$RAIZ" || exit 1

if [ -z "${BNA_PROYECTO:-}" ]; then
  rama="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  rama="$(printf '%s' "$rama" | tr 'A-Z' 'a-z' | tr -c 'a-z0-9' '-' | cut -c1-24 | sed 's/^-*//; s/-*$//')"
  BNA_PROYECTO="bna-prueba-${rama:+$rama-}$$"
fi
# `bna` es el producto de `./bna up`: una corrida nunca lo usa ni lo borra.
if [ "$BNA_PROYECTO" = bna ]; then
  echo "BNA_PROYECTO=bna es el producto de ./bna up: las pruebas usan otro proyecto (sin BNA_PROYECTO, uno propio)." >&2
  exit 2
fi
BNA_ETIQUETA_LOCAL="${BNA_ETIQUETA_LOCAL:-$BNA_PROYECTO}"
export BNA_PROYECTO BNA_ETIQUETA_LOCAL COMPOSE_PROJECT_NAME="$BNA_PROYECTO"
export COMPOSE_PATH_SEPARATOR=: COMPOSE_FILE=compose.yaml:compose.sin-puertos.yaml
# La base de cada suite de integración, en un puerto libre que elige Docker (no en 3327…3332).
export COREDB_PUERTO_PRUEBAS=0 EVALUACION_PUERTO_PRUEBAS=0 DESEMBOLSO_PUERTO_PRUEBAS=0 \
  COBRANZA_PUERTO_PRUEBAS=0 CAPTACION_PUERTO_PRUEBAS=0 SEGURIDAD_PUERTO_PRUEBAS=0
echo "Proyecto de Compose $BNA_PROYECTO, imágenes bna/*:$BNA_ETIQUETA_LOCAL, sin puertos en esta máquina."

# Solo un proyecto vacío: así todo lo que haya al terminar lo creó esta corrida y se puede
# eliminar sin tocar los datos de nadie (por ejemplo, el producto de `./bna up`, proyecto bna).
if [ -n "$(docker compose ps -aq 2>/dev/null)" ] \
  || [ -n "$(docker volume ls -q --filter "label=com.docker.compose.project=$BNA_PROYECTO")" ]; then
  echo "El proyecto $BNA_PROYECTO ya tiene contenedores o volúmenes: use otro BNA_PROYECTO." >&2
  exit 1
fi

limpiar() {
  local imagenes
  echo
  if [ "$fallas" -gt 0 ] && [ -n "$(docker compose ps -aq 2>/dev/null)" ]; then
    echo "══ Estado y registros de los servicios"
    docker compose ps -a || true
    docker compose logs --tail=80 || true
    echo
  fi
  echo "══ Limpieza: contenedores, redes y volúmenes del proyecto $BNA_PROYECTO"
  docker compose down -v --remove-orphans || true
  # Las etiquetas de esta corrida. --no-prune conserva las capas intermedias: son la caché de la
  # próxima construcción. Nunca bna/*:local, la del producto de `./bna up`.
  if [ "$BNA_ETIQUETA_LOCAL" != local ]; then
    imagenes="$(docker image ls --format '{{.Repository}}:{{.Tag}}' --filter "reference=bna/*:$BNA_ETIQUETA_LOCAL")"
    [ -z "$imagenes" ] || docker image rm --no-prune $imagenes >/dev/null || true
  fi
}
trap limpiar EXIT
trap 'exit 130' INT TERM

# Lo que Compose va a crear lleva el proyecto, la etiqueta y ningún puerto de esta corrida.
aislamiento() {
  local config
  config="$(docker compose config)" || return 1
  if [ "$(printf '%s\n' "$config" | sed -n 's/^name: //p')" != "$BNA_PROYECTO" ]; then
    echo "El proyecto de Compose no es $BNA_PROYECTO." >&2
    return 1
  fi
  if printf '%s\n' "$config" | grep -q 'published:'; then
    echo "Algún servicio publica un puerto en esta máquina." >&2
    return 1
  fi
  if printf '%s\n' "$config" | grep -E '^ +image: bna/' | grep -vq ":$BNA_ETIQUETA_LOCAL\$"; then
    echo "Alguna imagen bna/* no lleva la etiqueta $BNA_ETIQUETA_LOCAL." >&2
    return 1
  fi
}
correr "Aislamiento de la corrida" aislamiento
correr "Imágenes" docker compose build -q
correr "CUENTAS" en_backend CUENTAS/tests
correr "TARJETAS" en_backend TARJETAS/tests
correr "ATM" en_backend ATM/tests
correr "BILLETERA (Chaski)" docker run --rm bna/billetera:$BNA_ETIQUETA_LOCAL npm test --silent
correr "Bus de Servicios" en_backend BUS_SERVICIOS/tests
# Fase 2: ningún módulo tiene configurada la dirección directa de COREDB (compose, k8s,
# .env.example, valores por omisión); solo el Bus, COREDB y su arranque.
correr "Bus de Servicios, rutas a COREDB" \
  docker_montado run --rm -v "$RAIZ_HOST:/repo:ro" -e REPO=/repo bna/backend:$BNA_ETIQUETA_LOCAL $PYTEST /repo/scripts/test_comprobar_rutas_coredb.py
correr "Aislamiento de las corridas" \
  docker_montado run --rm -v "$RAIZ_HOST:/repo:ro" -e REPO=/repo "bna/backend:$BNA_ETIQUETA_LOCAL" $PYTEST /repo/scripts/test_aislamiento_pruebas.py
# k8s/overlays/infraestructura: claves sin Secrets, generado al día con k8s/base.
correr "Overlay de Infraestructura" \
  docker_montado run --rm -v "$RAIZ_HOST:/repo:ro" -e REPO=/repo bna/backend:$BNA_ETIQUETA_LOCAL $PYTEST /repo/scripts/test_overlay_infraestructura.py
correr "SOL" docker run --rm bna/sol:$BNA_ETIQUETA_LOCAL $PYTEST SOL/tests
correr "EVALUACION contra COREDB y MySQL" \
  env EVALUACION_IMAGEN_PRUEBAS=bna/backend:$BNA_ETIQUETA_LOCAL EVALUACION_IMAGEN_COREDB=bna/coredb:$BNA_ETIQUETA_LOCAL \
  backend/EVALUACION/scripts/pruebas_integracion.sh
correr "DESEMBOLSO contra COREDB y MySQL" \
  env DESEMBOLSO_IMAGEN_PRUEBAS=bna/backend:$BNA_ETIQUETA_LOCAL DESEMBOLSO_IMAGEN_COREDB=bna/coredb:$BNA_ETIQUETA_LOCAL \
  backend/DESEMBOLSO/scripts/pruebas_integracion.sh
correr "COBRANZA contra COREDB y MySQL" \
  env COBRANZA_IMAGEN_PRUEBAS=bna/backend:$BNA_ETIQUETA_LOCAL COBRANZA_IMAGEN_COREDB=bna/coredb:$BNA_ETIQUETA_LOCAL \
  backend/COBRANZA/scripts/pruebas_integracion.sh
# CAPTACION y, en la imagen de SOL, su contrato CR-INT-01 con el adaptador real de SOL.
correr "CAPTACION contra COREDB y MySQL" \
  env CAPTACION_IMAGEN_PRUEBAS=bna/backend:$BNA_ETIQUETA_LOCAL CAPTACION_IMAGEN_COREDB=bna/coredb:$BNA_ETIQUETA_LOCAL \
  CAPTACION_IMAGEN_SOL=bna/sol:$BNA_ETIQUETA_LOCAL backend/CAPTACION/scripts/pruebas_integracion.sh
# Seguridad sin base propia: las unitarias con un COREDB en memoria y las de integración con
# COREDB y la base integrada reales, a través del Bus.
correr "Seguridad contra COREDB y MySQL" \
  env SEGURIDAD_IMAGEN_PRUEBAS=bna/seguridad:$BNA_ETIQUETA_LOCAL SEGURIDAD_IMAGEN_COREDB=bna/coredb:$BNA_ETIQUETA_LOCAL \
  SEGURIDAD_IMAGEN_BUS=bna/backend:$BNA_ETIQUETA_LOCAL backend/seguridad/scripts/pruebas_integracion.sh
correr "COREDB, unitarias" \
  docker run --rm bna/coredb:$BNA_ETIQUETA_LOCAL sh -c "cd COREDB && $PYTEST"
# Lo que CUENTAS y TARJETAS envían a COREDB, contra los esquemas de COREDB: solo su
# imagen los tiene; en la del backend estas pruebas se omiten.
correr "Contratos de CUENTAS y TARJETAS con COREDB" \
  docker run --rm bna/coredb:$BNA_ETIQUETA_LOCAL $PYTEST \
  CUENTAS/tests/test_contrato_core.py TARJETAS/tests/test_contrato_core.py
correr "COREDB contra MySQL" \
  env COREDB_IMAGEN_PRUEBAS=bna/coredb:$BNA_ETIQUETA_LOCAL backend/COREDB/scripts/pruebas_integracion.sh
correr "Base integrada, despliegue" database/pruebas/mysql/prueba_despliegue.sh
correr "Aviso de push directo" \
  docker_montado run --rm -v "$RAIZ_HOST/.github/scripts:/aviso:ro" bna/backend:$BNA_ETIQUETA_LOCAL $PYTEST /aviso
correr "Frontend, imagen de pruebas" \
  docker build -q --target pruebas -f docker/frontend/Dockerfile -t bna/frontend-pruebas:$BNA_ETIQUETA_LOCAL frontend
correr "Frontend, lint" docker run --rm bna/frontend-pruebas:$BNA_ETIQUETA_LOCAL npm run lint
correr "Frontend, pruebas" docker run --rm bna/frontend-pruebas:$BNA_ETIQUETA_LOCAL npm test

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
