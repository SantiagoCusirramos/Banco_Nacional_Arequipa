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
# Túnel de Cloudflare (opcional; k8s/overlays/infraestructura/tunel):
#   tunel-manifiestos  imprime lo que aplicaría tunel-aplicar
#   tunel-cargar       pod temporal bna-carga-tunel para guardar el token en el PVC bna-secretos;
#                      imprime el comando de carga, espera el archivo y valida su forma sin mostrarlo
#   tunel-aplicar      aplica el Deployment bna-tunel y espera a que conecte (/ready)
#   tunel-quitar       borra el Deployment bna-tunel (el token queda en el PVC)
#
# Variables:
#   KUBECONFIG      obligatorio para las órdenes que tocan el clúster (nunca ~/.kube/config por omisión)
#   BNA_NAMESPACE   obligatorio para esas mismas órdenes; solo se usa ese namespace
#   BNA_REGISTRO    registro de las imágenes (ghcr.io/miguelpro324)
#   BNA_ETIQUETA    etiqueta de las imágenes (el commit actual, 12 caracteres)
#   KUBECTL         kubectl a usar (kubectl)
#   BNA_ESPERA_SEGUNDOS  espera máxima por Deployment (600)
#   BNA_FRONTEND, BNA_BUS  direcciones para `flujo` (por omisión, las del Ingress)
#   BNA_TUNEL_PROTOCOLO    auto (por omisión), quic o http2, para tunel-aplicar
#   BNA_TUNEL_ESPERA_SEGUNDOS  espera máxima a que el túnel conecte (180)
#   BNA_TUNEL_ESPERA_CARGA     espera máxima a que se cargue el token (540)
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

OVERLAY=k8s/overlays/infraestructura
TUNEL="$OVERLAY/tunel"
TOKEN_TUNEL=/bna-secretos/cloudflared-token
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

# Un overlay más lo que depende del momento: namespace, etiqueta de las imágenes y, para el
# principal, el ConfigMap con scripts/generar_env.sh y .env.example, que kustomize no lee desde
# el overlay. Uso: kustomizar CARPETA [principal|tunel]
kustomizar() {
  : "${BNA_NAMESPACE:?Falta BNA_NAMESPACE (el namespace asignado)}"
  local carpeta="$1" tipo="$2" dir tag relativo nombre protocolo
  dir="$(mktemp -d)"
  TEMPORALES+=("$dir")
  tag="$(etiqueta)"
  relativo="$(python3 -c 'import os, sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "$RAIZ/$carpeta" "$dir")"
  {
    echo "apiVersion: kustomize.config.k8s.io/v1beta1"
    echo "kind: Kustomization"
    echo "namespace: \"$BNA_NAMESPACE\""
    echo "resources: [\"$relativo\"]"
    echo "labels:"
    echo "  - pairs: { app.kubernetes.io/part-of: bna, app.kubernetes.io/instance: bna }"
    if [ "$tipo" = principal ]; then
      cp scripts/generar_env.sh "$dir/generar_env.sh"
      cp .env.example "$dir/env.example"
      echo "configMapGenerator:"
      echo "  - name: bna-generar-env"
      echo "    files: [generar_env.sh, env.example]"
      echo "    options: { disableNameSuffixHash: true }"
    else
      protocolo="${BNA_TUNEL_PROTOCOLO:-auto}"
      case "$protocolo" in
        auto) ;;
        quic|http2)
          echo "patches:"
          echo "  - target: { kind: Deployment, name: bna-tunel }"
          echo "    patch: '[{\"op\": \"replace\", \"path\": \"/spec/template/spec/containers/0/env/0\", \"value\": {\"name\": \"TUNNEL_TRANSPORT_PROTOCOL\", \"value\": \"$protocolo\"}}]'"
          ;;
        *) echo "BNA_TUNEL_PROTOCOLO debe ser auto, quic o http2 (es '$protocolo')." >&2; exit 2 ;;
      esac
    fi
    echo "images:"
    for nombre in "${NOMBRES[@]}"; do
      echo "  - { name: $REGISTRO_OVERLAY/bna-$nombre, newName: $REGISTRO/bna-$nombre, newTag: \"$tag\" }"
    done
  } > "$dir/kustomization.yaml"
  "$KUBECTL" kustomize "$dir"
}

manifiestos() { kustomizar "$OVERLAY" principal; }
tunel_manifiestos() { kustomizar "$TUNEL" tunel; }

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
  k delete pod bna-carga-tunel --ignore-not-found --wait=true >/dev/null
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

# ── Túnel de Cloudflare (opcional) ─────────────────────────────────────────────
# Guía: Documents/despliegue-infraestructura.md, «Acceso público por túnel (opcional)».

# Sin BNA_ETIQUETA, la del backend que corre en el clúster: el commit actual puede no tener
# imágenes publicadas (por ejemplo, un cambio solo de documentación).
etiqueta_en_uso() {
  [ -z "${BNA_ETIQUETA:-}" ] || return 0
  local imagen
  imagen="$(k get deployment bna-cuentas -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null || true)"
  if [ -z "$imagen" ]; then
    echo "No está bna-cuentas en $BNA_NAMESPACE: aplique antes el producto o fije BNA_ETIQUETA." >&2
    exit 1
  fi
  BNA_ETIQUETA="${imagen##*:}"
}

# Lo que corre dentro del pod de carga, con el token por stdin (la primera línea). Escritura
# atómica: si llega vacío, el token anterior no cambia.
CARGA_REMOTA='umask 077; head -n 1 | tr -d "\r\n" > /bna-secretos/cloudflared-token.nuevo && test -s /bna-secretos/cloudflared-token.nuevo && mv -f /bna-secretos/cloudflared-token.nuevo /bna-secretos/cloudflared-token && echo "Token guardado ($(wc -c < /bna-secretos/cloudflared-token) bytes)."'

# Comprueba la forma del token sin mostrarlo: base64 de un JSON con a (cuenta), t (túnel) y s.
VALIDAR_TOKEN="$(cat <<'PY'
import base64, json, os, stat, sys
archivo = "/bna-secretos/cloudflared-token"
crudo = open(archivo, "rb").read().strip()
try:
    datos = json.loads(base64.b64decode(crudo + b"=" * (-len(crudo) % 4)))
    valido = isinstance(datos, dict) and all(isinstance(datos.get(c), str) and datos[c] for c in ("a", "t", "s"))
except Exception:
    valido = False
if not valido:
    print("El archivo no tiene la forma de un token de túnel (base64 de un JSON con a, t y s). "
          "Repita la carga con el token correcto.", file=sys.stderr)
    sys.exit(1)
os.chmod(archivo, 0o600)
print(f"Token con forma válida: {len(crudo)} bytes, permisos {stat.S_IMODE(os.stat(archivo).st_mode):o}.")
PY
)"

firma_token() {
  k exec bna-carga-tunel -c carga -- sh -c "stat -c '%i %Y %s' $TOKEN_TUNEL 2>/dev/null || true"
}

tunel_cargar() {
  exigir_cluster
  etiqueta_en_uso
  local imagen antes ahora espera inicio
  imagen="$REGISTRO/bna-backend:$(etiqueta)"
  espera="${BNA_TUNEL_ESPERA_CARGA:-540}"
  k delete pod bna-carga-tunel --ignore-not-found --wait=true >/dev/null
  trap 'k delete pod bna-carga-tunel --ignore-not-found --wait=false >/dev/null 2>&1 || true; rm -rf "${TEMPORALES[@]}"' EXIT
  k apply -f - >/dev/null <<YAML
apiVersion: v1
kind: Pod
metadata:
  name: bna-carga-tunel
  labels: { app.kubernetes.io/name: carga-tunel, app.kubernetes.io/part-of: bna, app.kubernetes.io/instance: bna }
spec:
  restartPolicy: Never
  activeDeadlineSeconds: 900
  automountServiceAccountToken: false
  securityContext: { runAsUser: 10001, runAsGroup: 10001, runAsNonRoot: true, seccompProfile: { type: RuntimeDefault } }
  containers:
    - name: carga
      image: $imagen
      command: [sleep, "600"]
      volumeMounts: [{ name: bna-secretos, mountPath: /bna-secretos }]
      resources: { requests: { cpu: 10m, memory: 32Mi }, limits: { cpu: 200m, memory: 128Mi } }
      securityContext: { allowPrivilegeEscalation: false, readOnlyRootFilesystem: true, capabilities: { drop: [ALL] } }
  volumes:
    - name: bna-secretos
      persistentVolumeClaim: { claimName: bna-secretos }
YAML
  if ! k wait --for=condition=Ready pod/bna-carga-tunel --timeout=180s >/dev/null; then
    diagnostico
    exit 1
  fi
  antes="$(firma_token)"
  [ -z "$antes" ] || echo "Ya hay un token en el PVC: si carga otro, lo reemplaza (Ctrl-C para conservarlo)."
  cat <<TEXTO
Pod bna-carga-tunel listo. En otra terminal, con KUBECONFIG y BNA_NAMESPACE exportados:

set -o pipefail
<orden que imprime el token> \\
  | kubectl --kubeconfig "\$KUBECONFIG" -n "\$BNA_NAMESPACE" exec -i bna-carga-tunel -c carga -- \\
      sh -c '$CARGA_REMOTA'

Esperando el token (hasta $espera s)...
TEXTO
  inicio="$(date +%s)"
  while ahora="$(firma_token)"; [ -z "$ahora" ] || [ "$ahora" = "$antes" ]; do
    if [ $(( $(date +%s) - inicio )) -ge "$espera" ]; then
      echo "No llegó el token en $espera s. Vuelva a correr scripts/k8s-infra.sh tunel-cargar." >&2
      exit 1
    fi
    sleep 3
  done
  k exec bna-carga-tunel -c carga -- python3 -c "$VALIDAR_TOKEN"
  echo "Siguiente: scripts/k8s-infra.sh tunel-aplicar (para rotarlo con el túnel ya aplicado: kubectl rollout restart deployment/bna-tunel)."
}

tunel_aplicar() {
  exigir_cluster
  etiqueta_en_uso
  local render
  render="$(mktemp)"
  TEMPORALES+=("$render")
  tunel_manifiestos > "$render"
  python3 scripts/overlay_infraestructura.py revisar "$render" --registro "$REGISTRO/" >/dev/null
  echo "Túnel en $BNA_NAMESPACE (protocolo ${BNA_TUNEL_PROTOCOLO:-auto}, imagen del copiador $REGISTRO/bna-backend:$(etiqueta))"
  k apply -f "$render"
  if ! k rollout status deployment/bna-tunel --timeout="${BNA_TUNEL_ESPERA_SEGUNDOS:-180}s"; then
    echo "El túnel no conectó. Si cloudflared no llega a Cloudflare por QUIC, pruebe BNA_TUNEL_PROTOCOLO=http2." >&2
    echo "Los registros incluyen el id del túnel: no los pegue en PR ni issues." >&2
    diagnostico
    exit 1
  fi
  echo "Túnel conectado (bna-tunel listo: /ready con al menos una conexión). Las rutas y Access se configuran en el panel de Cloudflare."
}

tunel_quitar() {
  exigir_cluster
  k delete deployment bna-tunel --ignore-not-found --wait=true
  k wait --for=delete pod -l app.kubernetes.io/name=tunel --timeout=120s 2>/dev/null || true
  echo "Túnel quitado. El token sigue en el PVC bna-secretos (lo borra borrar --si)."
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
  tunel-manifiestos) tunel_manifiestos ;;
  tunel-cargar) tunel_cargar ;;
  tunel-aplicar) tunel_aplicar ;;
  tunel-quitar) tunel_quitar ;;
  *) sed -n '2,34p' "$0" >&2; exit 2 ;;
esac
