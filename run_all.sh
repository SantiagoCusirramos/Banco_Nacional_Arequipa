#!/usr/bin/env bash
# Vuelve a ejecutar todo (rama mysql) y regenera las salidas y los fragmentos
# del informe:
#   1. Modelo: sql/bna_core.sql (MySQL 8.4) y los fragmentos del modelo en
#      informe/, que deben quedar idénticos a los de la rama main.
#   2. Pruebas en MySQL 8.4: resultados/mysql/ e informe/mysql-pruebas-stats.tex.
#   3. Matriz de trazabilidad y comparaciones con PostgreSQL (rama main,
#      commit MAIN_COMMIT de trazabilidad/catalogo.py):
#      resultados/trazabilidad.{md,csv} e informe/mysql-*.tex.
# Los experimentos de la comparación de gestores, la reproducción de la línea
# base MySQL y el control son de la rama main.
# Cada carpeta de resultados/ incluye metadatos.txt (fecha, commit, versión,
# imagen y configuración del servidor). Para que el commit registrado
# describa lo ejecutado, conviene correrlo con el árbol limpio (fuera de
# resultados/ e informe/).
#
# Uso: ./run_all.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
. "$ROOT/lib/comun.sh"

case "$(commit_actual)" in
  *sucio*) echo "Aviso: hay cambios sin confirmar; los metadatos registrarán el commit como «sucio»." >&2 ;;
esac

echo "== 1. Modelo"
(cd "$ROOT/modelo" && python3 modelo_bna.py ../informe > /dev/null)

echo "== 2. Pruebas"
"$ROOT/pruebas/mysql/run_tests.sh"

echo "== 3. Trazabilidad"
python3 "$ROOT/trazabilidad/matriz.py"
