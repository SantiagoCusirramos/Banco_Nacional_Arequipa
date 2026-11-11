#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -f .env.seguridad.local ]]; then
  set -a
  source .env.seguridad.local
  set +a
fi
: "${SEGURIDAD_SECRET_KEY:?Defina SEGURIDAD_SECRET_KEY o backend/.env.seguridad.local}"
exec ../.venv-seguridad/bin/python -m uvicorn seguridad.app:app --host 127.0.0.1 --port 8013 "$@"
