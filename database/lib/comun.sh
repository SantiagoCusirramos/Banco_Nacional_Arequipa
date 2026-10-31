# Funciones comunes de los ejecutores. Se carga con:
#   . "$ROOT/lib/comun.sh"   (con ROOT = raíz del repositorio)
# shellcheck shell=bash

# shellcheck source=../imagenes.env
. "$ROOT/imagenes.env"

# Commit sobre el que corre la ejecución. "sucio" indica cambios sin
# confirmar fuera de resultados/ e informe/, que son salidas.
commit_actual() {
  local c estado=limpio
  c="$(git -C "$ROOT" rev-parse --short=12 HEAD)"
  [ -n "$(git -C "$ROOT" status --porcelain -- . ':!resultados' ':!informe')" ] && estado=sucio
  echo "$c ($estado)"
}

# metadatos ARCHIVO [CLAVE=VALOR]...
# Escribe la fecha de la ejecución, el commit, Docker y los pares recibidos
# (versiones de los gestores, imágenes, etc.).
metadatos() {
  local f="$1"; shift
  {
    echo "fecha: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "commit: $(commit_actual)"
    echo "docker: $(docker version --format '{{.Server.Version}}' 2>/dev/null || echo desconocido)"
    for kv in "$@"; do echo "${kv%%=*}: ${kv#*=}"; done
  } > "$f"
}

# lecturas_de CLIENTE_ROOT CLIENTE: las tablas y vistas de las bases del sistema que
# CLIENTE puede leer, una por línea y ordenadas. Una sola sesión intenta todas.
lecturas_de() {
  "$1" -N -B -e "SELECT CONCAT('SELECT ''', table_schema, '.', table_name, ''' WHERE (SELECT COUNT(*) FROM ',
                               table_schema, '.', table_name, ') >= 0;')
                   FROM information_schema.tables
                  WHERE table_schema NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys', 'prueba')" \
    | "$2" -N -B --force 2>/dev/null | LC_ALL=C sort
}

# Concesiones de lectura de bna_api que una lista de objetos no vería: las que cubren
# objetos que aún no existen, y las que llegan por otro rol.
CONCESIONES_AMPLIAS_API="SELECT (SELECT COUNT(*) FROM mysql.user WHERE User = 'bna_api' AND Select_priv = 'Y')
  + (SELECT COUNT(*) FROM mysql.db WHERE User = 'bna_api' AND Select_priv = 'Y')
  + (SELECT COUNT(*) FROM mysql.columns_priv WHERE User = 'bna_api')
  + (SELECT COUNT(*) FROM mysql.role_edges WHERE TO_USER = 'bna_api')"
