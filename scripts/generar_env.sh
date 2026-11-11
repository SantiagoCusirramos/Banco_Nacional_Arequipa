#!/usr/bin/env bash
# Crea o completa .env a partir de .env.example.
#   - Una variable que falta se agrega con el valor del ejemplo.
#   - Una variable vacía recibe un valor aleatorio de 48 caracteres hexadecimales.
#   - Un valor que ya existe nunca se cambia.
# Uso: scripts/generar_env.sh [carpeta del repositorio]
set -euo pipefail

RAIZ="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
EJEMPLO="$RAIZ/.env.example"
DESTINO="$RAIZ/.env"

aleatorio() { head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n'; }

[ -f "$EJEMPLO" ] || { echo "No existe $EJEMPLO" >&2; exit 1; }
umask 077
[ -f "$DESTINO" ] || : > "$DESTINO"
chmod 600 "$DESTINO"

nuevas=0
while IFS= read -r linea || [ -n "$linea" ]; do
  case "$linea" in
    [A-Za-z_]*=*) ;;
    *) continue ;;
  esac
  clave="${linea%%=*}"
  valor="${linea#*=}"
  actual="$(grep -E "^${clave}=" "$DESTINO" | tail -n 1 || true)"
  if [ -n "$actual" ] && [ -n "${actual#*=}" ]; then
    continue
  fi
  [ -n "$valor" ] || valor="$(aleatorio)"
  if [ -n "$actual" ]; then
    # Estaba vacía: se reemplaza en su sitio.
    temporal="$(mktemp "$RAIZ/.env.XXXXXX")"
    sed "s|^${clave}=.*|${clave}=${valor}|" "$DESTINO" > "$temporal"
    cat "$temporal" > "$DESTINO"
    rm -f "$temporal"
  else
    printf '%s=%s\n' "$clave" "$valor" >> "$DESTINO"
  fi
  nuevas=$((nuevas + 1))
done < "$EJEMPLO"

if [ "$nuevas" -gt 0 ]; then
  echo "$DESTINO: $nuevas variables nuevas. El archivo no se versiona."
fi
