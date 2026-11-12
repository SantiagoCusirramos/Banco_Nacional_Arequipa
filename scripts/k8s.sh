#!/usr/bin/env bash
# Despliegue del producto en un clúster local de kind. Uso: ./bna k8s-up | k8s-smoke | k8s-ps | k8s-down
# Requiere Docker, kind y kubectl. Solo toca el clúster `bna` que crea este script:
# toda orden de kubectl lleva su contexto.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

CLUSTER=bna
CONTEXTO="kind-$CLUSTER"
NS=bna
IMAGENES=(bna/core-db:local bna/db-aux:local bna/coredb:local bna/backend:local
          bna/sol:local bna/seguridad:local bna/frontend:local)
DESPLIEGUES=(db db-aux coredb cuentas sol seguridad frontend)
ESPERA="${BNA_ESPERA_SEGUNDOS:-600}"

k() { kubectl --context "$CONTEXTO" "$@"; }
valor() { grep -E "^$1=" .env | tail -n 1 | cut -d= -f2-; }

requisitos() {
  local falta=0 orden
  for orden in docker kind kubectl; do
    command -v "$orden" >/dev/null 2>&1 || { echo "Falta $orden en esta máquina." >&2; falta=1; }
  done
  [ "$falta" = 0 ] || exit 1
}

hay_cluster() { kind get clusters 2>/dev/null | grep -qx "$CLUSTER"; }

exigir_cluster() {
  hay_cluster || { echo "No existe el clúster $CLUSTER: ejecute primero ./bna k8s-up" >&2; exit 1; }
}

# El Secret sale del .env local y se aplica directo al clúster: nunca se escribe en un archivo.
secreto() {
  k -n "$NS" create secret generic bna-secretos --from-env-file=.env --dry-run=client -o yaml \
    | k apply -f - >/dev/null
  echo "Secret bna-secretos aplicado desde .env."
}

# De cada pod que no está listo muestra por qué terminó su ejecución anterior y el
# final de sus registros: el motivo de un reinicio solo queda en la ejecución anterior.
diagnostico() {
  echo "── Estado del clúster" >&2
  k -n "$NS" get pods -o wide >&2 || true
  k -n "$NS" get events --sort-by=.lastTimestamp 2>/dev/null | tail -n 25 >&2 || true
  local pod
  for pod in $(k -n "$NS" get pods --no-headers 2>/dev/null \
                 | awk '{ split($2, listos, "/"); if (listos[1] != listos[2]) print $1 }'); do
    echo "── $pod" >&2
    k -n "$NS" get pod "$pod" -o jsonpath='{range .status.initContainerStatuses[*]}{.name}: reinicios={.restartCount} anterior={.lastState.terminated.reason} salida={.lastState.terminated.exitCode}{"\n"}{end}{range .status.containerStatuses[*]}{.name}: reinicios={.restartCount} anterior={.lastState.terminated.reason} salida={.lastState.terminated.exitCode}{"\n"}{end}' >&2 || true
    echo "· registros de la ejecución anterior" >&2
    k -n "$NS" logs "$pod" --all-containers --prefix --previous --tail=25 >&2 2>/dev/null || true
    echo "· registros de la ejecución actual" >&2
    k -n "$NS" logs "$pod" --all-containers --prefix --tail=25 >&2 2>/dev/null || true
  done
}

# kind corre los pods sin perfil de AppArmor propio. Si el anfitrión tiene un perfil
# para /usr/sbin/mysqld (Ubuntu con MySQL instalado), se aplica al mysqld de los pods,
# que no puede leer /etc/my.cnf, y las bases no arrancan. Ver k8s/README.md.
aviso_apparmor() {
  [ -e /etc/apparmor.d/usr.sbin.mysqld ] || return 0
  [ ! -e /etc/apparmor.d/disable/usr.sbin.mysqld ] || return 0
  [ "$(cat /sys/module/apparmor/parameters/enabled 2>/dev/null)" = Y ] || return 0
  cat >&2 <<'TEXTO'
Aviso: esta máquina tiene un perfil de AppArmor para /usr/sbin/mysqld. Con él las bases
no arrancan dentro de kind. Para desactivarlo (lo usa el MySQL instalado en la máquina):

  sudo ln -s /etc/apparmor.d/usr.sbin.mysqld /etc/apparmor.d/disable/
  sudo apparmor_parser -R /etc/apparmor.d/usr.sbin.mysqld

TEXTO
}

subir() {
  requisitos
  aviso_apparmor
  scripts/generar_env.sh "$RAIZ"
  echo "Construyendo las imágenes..."
  docker compose build -q
  if ! hay_cluster; then
    kind create cluster --config k8s/kind-config.yaml --wait 180s
  fi
  echo "Cargando las imágenes en el clúster..."
  kind load docker-image "${IMAGENES[@]}" --name "$CLUSTER"
  k apply -f k8s/base/namespace.yaml >/dev/null
  secreto
  k apply -k k8s/overlays/local
  local despliegue
  for despliegue in "${DESPLIEGUES[@]}"; do
    if ! k -n "$NS" rollout status "deployment/$despliegue" --timeout="${ESPERA}s"; then
      diagnostico
      exit 1
    fi
  done
  cat <<TEXTO

Producto desplegado en el clúster $CLUSTER (kind).

  Frontend      http://localhost:13000
  COREDB (API)  http://127.0.0.1:18012/docs
  CUENTAS       http://127.0.0.1:18001/docs
  SOL           http://127.0.0.1:18011/docs
  Seguridad     http://127.0.0.1:18013

  Administrador de COREDB: usuario $(valor BNA_ADMIN_USUARIO); su contraseña está en .env.
  Para comprobarlo: ./bna k8s-smoke
TEXTO
}

humo() {
  requisitos
  exigir_cluster
  k -n "$NS" exec -i deployment/coredb -c coredb -- env \
    BNA_ADMIN_USUARIO="$(valor BNA_ADMIN_USUARIO)" \
    BNA_ADMIN_PASSWORD="$(valor BNA_ADMIN_PASSWORD)" \
    python - < scripts/flujo_e2e.py
}

case "${1:-}" in
  up) subir ;;
  smoke) humo ;;
  ps) requisitos; exigir_cluster; k -n "$NS" get pods,services ;;
  diagnostico) requisitos; exigir_cluster; diagnostico ;;
  down) requisitos; kind delete cluster --name "$CLUSTER" ;;
  *) echo "Uso: scripts/k8s.sh up | smoke | ps | diagnostico | down" >&2; exit 2 ;;
esac
