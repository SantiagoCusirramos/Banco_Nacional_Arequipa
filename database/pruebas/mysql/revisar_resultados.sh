#!/usr/bin/env bash
# Decide el código de salida de run_tests.sh: 1 si alguna prueba de la matriz o de la
# extensión está como «falla», o si falta alguno de los dos archivos de resultados.
#
# Uso: pruebas/mysql/revisar_resultados.sh CARPETA_DE_RESULTADOS
set -uo pipefail

OUT="$1"
fallas=0
for f in resultado.tsv resultado-extension.tsv; do
  if [ ! -s "$OUT/$f" ]; then
    echo "   falta $OUT/$f"
    fallas=1
  elif grep -q 'falla$' "$OUT/$f"; then
    echo "   hay pruebas que fallan en $f:"
    grep 'falla$' "$OUT/$f" | cut -f1 | sed 's/^/     /'
    fallas=1
  fi
done
exit "$fallas"
