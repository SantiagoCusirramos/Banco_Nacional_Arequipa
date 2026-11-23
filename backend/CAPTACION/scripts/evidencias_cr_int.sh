#!/usr/bin/env bash
# Evidencias de CR-INT-09, CR-INT-01 y CR-INT-10 (parte de Captación) contra el producto levantado
# con ./bna up. Corre evidencias_cr_int.py en el contenedor del Bus, como ./bna smoke: llega a
# CAPTACION, SOL y COREDB solo por el Bus. Deja el JSON (sin tokens ni claves, con documentos y
# contactos enmascarados) en Documents/captacion/evidencias/.
#
# Uso, desde la raíz del repositorio:  backend/CAPTACION/scripts/evidencias_cr_int.sh
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$RAIZ"
[ -f .env ] || { echo "No hay .env: ejecute primero ./bna up" >&2; exit 1; }

valor() { grep -E "^$1=" .env | tail -n 1 | cut -d= -f2-; }

DESTINO="Documents/captacion/evidencias"
mkdir -p "$DESTINO"
SALIDA="$DESTINO/evidencias-$(date +%Y-%m-%d-%H%M).json"

set +e
MSYS_NO_PATHCONV=1 docker compose exec -T \
  -e E2E_BUS=http://127.0.0.1:8018 \
  -e BUS_TOKEN="$(valor BUS_TOKEN_PRUEBAS)" \
  -e BNA_ADMIN_USUARIO="$(valor BNA_ADMIN_USUARIO)" \
  -e BNA_ADMIN_PASSWORD="$(valor BNA_ADMIN_PASSWORD)" \
  -e CAP_SOL_TOKEN="$(valor CAP_SOL_TOKEN)" \
  bus python - < backend/CAPTACION/scripts/evidencias_cr_int.py > "$SALIDA"
codigo=$?
set -e
echo "Evidencias en $SALIDA"
exit "$codigo"
