#!/usr/bin/env bash
# Despliega el módulo de Clientes en el namespace 2022251091 del clúster K3s.
# NO crea el namespace ni recursos globales. Requiere: VPN WireGuard activa, kubectl apuntando al clúster
# e imágenes ya publicadas en Docker Hub (scripts/publicar_imagenes.sh).
set -euo pipefail
cd "$(dirname "$0")"
NS="2022251091"
command -v kubectl >/dev/null || { echo "No se encontró kubectl"; exit 1; }
kubectl get namespace "$NS" >/dev/null || { echo "No se puede acceder al namespace $NS (¿VPN activa y kubeconfig correcto?)"; exit 1; }

# Secretos: kubernetes/secretos.env si existe; si no, se toman de ../.env (python scripts/generar_env.py).
if [ ! -f secretos.env ]; then
  [ -f ../.env ] || { echo "No hay secretos.env ni ../.env. Ejecute primero: python scripts/generar_env.py"; exit 1; }
  grep -E '^(MYSQL_ROOT_PASSWORD|MYSQL_PASSWORD|BUS_TOKEN|CLIENTES_TOKEN|CORE_TOKEN|RENIEC_SERVICE_TOKEN|RENIEC_ADMIN_PASSWORD|CLIENTES_PANEL_PASSWORD)=' ../.env > secretos.env
  chmod 600 secretos.env
  echo "Se creó kubernetes/secretos.env a partir de ../.env (no se sube a Git)."
fi
kubectl -n "$NS" create secret generic bna-secretos --from-env-file=secretos.env --dry-run=client -o yaml | kubectl -n "$NS" apply -f -

for f in 00-config.yaml 10-mysql.yaml 20-core.yaml 30-bus.yaml 40-reniec.yaml 50-clientes.yaml; do
  echo "Aplicando $f"; kubectl apply -f "$f"
done

# Con la etiqueta :latest y imagePullPolicy Always, esto fuerza a descargar la imagen más reciente.
if [ "${REINICIAR:-0}" = "1" ]; then
  for d in core bus reniec clientes; do kubectl -n "$NS" rollout restart deployment/$d; done
fi

echo; echo "Esperando a que los pods estén listos (la primera vez, MySQL y la descarga de imágenes pueden tardar)..."
for d in mysql core bus reniec clientes; do kubectl -n "$NS" rollout status deployment/$d --timeout=900s; done
kubectl -n "$NS" get pods,svc
echo; echo "Panel de Clientes : http://172.16.10.31:31091   (usuario: panel)"
echo "Admin de RENIEC   : http://172.16.10.31:31092   (usuario: admin)"
