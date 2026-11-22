#!/usr/bin/env bash
# Prueba k8s/overlays/infraestructura en un clúster de kind con scripts/k8s-infra.sh: las mismas
# imágenes (cargadas con `kind load`, sin registro) y los mismos manifiestos, con el namespace
# creado aquí y una StorageClass `local-path` como la de k3s. Sin Ingress: el flujo llega al
# frontend y al Bus por `kubectl port-forward`.
#
# Comprueba el patrón de claves sin Secrets (ningún Secret en el namespace, archivos 0440 con
# solo las claves del pod, el Job no cambia un .env que ya existe), carga los datos de
# referencia, corre scripts/flujo_demo.py y borra todo con `k8s-infra.sh borrar`.
# También el túnel opcional de Cloudflare con un token falso: tunel-cargar con la misma tubería
# que usa el dueño, el contenedor de inicio deja el token 0440 en memoria, cloudflared no monta
# el PVC (no ve el .env), no conecta (el token es falso) y tunel-quitar lo borra.
# Al terminar elimina el clúster, aunque algo falle.
#
# Uso: scripts/prueba_k8s_infra_kind.sh
# Requiere docker, kind (v0.30.0: Kubernetes 1.34), kubectl y python3.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

CLUSTER="${BNA_KIND_CLUSTER:-bna-infra}"
# Numérico, como el que asigna Infraestructura: comprueba que los manifiestos lo citan.
export BNA_NAMESPACE="${BNA_NAMESPACE:-1234567890}"
export BNA_ETIQUETA="${BNA_ETIQUETA:-prueba-kind}"
export KUBECTL="${KUBECTL:-kubectl}"
TRABAJO="$(mktemp -d)"
export KUBECONFIG="$TRABAJO/kubeconfig"
REENVIOS=()

k() { "$KUBECTL" --kubeconfig "$KUBECONFIG" -n "$BNA_NAMESPACE" "$@"; }

limpiar() {
  local estado=$?
  [ "${#REENVIOS[@]}" -eq 0 ] || kill "${REENVIOS[@]}" 2>/dev/null || true
  if [ "$estado" -ne 0 ] && [ -f "$KUBECONFIG" ]; then
    scripts/k8s-infra.sh diagnostico || true
  fi
  kind delete cluster --name "$CLUSTER" >/dev/null 2>&1 || true
  # kind no elimina la red `kind` con el último clúster: se quita si nadie más la usa.
  if docker network inspect kind >/dev/null 2>&1 && [ -z "$(docker ps -aq --filter network=kind)" ]; then
    docker network rm kind >/dev/null || true
  fi
  rm -rf "$TRABAJO"
  exit "$estado"
}
trap limpiar EXIT

paso() { echo; echo "══ $*"; }

paso "Clúster de kind $CLUSTER ($(kind version | cut -d' ' -f1-2))"
kind create cluster --name "$CLUSTER" --kubeconfig "$KUBECONFIG" --wait 180s
"$KUBECTL" --kubeconfig "$KUBECONFIG" version | sed -n 's/^Server Version: /Servidor: /p'
"$KUBECTL" --kubeconfig "$KUBECONFIG" create namespace "$BNA_NAMESPACE"
# k3s llama local-path a su StorageClass; en kind se llama standard, con el mismo aprovisionador.
"$KUBECTL" --kubeconfig "$KUBECONFIG" apply -f - <<'YAML'
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: local-path
provisioner: rancher.io/local-path
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
YAML

paso "Imágenes"
scripts/k8s-infra.sh construir
# shellcheck disable=SC2046
kind load docker-image $(scripts/k8s-infra.sh imagenes) --name "$CLUSTER"

paso "Aplicar el overlay"
scripts/k8s-infra.sh aplicar

paso "Claves sin Secrets"
if [ -n "$(k get secrets -o name)" ]; then
  echo "Hay Secrets en el namespace:" >&2
  k get secrets >&2
  exit 1
fi
if k get deployments,jobs -o yaml | grep -qE 'secretKeyRef|secretRef|secretName'; then
  echo "Algún Deployment o Job lee un Secret." >&2
  exit 1
fi
echo "Ningún Secret en $BNA_NAMESPACE ni referencias a Secrets."
# Usuario 10001 (dueño) y 1000 (por el grupo del pod): cada uno lee su archivo y solo con sus claves.
comprobar_archivo() {
  local despliegue="$1" contenedor="$2" esperadas="$3" claves permisos
  permisos="$(k exec "deployment/bna-$despliegue" -c "$contenedor" -- stat -c '%a' /secretos/env)"
  claves="$(k exec "deployment/bna-$despliegue" -c "$contenedor" -- sh -c 'cut -d= -f1 /secretos/env | sort | tr "\n" " "')"
  if [ "$permisos" != 440 ] || [ "$claves" != "$esperadas" ]; then
    echo "bna-$despliegue: /secretos/env con permisos $permisos y claves [$claves]; se esperaba 440 y [$esperadas]" >&2
    exit 1
  fi
  echo "bna-$despliegue: /secretos/env 0440 con [$claves]"
}
comprobar_archivo cuentas cuentas "BUS_TOKEN "
comprobar_archivo frontend frontend "BUS_TOKEN "
comprobar_archivo billetera billetera "BUS_TOKEN CHASKI_COREDB_SECRETO "
comprobar_archivo db mysql "CORE_DB_ADMIN_PASSWORD CORE_DB_APP_PASSWORD CORE_DB_SEGURIDAD_PASSWORD MYSQL_ROOT_PASSWORD "
# El proceso del contenedor recibió la variable (sin mostrar su valor).
if ! k exec deployment/bna-cuentas -c cuentas -- sh -c 'tr "\0" "\n" < /proc/1/environ | grep -q "^BUS_TOKEN=."'; then
  echo "El proceso de bna-cuentas no tiene BUS_TOKEN." >&2
  exit 1
fi
echo "El proceso de bna-cuentas tiene BUS_TOKEN en su entorno."

paso "Aplicar otra vez: el Job no cambia el .env"
scripts/k8s-infra.sh aplicar | tee "$TRABAJO/segunda.txt"
grep -q "no cambia" "$TRABAJO/segunda.txt" || { echo "El Job bna-arranque reescribió el .env." >&2; exit 1; }

paso "Datos de referencia (dos veces: es idempotente)"
scripts/k8s-infra.sh datos
scripts/k8s-infra.sh datos >/dev/null

paso "Flujo de demostración (scripts/flujo_demo.py)"
reenviar() {
  local servicio="$1" puerto="$2"
  k port-forward "service/bna-$servicio" "$puerto" >"$TRABAJO/reenvio-$servicio.log" 2>&1 &
  REENVIOS+=("$!")
}
reenviar frontend 13000:3000
reenviar bus 18018:8018
for _ in $(seq 1 30); do
  if curl -fsS -o /dev/null http://127.0.0.1:13000/login && curl -fsS -o /dev/null http://127.0.0.1:18018/docs; then
    break
  fi
  sleep 2
done
BNA_FRONTEND=http://127.0.0.1:13000 BNA_BUS=http://127.0.0.1:18018 scripts/k8s-infra.sh flujo

paso "Túnel de Cloudflare con un token falso"
falso="$(printf '{"a":"%s","t":"%s","s":"%s"}' 00000000000000000000000000000000 \
  00000000-0000-0000-0000-000000000000 "$(printf 'falso' | base64)" | base64 -w0)"
BNA_TUNEL_ESPERA_CARGA=180 scripts/k8s-infra.sh tunel-cargar >"$TRABAJO/carga.txt" 2>&1 &
cargador=$!
for _ in $(seq 1 90); do
  grep -q "Esperando el token" "$TRABAJO/carga.txt" && break
  kill -0 "$cargador" 2>/dev/null || break
  sleep 2
done
# La misma tubería que imprime tunel-cargar (CARGA_REMOTA en scripts/k8s-infra.sh).
remota="$(sed -n "s/^ *sh -c '\(.*\)'\$/\1/p" "$TRABAJO/carga.txt")"
[ -n "$remota" ] || { cat "$TRABAJO/carga.txt" >&2; echo "tunel-cargar no imprimió el comando de carga." >&2; exit 1; }
printf '%s\n' "$falso" | k exec -i bna-carga-tunel -c carga -- sh -c "$remota"
if ! wait "$cargador"; then
  cat "$TRABAJO/carga.txt" >&2
  exit 1
fi
cat "$TRABAJO/carga.txt"
grep -q "Token con forma válida: .* permisos 600" "$TRABAJO/carga.txt"
k wait --for=delete pod/bna-carga-tunel --timeout=120s >/dev/null 2>&1 || true
if k get pod bna-carga-tunel >/dev/null 2>&1; then
  echo "Quedó el pod bna-carga-tunel." >&2
  exit 1
fi
if BNA_TUNEL_ESPERA_SEGUNDOS=45 scripts/k8s-infra.sh tunel-aplicar >"$TRABAJO/tunel.txt" 2>&1; then
  echo "El túnel quedó listo con un token falso." >&2
  exit 1
fi
pod="$(k get pod -l app.kubernetes.io/name=tunel -o name)"
salida_inicio="$(k get "$pod" -o jsonpath='{.status.initContainerStatuses[0].state.terminated.exitCode}')"
copia="$(k logs "$pod" -c secretos)"
echo "$copia"
if [ "$salida_inicio" != 0 ] || ! grep -q "permisos 440" <<<"$copia"; then
  echo "El contenedor de inicio del túnel no copió el token (salida '$salida_inicio')." >&2
  exit 1
fi
montajes="$(k get "$pod" -o jsonpath='{.spec.containers[?(@.name=="cloudflared")].volumeMounts[*].name}')"
if [ "$montajes" != secretos ]; then
  echo "cloudflared monta [$montajes]; se esperaba solo secretos (sin el PVC con el .env)." >&2
  exit 1
fi
echo "cloudflared monta solo /secretos y no conectó con el token falso, como se espera:"
k logs "$pod" -c cloudflared --tail=3 2>/dev/null | cut -c1-160 || true
scripts/k8s-infra.sh tunel-quitar
if k get deployment bna-tunel >/dev/null 2>&1; then
  echo "tunel-quitar no borró bna-tunel." >&2
  exit 1
fi

paso "Borrar"
kill "${REENVIOS[@]}" 2>/dev/null || true
REENVIOS=()
scripts/k8s-infra.sh borrar --si
restos="$(k get all,ingresses,configmaps,persistentvolumeclaims -l app.kubernetes.io/instance=bna -o name)"
if [ -n "$restos" ]; then
  echo "Quedaron objetos del producto: $restos" >&2
  exit 1
fi
echo
echo "Overlay de Infraestructura comprobado en kind."
