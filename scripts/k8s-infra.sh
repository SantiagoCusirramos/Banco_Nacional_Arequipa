#!/usr/bin/env bash
# Despliegue del producto en el clúster de Infraestructura (k8s/overlays/infraestructura).
# Guía: Documents/despliegue-infraestructura.md.
#
# Uso: scripts/k8s-infra.sh ORDEN
#   construir     construye las imágenes (docker compose) y las etiqueta para el registro
#   publicar      construir + docker push (exige el árbol de git limpio: la etiqueta es el commit)
#   imagenes      lista las imágenes con su etiqueta
#   manifiestos   imprime lo que aplicaría (overlay + namespace + etiqueta + bna-generar-env)
#   aplicar       aplica, espera el Job bna-arranque y cada Deployment, y muestra las direcciones
#   datos         carga los datos de referencia en la base (idempotente)
#   flujo         corre scripts/flujo_demo.py contra el clúster
#   estado        pods, servicios, Ingress, PVC y Jobs del producto
#   diagnostico   estado + registros de los pods que no están listos
#   borrar --si   borra todo lo del producto en el namespace (bna-*), también los PVC y sus datos
#
# Variables:
#   KUBECONFIG      obligatorio para las órdenes que tocan el clúster (nunca ~/.kube/config por omisión)
#   BNA_NAMESPACE   obligatorio para esas mismas órdenes; solo se usa ese namespace
#   BNA_REGISTRO    registro de las imágenes (ghcr.io/miguelpro324)
#   BNA_ETIQUETA    etiqueta de las imágenes (el commit actual, 12 caracteres)
#   KUBECTL         kubectl a usar (kubectl)
#   BNA_ESPERA_SEGUNDOS  espera máxima por Deployment (600)
#   BNA_FRONTEND, BNA_BUS  direcciones para `flujo` (por omisión, las del Ingress)
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

OVERLAY=k8s/overlays/infraestructura
REGISTRO_OVERLAY=ghcr.io/miguelpro324
REGISTRO="${BNA_REGISTRO:-$REGISTRO_OVERLAY}"
KUBECTL="${KUBECTL:-kubectl}"
ESPERA="${BNA_ESPERA_SEGUNDOS:-600}"
SELECTOR=app.kubernetes.io/instance=bna
# Imagen de compose → nombre en el registro (bna-<nombre>).
NOMBRES=(core-db coredb backend sol seguridad billetera frontend)
# En orden de arranque; cada pod espera igual a lo que necesita.
DESPLIEGUES=(db coredb bus cuentas tarjetas sol evaluacion desembolso cobranza captacion seguridad atm billetera frontend)
TEMPORALES=()
trap 'rm -rf "${TEMPORALES[@]}"' EXIT

etiqueta() {
  if [ -n "${BNA_ETIQUETA:-}" ]; then
    printf '%s\n' "$BNA_ETIQUETA"
  else
    git rev-parse --short=12 HEAD
  fi
}

imagenes() {
  local nombre tag
  tag="$(etiqueta)"
  for nombre in "${NOMBRES[@]}"; do
    printf '%s/bna-%s:%s\n' "$REGISTRO" "$nombre" "$tag"
  done
}

construir() {
  local nombre tag
  tag="$(etiqueta)"
  scripts/generar_env.sh "$RAIZ" >/dev/null  # compose.yaml exige las variables de .env para construir
  echo "Construyendo las imágenes..."
  docker compose build -q
  for nombre in "${NOMBRES[@]}"; do
    docker tag "bna/$nombre:local" "$REGISTRO/bna-$nombre:$tag"
  done
  echo "Imágenes etiquetadas $REGISTRO/bna-*:$tag"
}

publicar() {
  local imagen
  if [ -z "${BNA_ETIQUETA:-}" ] && [ -n "$(git status --porcelain)" ]; then
    echo "Hay cambios sin confirmar: la etiqueta (el commit) no describiría las imágenes." >&2
    echo "Confirme los cambios o fije BNA_ETIQUETA." >&2
    exit 1
  fi
  construir
  for imagen in $(imagenes); do
    docker push -q "$imagen"
  done
  echo "Publicadas en $REGISTRO con la etiqueta $(etiqueta)."
}

exigir_cluster() {
  : "${BNA_NAMESPACE:?Falta BNA_NAMESPACE (el namespace asignado)}"
  : "${KUBECONFIG:?Falta KUBECONFIG (el archivo del clúster; este script no usa ~/.kube/config por omisión)}"
  [ -f "$KUBECONFIG" ] || { echo "No existe $KUBECONFIG" >&2; exit 1; }
  command -v "$KUBECTL" >/dev/null 2>&1 || { echo "Falta kubectl ($KUBECTL)." >&2; exit 1; }
}

k() { "$KUBECTL" --kubeconfig "$KUBECONFIG" -n "$BNA_NAMESPACE" "$@"; }

# El overlay más lo que depende del momento: namespace, etiqueta de las imágenes y el
# ConfigMap con scripts/generar_env.sh y .env.example, que kustomize no lee desde el overlay.
manifiestos() {
  : "${BNA_NAMESPACE:?Falta BNA_NAMESPACE (el namespace asignado)}"
  local dir tag relativo nombre
  dir="$(mktemp -d)"
  TEMPORALES+=("$dir")
  tag="$(etiqueta)"
  cp scripts/generar_env.sh "$dir/generar_env.sh"
  cp .env.example "$dir/env.example"
  relativo="$(python3 -c 'import os, sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "$RAIZ/$OVERLAY" "$dir")"
  {
    echo "apiVersion: kustomize.config.k8s.io/v1beta1"
    echo "kind: Kustomization"
    echo "namespace: \"$BNA_NAMESPACE\""
    echo "resources: [\"$relativo\"]"
    echo "labels:"
    echo "  - pairs: { app.kubernetes.io/part-of: bna, app.kubernetes.io/instance: bna }"
    echo "configMapGenerator:"
    echo "  - name: bna-generar-env"
    echo "    files: [generar_env.sh, env.example]"
    echo "    options: { disableNameSuffixHash: true }"
    echo "images:"
    for nombre in "${NOMBRES[@]}"; do
      echo "  - { name: $REGISTRO_OVERLAY/bna-$nombre, newName: $REGISTRO/bna-$nombre, newTag: \"$tag\" }"
    done
  } > "$dir/kustomization.yaml"
  "$KUBECTL" kustomize "$dir"
}

# De cada pod que no está listo o que se reinició: estado de sus contenedores, motivo del último
# reinicio (por ejemplo OOMKilled) y el final de sus registros. La cuenta no ve eventos.
diagnostico() {
  echo "── Estado" >&2
  k get pods,jobs -l "$SELECTOR" -o wide >&2 || true
  local pod
  for pod in $(k get pods -l "$SELECTOR" --no-headers 2>/dev/null \
                 | awk '{ split($2, listos, "/"); if ((listos[1] != listos[2] && $3 != "Completed") || $4 != "0") print $1 }'); do
    echo "── $pod" >&2
    k get pod "$pod" -o jsonpath='{range .status.initContainerStatuses[*]}{.name}: reinicios={.restartCount} estado={.state} anterior={.lastState.terminated.reason}{"\n"}{end}{range .status.containerStatuses[*]}{.name}: reinicios={.restartCount} estado={.state} anterior={.lastState.terminated.reason}{"\n"}{end}' >&2 || true
    echo "· registros de la ejecución anterior" >&2
    k logs "$pod" --all-containers --prefix --previous --tail=25 >&2 2>/dev/null || true
    echo "· registros de la ejecución actual" >&2
    k logs "$pod" --all-containers --prefix --tail=25 >&2 2>/dev/null || true
  done
}

aplicar() {
  exigir_cluster
  local render despliegue host
  render="$(mktemp)"
  TEMPORALES+=("$render")
  manifiestos > "$render"
  python3 scripts/overlay_infraestructura.py revisar "$render" --registro "$REGISTRO/" >/dev/null
  echo "Namespace $BNA_NAMESPACE, imágenes $REGISTRO/bna-*:$(etiqueta)"
  # La plantilla de un Job no se puede cambiar: se reemplaza. El .env queda en el PVC.
  k delete job bna-arranque --ignore-not-found --wait=true >/dev/null
  k apply -f "$render"
  if ! k wait --for=condition=complete job/bna-arranque --timeout=300s; then
    k logs job/bna-arranque --tail=50 >&2 || true
    diagnostico
    exit 1
  fi
  k logs job/bna-arranque --tail=5
  for despliegue in "${DESPLIEGUES[@]}"; do
    if ! k rollout status "deployment/bna-$despliegue" --timeout="${ESPERA}s"; then
      diagnostico
      exit 1
    fi
  done
  echo
  echo "Producto desplegado en $BNA_NAMESPACE. Direcciones (Ingress):"
  for host in $(k get ingress bna-web -o jsonpath='{.spec.rules[*].host}'); do
    echo "  http://$host"
  done
  echo "Datos de referencia: scripts/k8s-infra.sh datos. Flujo: scripts/k8s-infra.sh flujo"
}

# Los que carga la imagen de la base al crear su volumen (database/sql/bna_datos_dev.sql), con
# INSERT IGNORE: se puede repetir y completa lo que falte (por ejemplo, periodos de meses nuevos).
# La clave de root no sale del pod: la lee el propio contenedor de /secretos.
SQL_DATOS="$(cat <<'SQL'
SET NAMES utf8mb4;
SET @hoy = DATE(CONVERT_TZ(UTC_TIMESTAMP(), '+00:00', 'America/Lima'));
INSERT IGNORE INTO core.periodo_contable (anio, mes, fecha_inicio, fecha_fin, estado)
WITH RECURSIVE meses (inicio, n) AS (
    SELECT CAST(DATE_FORMAT(@hoy, '%Y-%m-01') AS DATE), 0
    UNION ALL
    SELECT inicio + INTERVAL 1 MONTH, n + 1 FROM meses WHERE n < 23
)
SELECT YEAR(inicio), MONTH(inicio), inicio, LAST_DAY(inicio), 'ABIERTO' FROM meses;
INSERT IGNORE INTO core.agencia VALUES
    ('AQP01', 'Agencia Arequipa Centro', 'Calle Mercaderes 120', 'Cercado', 'Arequipa', 'ACTIVA');
INSERT IGNORE INTO core.terminal (id_terminal, descripcion, activo, id_canal, id_agencia) VALUES
    ('DEV-ATM-01', 'Cajero de desarrollo', TRUE, 'ATM', 'AQP01'),
    ('DEV-AGE-01', 'Agente de desarrollo', TRUE, 'AGE', 'AQP01'),
    ('DEV-VEN-01', 'Ventanilla de desarrollo', TRUE, 'VEN', 'AQP01'),
    ('DEV-HB-01', 'Home Banking de desarrollo', TRUE, 'HB', NULL),
    ('DEV-BD-01', 'Billetera Digital de desarrollo', TRUE, 'BD', NULL);
INSERT IGNORE INTO tarjetas.bin_tarjeta VALUES ('004499', 'FISICA', 'Débito BNA física');
SELECT 'periodo contable del mes, abierto' AS dato,
       (SELECT COUNT(*) FROM core.periodo_contable
         WHERE anio = YEAR(@hoy) AND mes = MONTH(@hoy) AND estado = 'ABIERTO') AS hay
UNION ALL SELECT 'BIN 004499', (SELECT COUNT(*) FROM tarjetas.bin_tarjeta WHERE bin = '004499')
UNION ALL SELECT 'agencia AQP01', (SELECT COUNT(*) FROM core.agencia WHERE id_agencia = 'AQP01')
UNION ALL SELECT 'terminales DEV-*', (SELECT COUNT(*) FROM core.terminal WHERE id_terminal LIKE 'DEV-%')
UNION ALL SELECT 'cajero DEV-ATM-01 activo',
                 (SELECT COUNT(*) FROM core.terminal WHERE id_terminal = 'DEV-ATM-01' AND activo);
SQL
)"

datos() {
  exigir_cluster
  local salida
  salida="$(printf '%s\n' "$SQL_DATOS" | k exec -i deployment/bna-db -c mysql -- sh -c \
    '. /secretos/env; MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot -h127.0.0.1 --protocol=TCP --default-character-set=utf8mb4 --table')"
  echo "$salida"
  if printf '%s\n' "$salida" | grep -qE '\|[[:space:]]+0[[:space:]]+\|'; then
    echo "Falta algún dato de referencia (arriba, con 0)." >&2
    exit 1
  fi
  echo "Datos de referencia completos."
}

flujo() {
  exigir_cluster
  local hosts frontend bus
  hosts="$(k get ingress bna-web -o jsonpath='{.spec.rules[*].host}')"
  frontend="$(printf '%s\n' $hosts | grep -E '^bna\.' | head -n 1)"
  bus="$(printf '%s\n' $hosts | grep -E '^bna-bus\.' | head -n 1)"
  BNA_K8S_NAMESPACE="$BNA_NAMESPACE" KUBECTL="$KUBECTL" \
    BNA_FRONTEND="${BNA_FRONTEND:-http://$frontend}" BNA_BUS="${BNA_BUS:-http://$bus}" \
    python3 scripts/flujo_demo.py "$@"
}

borrar() {
  exigir_cluster
  if [ "${1:-}" != "--si" ]; then
    echo "Borra todo lo del producto en $BNA_NAMESPACE (bna-*), con los PVC: la base y el .env." >&2
    echo "Para hacerlo: scripts/k8s-infra.sh borrar --si" >&2
    exit 2
  fi
  local objetos objeto
  objetos="$(k get deployments,services,ingresses,jobs,configmaps,persistentvolumeclaims -l "$SELECTOR" -o name)"
  for objeto in $objetos; do
    case "${objeto#*/}" in
      bna-*) ;;
      *) echo "$objeto tiene la etiqueta del producto pero no el prefijo bna-: no se borra nada." >&2; exit 1 ;;
    esac
  done
  if [ -z "$objetos" ]; then
    echo "No hay nada del producto en $BNA_NAMESPACE."
    return 0
  fi
  # shellcheck disable=SC2086
  k delete --wait=true $objetos
  k wait --for=delete pod -l "$SELECTOR" --timeout=180s 2>/dev/null || true
  echo "Borrado lo del producto en $BNA_NAMESPACE."
}

case "${1:-}" in
  construir) construir ;;
  publicar) publicar ;;
  imagenes) imagenes ;;
  manifiestos) manifiestos ;;
  aplicar) aplicar ;;
  datos) datos ;;
  flujo) shift; flujo "$@" ;;
  estado) exigir_cluster; k get pods,services,ingresses,persistentvolumeclaims,jobs -l "$SELECTOR" ;;
  diagnostico) exigir_cluster; diagnostico ;;
  borrar) shift; borrar "$@" ;;
  *) sed -n '2,24p' "$0" >&2; exit 2 ;;
esac
