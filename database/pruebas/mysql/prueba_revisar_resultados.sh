#!/usr/bin/env bash
# Prueba revisar_resultados.sh sin base de datos: una falla en cualquiera de los dos
# archivos de resultados debe dar un código de salida distinto de 0.
#
# Uso: pruebas/mysql/prueba_revisar_resultados.sh
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fallas=0

# esperar SALIDA DESCRIPCION BASE EXTENSION
esperar() {
  printf '%s' "$3" > "$TMP/resultado.tsv"
  printf '%s' "$4" > "$TMP/resultado-extension.tsv"
  "$HERE/revisar_resultados.sh" "$TMP" >/dev/null
  local obtenido=$?
  if [ "$obtenido" = "$1" ]; then
    echo "ok    $2"
  else
    echo "FALLA $2: salió con $obtenido, se esperaba $1"
    fallas=1
  fi
}

esperar 0 'todo pasa' $'F01\tpasa\nF02\tN/A\n' $'X01\tpasa\n'
esperar 1 'falla una prueba de la matriz' $'F01\tpasa\nF12d\tfalla\n' $'X01\tpasa\n'
esperar 1 'falla una prueba de la extensión' $'F01\tpasa\n' $'X01\tfalla\n'
esperar 1 'no hay resultados de la matriz' '' $'X01\tpasa\n'
esperar 1 'no hay resultados de la extensión' $'F01\tpasa\n' ''
exit "$fallas"
