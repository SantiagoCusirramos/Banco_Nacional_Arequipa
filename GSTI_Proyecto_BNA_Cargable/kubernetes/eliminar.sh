#!/usr/bin/env bash
# Elimina los recursos del módulo de Clientes del namespace 2022251091 (NO borra el namespace ni las carpetas hostPath).
set -euo pipefail
cd "$(dirname "$0")"
NS="2022251091"
for f in 50-clientes.yaml 40-reniec.yaml 30-bus.yaml 20-core.yaml 10-mysql.yaml 00-config.yaml; do kubectl delete -f "$f" --ignore-not-found; done
kubectl -n "$NS" delete secret bna-secretos --ignore-not-found
echo "Listo. Los datos siguen en /mnt/data/2022251091/bna-clientes/ del servidor."
